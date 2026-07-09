#!/usr/bin/env python3

import rospy
import numpy as np
import open3d as o3d
import sensor_msgs.point_cloud2 as pc2
from sensor_msgs.msg import PointCloud2
import ros_numpy
import time

class VoxelGridFilter:
    def __init__(self):
        # Params
        self.leaf_size = rospy.get_param("~leaf_size", 0.1)
        self.accumulation_frames = rospy.get_param("~accumulation_frames", 50)
        self.input_topic = rospy.get_param("~input_topic", "/livox/lidar")
        self.voxel_cloud_topic = rospy.get_param("~voxel_cloud_topic", "/voxel_cloud")
        self.dense_cloud_topic = rospy.get_param("~dense_cloud_topic", "/dense_cloud")
    
        # Publishers & Subscribers
        self.sub = rospy.Subscriber(self.input_topic, PointCloud2, self.cloud_callback, queue_size=10)
        self.voxel_pub = rospy.Publisher(self.voxel_cloud_topic, PointCloud2, queue_size=10)
        self.dense_pub = rospy.Publisher(self.dense_cloud_topic, PointCloud2, queue_size=10)

        self.raw_buffer = []
        self.print_configuration()


    def print_configuration(self):
        rospy.loginfo("=" * 60)
        rospy.loginfo("VoxelGridFilter Node Started")
        rospy.loginfo(f"Leaf size: {self.leaf_size} m")
        rospy.loginfo(f"Accumulation frames: {self.accumulation_frames}")
        rospy.loginfo(f"Input topic: {self.input_topic}")
        rospy.loginfo(f"Voxel cloud topic: {self.voxel_cloud_topic}")
        rospy.loginfo(f"Dense cloud topic: {self.dense_cloud_topic}")
        rospy.loginfo("=" * 60)

    def cloud_callback(self, cloud_msg):
        try:
            points = self.ros_to_numpy(cloud_msg)
            if len(points) == 0:
                return
            
            self.raw_buffer.append(points)
            if len(self.raw_buffer) >= self.accumulation_frames:
                t_start = time.time()
                
                # Merge accumulated frames
                dense_points = np.vstack(self.raw_buffer)
                self.raw_buffer = []  # Clear buffer

                # Publish dense cloud
                dense_msg = self.numpy_to_ros(dense_points, cloud_msg.header)
                self.dense_pub.publish(dense_msg)

                # Voxel grid filter
                voxel_points = self.apply_voxel_grid(dense_points)
                voxel_msg = self.numpy_to_ros(voxel_points, cloud_msg.header)
                self.voxel_pub.publish(voxel_msg)

                t_end = time.time()
                reduction = (1.0 - len(voxel_points) / len(dense_points)) * 100
                rospy.loginfo(
                    f"Filtered: {len(dense_points)} -> {len(voxel_points)} points "
                    f"({reduction:.1f}% reduction) in {t_end - t_start:.2f} s"
                )
                rospy.loginfo("=" * 60)
            
        except Exception as e:
            rospy.logerr(f"Error processing cloud: {e}")
    
    
    def apply_voxel_grid(self, points):
        """Voxel grid filter using Open3D"""
        # Convert numpy array to Open3D point cloud
        o3d_cloud = o3d.geometry.PointCloud()
        o3d_cloud.points = o3d.utility.Vector3dVector(points.astype(np.float64))
        
        # Apply voxel downsampling
        downsampled = o3d_cloud.voxel_down_sample(self.leaf_size)
        
        # Convert back to numpy array
        return np.asarray(downsampled.points, dtype=np.float32)
    

    def ros_to_numpy(self, cloud_msg):
        """Converts ROS PointCloud2 message to numpy array"""
        xyz_array = ros_numpy.point_cloud2.pointcloud2_to_xyz_array(cloud_msg, remove_nans=True)
        return xyz_array


    def numpy_to_ros(self, points, header):
        """Converts numpy array to ROS PointCloud2 message"""
        if points.dtype != np.float32:
            points = points.astype(np.float32)

        return pc2.create_cloud_xyz32(header, points)


if __name__ == '__main__':
    try:
        rospy.init_node('voxel_grid_filter', anonymous=False)
        filter_node = VoxelGridFilter()
        rospy.spin()
        
    except rospy.ROSInterruptException:
        rospy.loginfo("Node terminated")
    except Exception as e:
        rospy.logfatal(f"Failed to start Voxel Grid Filter Node: {e}")