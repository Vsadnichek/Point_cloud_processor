#pragma once

#include <ros/time.h>
#include <sensor_msgs/PointCloud2.h>

#include <vector>

namespace pointcloud_processor {

struct PointCloudBatch {
  std::vector<sensor_msgs::PointCloud2::ConstPtr> messages;
  ros::Time window_start;
  ros::Time window_end;
};

}  // namespace pointcloud_processor
