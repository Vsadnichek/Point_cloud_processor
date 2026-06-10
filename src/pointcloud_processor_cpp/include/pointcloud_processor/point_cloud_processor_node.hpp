#pragma once

#include <pointcloud_processor/point_cloud_batch.hpp>

#include <ros/ros.h>
#include <sensor_msgs/PointCloud2.h>

#include <concurrentqueue.h>

#include <atomic>
#include <chrono>
#include <cstddef>
#include <memory>
#include <string>
#include <thread>

namespace pointcloud_processor {

class PointCloudProcessorNode {
public:
  PointCloudProcessorNode(ros::NodeHandle& nh, ros::NodeHandle& pnh);
  PointCloudProcessorNode(const PointCloudProcessorNode&) = delete;
  PointCloudProcessorNode(PointCloudProcessorNode&&) = delete;
  ~PointCloudProcessorNode() noexcept { Stop(); }

  PointCloudProcessorNode& operator=(const PointCloudProcessorNode&) = delete;
  PointCloudProcessorNode& operator=(PointCloudProcessorNode&&) = delete;

  void Start();
  void Stop() noexcept;

private:
  using SteadyClock = std::chrono::steady_clock;
  using SteadyTimePoint = SteadyClock::time_point;
  using IngressQueue =
      moodycamel::ConcurrentQueue<sensor_msgs::PointCloud2::ConstPtr>;
  using WorkQueue = moodycamel::ConcurrentQueue<PointCloudBatch>;

  void PointCloudCallback(const sensor_msgs::PointCloud2::ConstPtr& msg);
  void CollectorLoop();
  void WorkerLoop();
  [[nodiscard]] bool DrainIngressAndEnqueue();
  void ProcessBatch(const PointCloudBatch& batch);

  void SetUpdatePeriodSeconds(double period_seconds);
  void SetVoxelLeafSize(double leaf_size);

  [[nodiscard]] bool IsRunning() const noexcept {
    return collector_running_.load(std::memory_order_acquire) ||
           worker_running_.load(std::memory_order_acquire);
  }

  [[nodiscard]] double GetUpdatePeriodSeconds() const noexcept {
    return std::chrono::duration<double>(update_period_).count();
  }

  [[nodiscard]] const std::string& GetInputTopic() const noexcept {
    return input_topic_;
  }

  [[nodiscard]] const std::string& GetOutputTopic() const noexcept {
    return output_topic_;
  }

  [[nodiscard]] double GetVoxelLeafSize() const noexcept {
    return voxel_leaf_size_;
  }

  [[nodiscard]] std::size_t GetIngressQueueCapacity() const noexcept {
    return ingress_capacity_;
  }

  [[nodiscard]] std::size_t GetWorkQueueCapacity() const noexcept {
    return work_capacity_;
  }

  [[nodiscard]] std::size_t GetRosCallbackThreadCount() const noexcept {
    return ros_callback_thread_count_;
  }

  ros::NodeHandle nh_;
  ros::NodeHandle pnh_;
  ros::Subscriber cloud_sub_;
  ros::Publisher cloud_pub_;

  double voxel_leaf_size_{0.05};
  std::size_t ingress_capacity_{4096};
  std::size_t work_capacity_{32};
  std::size_t ros_callback_thread_count_{2};
  SteadyClock::duration update_period_{std::chrono::seconds(1)};
  std::string input_topic_{"/points"};
  std::string output_topic_{"/points_filtered"};

  IngressQueue ingress_queue_;
  WorkQueue work_queue_;
  moodycamel::ConsumerToken ingress_consumer_token_;
  moodycamel::ProducerToken work_producer_token_;
  moodycamel::ConsumerToken work_consumer_token_;

  std::unique_ptr<std::thread> collector_thread_;
  std::unique_ptr<std::thread> worker_thread_;

  std::atomic<bool> collector_running_{false};
  std::atomic<bool> worker_running_{false};
};

}  // namespace pointcloud_processor
