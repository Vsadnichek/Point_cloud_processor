#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import numpy as np
import tf.transformations as tft

from sensor_msgs.msg import PointCloud2, PointField
from visualization_msgs.msg import Marker
from sensor_msgs import point_cloud2

from dynamic_reconfigure.server import Server
from mirror_live_node.cfg import FilterBoxConfig


class CloudFilterNode:
    def __init__(self):
        rospy.init_node("cloud_filter_node")

        # Включение/выключение источников
        self.use_velodyne = rospy.get_param("~use_velodyne", True)
        self.use_reflected = rospy.get_param("~use_reflected", True)

        # Параметры бокса (будут перезаписаны dynamic_reconfigure)
        self.box_cx = 0.0
        self.box_cy = 0.0
        self.box_cz = 0.0
        self.box_lx = 2.0
        self.box_ly = 2.0
        self.box_lz = 2.0
        self.box_yaw = 0.0

        # dynamic_reconfigure
        self.srv = Server(FilterBoxConfig, self.reconfig_cb)

        # Publishers
        self.pub_filtered = rospy.Publisher("/filtrated_cloud", PointCloud2, queue_size=1)
        self.pub_marker = rospy.Publisher("/filter_box_marker", Marker, queue_size=1)

        # Storage
        self.pc_velodyne = None
        self.pc_reflected = None

        if self.use_velodyne:
            rospy.Subscriber("/velodyne_points", PointCloud2, self.cb_velodyne, queue_size=1)
        if self.use_reflected:
            rospy.Subscriber("/reflected_cloud", PointCloud2, self.cb_reflected, queue_size=1)

        rospy.Timer(rospy.Duration(0.05), self.process)

        rospy.loginfo("cloud_filter_node with dynamic_reconfigure started")
        rospy.spin()

    # ------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------

    def reconfig_cb(self, config, level):
        self.box_cx = config.box_cx
        self.box_cy = config.box_cy
        self.box_cz = config.box_cz
        self.box_lx = config.box_lx
        self.box_ly = config.box_ly
        self.box_lz = config.box_lz
        self.box_yaw = config.box_yaw
        return config

    def cb_velodyne(self, msg):
        self.pc_velodyne = msg

    def cb_reflected(self, msg):
        self.pc_reflected = msg

    # ------------------------------------------------------------
    # Utils
    # ------------------------------------------------------------

    def pc2_to_xyz(self, pc):
        pts = []
        for p in point_cloud2.read_points(pc, field_names=("x", "y", "z"), skip_nans=True):
            pts.append([p[0], p[1], p[2]])
        if len(pts) == 0:
            return np.zeros((0, 3))
        return np.array(pts)

    def xyz_to_pc2(self, arr, frame_id):
        fields = [
            PointField("x", 0, PointField.FLOAT32, 1),
            PointField("y", 4, PointField.FLOAT32, 1),
            PointField("z", 8, PointField.FLOAT32, 1),
        ]
        header = rospy.Header()
        header.stamp = rospy.Time.now()
        header.frame_id = frame_id
        return point_cloud2.create_cloud(header, fields, arr)

    def point_in_box(self, pts):
        pts_shift = pts - np.array([self.box_cx, self.box_cy, self.box_cz])
        R = tft.rotation_matrix(-self.box_yaw, (0, 0, 1))[:3, :3]
        pts_rot = pts_shift @ R.T

        hx = self.box_lx / 2.0
        hy = self.box_ly / 2.0
        hz = self.box_lz / 2.0

        return (
            (np.abs(pts_rot[:, 0]) <= hx) &
            (np.abs(pts_rot[:, 1]) <= hy) &
            (np.abs(pts_rot[:, 2]) <= hz)
        )

    # ------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------

    def publish_marker(self):
        m = Marker()
        m.header.frame_id = "velodyne"
        m.header.stamp = rospy.Time.now()
        m.type = Marker.CUBE
        m.action = Marker.ADD

        m.pose.position.x = self.box_cx
        m.pose.position.y = self.box_cy
        m.pose.position.z = self.box_cz

        q = tft.quaternion_from_euler(0, 0, self.box_yaw)
        m.pose.orientation.x = q[0]
        m.pose.orientation.y = q[1]
        m.pose.orientation.z = q[2]
        m.pose.orientation.w = q[3]

        m.scale.x = self.box_lx
        m.scale.y = self.box_ly
        m.scale.z = self.box_lz

        m.color.r = 0.0
        m.color.g = 1.0
        m.color.b = 0.0
        m.color.a = 0.25

        self.pub_marker.publish(m)

    # ------------------------------------------------------------

    def process(self, event):
        clouds = []

        if self.use_velodyne and self.pc_velodyne:
            clouds.append(self.pc2_to_xyz(self.pc_velodyne))

        if self.use_reflected and self.pc_reflected:
            clouds.append(self.pc2_to_xyz(self.pc_reflected))

        if not clouds:
            return

        merged = np.vstack(clouds)

        mask = self.point_in_box(merged)
        filtered = merged[mask]

        out = self.xyz_to_pc2(filtered, frame_id="velodyne")
        self.pub_filtered.publish(out)

        self.publish_marker()


# ------------------------------------------------------------
if __name__ == "__main__":
    CloudFilterNode()
