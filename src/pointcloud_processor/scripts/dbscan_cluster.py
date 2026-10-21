#!/usr/bin/env python3

import rospy
import numpy as np
from sensor_msgs.msg import PointCloud2
import ros_numpy
from sklearn.cluster import DBSCAN
import time

class DBSCANCluster:
    def __init__(self):
        # Params
        self.input_topic = rospy.get_param("~input_topic", "/objects_cloud")
        self.output_topic = rospy.get_param("~output_topic", "/dbscan_clusters")
        self.colors = np.array([
            [255,   0,   0],   # red
            [  0, 255,   0],   # green
            [  0,   0, 255],   # blue
            [255, 255,   0],   # yellow
            [255,   0, 255],   # magenta
            [  0, 255, 255],   # cyan
            [255, 128,   0],   # orange
            [128,   0, 255],   # violet
        ], dtype=np.uint8)

        # DBSCAN params
        self.eps = rospy.get_param("~dbscan_eps", 0.15)
        self.min_samples = rospy.get_param("~dbscan_min_samples", 30)

        # Publishers & Subscribers
        self.sub = rospy.Subscriber(self.input_topic, PointCloud2, self.cloud_callback, queue_size=10)
        self.pub_clusters = rospy.Publisher(self.output_topic, PointCloud2, queue_size=10)

        self.last_header = None  # header of the last frame
        self.print_configuration()

    def print_configuration(self):
        rospy.loginfo("=" * 60)
        rospy.loginfo("DBSCANCluster Node Started")
        rospy.loginfo(f"Input topic: {self.input_topic}")
        rospy.loginfo(f"Output topic: {self.output_topic}")
        rospy.loginfo(f"DBSCAN eps: {self.eps}")
        rospy.loginfo(f"DBSCAN min_samples: {self.min_samples}")
        rospy.loginfo("=" * 60)

    def cloud_callback(self, cloud_msg):
        try:
            self.last_header = cloud_msg.header
            points = self.ros_to_numpy(cloud_msg)
            if len(points) == 0:
                return

            # Perform DBSCAN clustering
            self.t_start = time.time()
            labels = DBSCAN(
                eps=self.eps, 
                min_samples=self.min_samples
            ).fit_predict(points)

            # Process and publish clusters
            
            self.publish_clusters(points, labels)

        except Exception as e:
            rospy.logerr(f"Error in cloud_callback: {e}")

    def publish_clusters(self, points, labels):
        if self.last_header is None:
            return

        dtype = np.dtype([
            ('x', np.float32), 
            ('y', np.float32), 
            ('z', np.float32), 
            ('rgb', np.uint32)
        ])

        cloud_array = np.zeros(len(points), dtype=dtype)

        cloud_array['x'] = points[:, 0]
        cloud_array['y'] = points[:, 1]
        cloud_array['z'] = points[:, 2]

        noise_rgb = (120 << 16) | (120 << 8) | 120  # Dark gray for noise
        cloud_array['rgb'][:] = noise_rgb  # Default color for noise

        unique_labels = set(labels)
        cluster_counter = 0

        for label in unique_labels:
            if label == -1:
                continue  # Skip noise
            
            color = self.colors[label % len(self.colors)]
            rgb = (color[0] << 16) | (color[1] << 8) | color[2]

            cloud_array['rgb'][labels == label] = rgb
            cluster_counter += 1    

        msg = ros_numpy.point_cloud2.array_to_pointcloud2(
            cloud_array, 
            stamp=self.last_header.stamp,
            frame_id=self.last_header.frame_id
        )
        
        self.pub_clusters.publish(msg)
        self.t_end = time.time()
        rospy.loginfo(f"Clusters found: {cluster_counter}; Time taken: {self.t_end - self.t_start:.4f} seconds")

    def ros_to_numpy(self, cloud_msg):
        # Convert ROS PointCloud2 message to numpy array
        return ros_numpy.point_cloud2.pointcloud2_to_xyz_array(cloud_msg)

if __name__ == "__main__":
    try:
        rospy.init_node("dbscan_cluster_node")
        dbscan_cluster = DBSCANCluster()
        rospy.spin()
    except rospy.ROSInterruptException:
        rospy.loginfo("DBSCAN Cluster Node terminated")
    except Exception as e:
        rospy.logerr(f"Failed to start DBSCAN Cluster Node: {e}")