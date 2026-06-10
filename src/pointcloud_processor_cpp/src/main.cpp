#include <pointcloud_processor/point_cloud_processor_node.hpp>

#include <ros/ros.h>

namespace {

constexpr int kRosSpinnerThreads = 2;

}  // namespace

int main(int argc, char** argv) {
  ros::init(argc, argv, "pointcloud_processor");
  ros::NodeHandle nh;
  ros::NodeHandle pnh("~");

  pointcloud_processor::PointCloudProcessorNode node(nh, pnh);
  node.Start();

  ros::AsyncSpinner spinner(kRosSpinnerThreads);
  spinner.start();

  ros::waitForShutdown();

  node.Stop();
  spinner.stop();
  return 0;
}
