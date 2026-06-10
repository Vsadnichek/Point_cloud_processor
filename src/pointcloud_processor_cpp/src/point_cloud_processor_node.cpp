#include <pointcloud_processor/point_cloud_processor_node.hpp>

#include <pcl/filters/voxel_grid.h>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl_conversions/pcl_conversions.h>

#include <cassert>
#include <utility>

namespace pointcloud_processor {

namespace {

constexpr char kDefaultInputTopic[] = "/livox/lidar";
constexpr char kDefaultOutputTopic[] = "/points_filtered";
constexpr double kDefaultUpdatePeriodSec = 1.0;
constexpr double kDefaultVoxelLeafSize = 0.05;
constexpr std::size_t kDefaultIngressCapacity = 4096;
constexpr std::size_t kDefaultWorkCapacity = 32;
constexpr std::size_t kDefaultRosCallbackThreadCount = 2;
constexpr int kWorkerIdleSleepMs = 2;

pcl::PointCloud<pcl::PointXYZ>::Ptr MergeBatch(const PointCloudBatch& batch) {
  pcl::PointCloud<pcl::PointXYZ>::Ptr merged(
      new pcl::PointCloud<pcl::PointXYZ>());
  for (const auto& msg : batch.messages) {
    assert(msg != nullptr);
    pcl::PointCloud<pcl::PointXYZ> cloud;
    pcl::fromROSMsg(*msg, cloud);
    *merged += cloud;
  }
  return merged;
}

template <typename T>
T ReadPositiveParam(ros::NodeHandle& pnh, const std::string& name,
                    T default_val) {
  int raw = 0;
  pnh.param(name, raw, static_cast<int>(default_val));
  assert(raw > 0);
  return static_cast<T>(raw);
}

}  // namespace

PointCloudProcessorNode::PointCloudProcessorNode(ros::NodeHandle& nh,
                                                 ros::NodeHandle& pnh)
    : nh_(nh),
      pnh_(pnh),
      cloud_sub_(),
      cloud_pub_(),
      voxel_leaf_size_(kDefaultVoxelLeafSize),
      ingress_capacity_(ReadPositiveParam<std::size_t>(
          pnh_, "ingress_queue_capacity", kDefaultIngressCapacity)),
      work_capacity_(ReadPositiveParam<std::size_t>(pnh_, "work_queue_capacity",
                                                    kDefaultWorkCapacity)),
      ros_callback_thread_count_(ReadPositiveParam<std::size_t>(
          pnh_, "ros_callback_thread_count", kDefaultRosCallbackThreadCount)),
      update_period_(std::chrono::seconds(1)),
      input_topic_(kDefaultInputTopic),
      output_topic_(kDefaultOutputTopic),
      ingress_queue_(ingress_capacity_, 0, ros_callback_thread_count_),
      work_queue_(work_capacity_, 1, 0),
      ingress_consumer_token_(ingress_queue_),
      work_producer_token_(work_queue_),
      work_consumer_token_(work_queue_),
      collector_thread_(),
      worker_thread_(),
      collector_running_(false),
      worker_running_(false) {
  double update_period_sec = kDefaultUpdatePeriodSec;
  pnh_.param("update_period_sec", update_period_sec, update_period_sec);
  SetUpdatePeriodSeconds(update_period_sec);

  pnh_.param<std::string>("input_topic", input_topic_, kDefaultInputTopic);
  pnh_.param<std::string>("output_topic", output_topic_, kDefaultOutputTopic);
  pnh_.param("voxel_leaf_size", voxel_leaf_size_, kDefaultVoxelLeafSize);
}

void PointCloudProcessorNode::Start() {
  if (IsRunning()) {
    return;
  }

  cloud_pub_ = nh_.advertise<sensor_msgs::PointCloud2>(output_topic_, 1);
  cloud_sub_ = nh_.subscribe<sensor_msgs::PointCloud2>(
      input_topic_, 50, &PointCloudProcessorNode::PointCloudCallback, this);

  collector_running_.store(true, std::memory_order_release);
  worker_running_.store(true, std::memory_order_release);

  collector_thread_ = std::make_unique<std::thread>(
      &PointCloudProcessorNode::CollectorLoop, this);
  worker_thread_ =
      std::make_unique<std::thread>(&PointCloudProcessorNode::WorkerLoop, this);
}

void PointCloudProcessorNode::Stop() noexcept {
  collector_running_.store(false, std::memory_order_release);
  worker_running_.store(false, std::memory_order_release);

  if (collector_thread_ != nullptr && collector_thread_->joinable()) {
    collector_thread_->join();
    collector_thread_.reset();
  }
  if (worker_thread_ != nullptr && worker_thread_->joinable()) {
    worker_thread_->join();
    worker_thread_.reset();
  }

  cloud_sub_.shutdown();
  cloud_pub_.shutdown();
}

void PointCloudProcessorNode::PointCloudCallback(
    const sensor_msgs::PointCloud2::ConstPtr& msg) {
  assert(msg != nullptr);
  const bool enqueued = ingress_queue_.try_enqueue(msg);
  if (!enqueued) {
    ROS_WARN_THROTTLE(5, "Ingress queue full (capacity %zu), dropping message",
                      ingress_capacity_);
  }
}

void PointCloudProcessorNode::CollectorLoop() {
  SteadyTimePoint tick = SteadyClock::now();
  while (ros::ok() && collector_running_.load(std::memory_order_acquire)) {
    tick += update_period_;
    std::this_thread::sleep_until(tick);

    [[maybe_unused]] const bool enqueued = DrainIngressAndEnqueue();
  }

  while (DrainIngressAndEnqueue()) {
  }
}

void PointCloudProcessorNode::WorkerLoop() {
  PointCloudBatch batch;
  while (ros::ok() && worker_running_.load(std::memory_order_acquire)) {
    if (work_queue_.try_dequeue(work_consumer_token_, batch)) {
      ProcessBatch(batch);
      continue;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(kWorkerIdleSleepMs));
  }

  while (work_queue_.try_dequeue(work_consumer_token_, batch)) {
    ProcessBatch(batch);
  }
}

bool PointCloudProcessorNode::DrainIngressAndEnqueue() {
  PointCloudBatch batch;
  sensor_msgs::PointCloud2::ConstPtr msg;
  while (ingress_queue_.try_dequeue(ingress_consumer_token_, msg)) {
    assert(msg != nullptr);
    if (batch.messages.empty()) {
      batch.window_start = msg->header.stamp;
    }
    batch.window_end = msg->header.stamp;
    batch.messages.push_back(std::move(msg));
  }

  if (batch.messages.empty()) {
    return false;
  }

  const bool enqueued =
      work_queue_.try_enqueue(work_producer_token_, std::move(batch));
  if (!enqueued) {
    ROS_WARN_THROTTLE(
        5, "Work queue full (capacity %zu), dropping batch (%zu msgs)",
        work_capacity_, batch.messages.size());
  }
  return enqueued;
}

void PointCloudProcessorNode::ProcessBatch(const PointCloudBatch& batch) {
  if (batch.messages.empty()) {
    return;
  }

  const pcl::PointCloud<pcl::PointXYZ>::Ptr merged = MergeBatch(batch);
  if (merged->empty()) {
    return;
  }

  pcl::VoxelGrid<pcl::PointXYZ> voxel;
  voxel.setInputCloud(merged);
  voxel.setLeafSize(static_cast<float>(voxel_leaf_size_),
                    static_cast<float>(voxel_leaf_size_),
                    static_cast<float>(voxel_leaf_size_));

  pcl::PointCloud<pcl::PointXYZ> filtered;
  voxel.filter(filtered);

  sensor_msgs::PointCloud2 output;
  pcl::toROSMsg(filtered, output);
  output.header.stamp = batch.window_end;
  if (batch.messages.back() != nullptr) {
    output.header.frame_id = batch.messages.back()->header.frame_id;
  }
  cloud_pub_.publish(output);
}

void PointCloudProcessorNode::SetUpdatePeriodSeconds(double period_seconds) {
  assert(period_seconds > 0.0);
  const auto ns = static_cast<SteadyClock::rep>(period_seconds * 1e9);
  update_period_ = std::chrono::nanoseconds(ns);
}

void PointCloudProcessorNode::SetVoxelLeafSize(double leaf_size) {
  assert(leaf_size > 0.0);
  voxel_leaf_size_ = leaf_size;
}

}  // namespace pointcloud_processor
