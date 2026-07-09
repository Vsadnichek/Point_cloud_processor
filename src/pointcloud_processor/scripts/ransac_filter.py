#!/usr/bin/env python3

import rospy
import numpy as np
import open3d as o3d
import sensor_msgs
from sensor_msgs import msg
import sensor_msgs.point_cloud2 as pc2
from sensor_msgs.msg import PointCloud2
import ros_numpy
import time

class RANSACFilter:
    def __init__(self):
        # Params
        self.input_topic = rospy.get_param("~input_topic", "/voxel_cloud")
        self.objects_topic = rospy.get_param("~objects_topic", "/objects_cloud")
        self.plane_topic = rospy.get_param("~plane_topic", "/plane_points")

        # RANSAC params
        self.distance_threshold = rospy.get_param("~distance_threshold", 0.1)
        self.accumulation_frames = rospy.get_param("~accumulation_frames", 4)
        self.max_iterations = rospy.get_param("~max_iterations", 1000)
        self.min_plane_points = rospy.get_param("~min_plane_points", 500)
        self.min_inlier_ratio = rospy.get_param("~min_inlier_ratio", 0.05)
        
        self.phase = 'init'  # 'init' -> 'online'
        self.init_buffer = []  # buffer for accumulated point clouds during 'init' phase
        self.plane_model = None
        self.last_header = None  # header of the last frame

        # Publishers & Subscribers
        self.sub = rospy.Subscriber(self.input_topic, PointCloud2, self.cloud_callback, queue_size=10)
        self.pub_objects = rospy.Publisher(self.objects_topic, PointCloud2, queue_size=10)
        self.pub_plane = rospy.Publisher(self.plane_topic, PointCloud2, queue_size=10)

        self.print_configuration()

    def print_configuration(self):
        rospy.loginfo("=" * 60)
        rospy.loginfo("RANSACFilter Node Started")
        rospy.loginfo(f"Input topic: {self.input_topic}")
        rospy.loginfo(f"Objects topic: {self.objects_topic}")
        rospy.loginfo(f"Plane topic: {self.plane_topic}")
        rospy.loginfo(f"Distance threshold: {self.distance_threshold} m")
        rospy.loginfo(f"Accumulation frames: {self.accumulation_frames}")
        rospy.loginfo(f"Max iterations: {self.max_iterations}")
        rospy.loginfo(f"Min plane points: {self.min_plane_points}")
        rospy.loginfo(f"Min inlier ratio: {self.min_inlier_ratio}")
        rospy.loginfo("=" * 60)

    def cloud_callback(self, cloud_msg):
        try:   
            self.last_header = cloud_msg.header
            points = self.ros_to_numpy(cloud_msg)
            if len(points) == 0:
                return
            
            if self.phase == 'init':
                t_start = time.time()
                self.init_buffer.append(points)
                rospy.loginfo(f"Init: {len(self.init_buffer)}/{self.accumulation_frames} frames")
                
                if len(self.init_buffer) >= self.accumulation_frames:
                    init_points = np.vstack(self.init_buffer)
                    self.ransac_find_plane(init_points)
                    objects_points, plane_points = self.split_by_plane(init_points)
                    self.publish_results(objects_points, plane_points)

                    self.init_buffer = []  # Clear the buffer after finding the plane
                    self.phase = 'online'
                    t_end = time.time()
                    rospy.loginfo(f"RANSAC initialization completed in {t_end - t_start:.2f} seconds")
            
            elif self.phase == 'online':
                t_start = time.time()
                if self.plane_model is not None:
                    objects_points, plane_points = self.split_by_plane(points)
                    
                else:
                    plane_points = np.empty((0, 3), dtype=np.float32)
                    objects_points = points

                self.publish_results(objects_points, plane_points)
                t_end = time.time()
                rospy.loginfo(f"Online processing completed in {t_end - t_start:.2f} seconds")
                rospy.loginfo("=" * 60)
        except Exception as e:
            rospy.logerr(f"Error in cloud_callback: {e}")


    def ransac_find_plane(self, points):
        rospy.loginfo(f"Running RANSAC on {len(points)} points from {len(self.init_buffer)} frames")

        # Create Open3D point cloud
        o3d_cloud = o3d.geometry.PointCloud()
        o3d_cloud.points = o3d.utility.Vector3dVector(points)

        try:
            while True:
                plane_model, inliers = o3d_cloud.segment_plane(
                distance_threshold=self.distance_threshold,
                ransac_n=3,
                num_iterations=self.max_iterations 
                )

                a, b, c, d = plane_model
                
                if abs(c) > 0.8: # Ensure the plane is roughly horizontal
                    break
                
                o3d_cloud = o3d_cloud.select_by_index(inliers, invert=True)  # Remove inliers and try again

                if len(o3d_cloud.points) < 1000:  # If too few points left, break
                    rospy.logwarn("Not enough points left to find a horizontal plane")
                    self.plane_model = None
                    return
        
        except Exception as e:
            rospy.logerr(f"RANSAC failed: {e}")
            self.plane_model = None
            return

        # Check if the found plane has enough inliers
        inlier_count = len(inliers)
        inlier_ratio = inlier_count / len(points)

        if (
            inlier_count < self.min_plane_points
            or
            inlier_ratio < self.min_inlier_ratio
        ):
            self.publish_results(
            objects_points=points,
            plane_points=np.empty((0, 3), dtype=np.float32)
            )
            self.plane_model = None
            return
        
        self.plane_model = plane_model
        rospy.loginfo(f"Plane found: {plane_model}")


    def split_by_plane(self, points):
        if self.plane_model is None:
            plane_points = np.empty((0, 3), dtype=np.float32)
            return points, plane_points

        a, b, c, d = self.plane_model
        distances = np.abs(np.dot(points, [a, b, c]) + d)
        plane_mask = distances < self.distance_threshold
        return points[~plane_mask], points[plane_mask]


    def publish_results(self, objects_points, plane_points):      
        if self.last_header is None:
            return

        if len(objects_points) > 0:
            objects_msg = self.numpy_to_ros(objects_points, self.last_header)
            self.pub_objects.publish(objects_msg)
            rospy.loginfo(f"Objects cloud: {len(objects_points)} points")

        if len(plane_points) > 0:
            plane_msg = self.numpy_to_ros(plane_points, self.last_header)
            self.pub_plane.publish(plane_msg)
            rospy.loginfo(f"Plane cloud: {len(plane_points)} points")

    def ros_to_numpy(self, msg):
        # Convert ROS PointCloud2 message to numpy array
        xyz_array = ros_numpy.point_cloud2.pointcloud2_to_xyz_array(msg)
        return xyz_array
    

    def numpy_to_ros(self, points, header):
        # Convert numpy array to ROS PointCloud2 message
        if points.dtype != np.float32:
            points = points.astype(np.float32)

        return pc2.create_cloud_xyz32(header, points)
    
if __name__ == "__main__":
    try:
        rospy.init_node("ransac_filter_node")
        ransac_filter = RANSACFilter()
        rospy.spin()
    except rospy.ROSInterruptException:
        rospy.loginfo("RANSAC Filter Node terminated")
    except Exception as e:
        rospy.logerr(f"Failed to start RANSAC Filter Node: {e}")