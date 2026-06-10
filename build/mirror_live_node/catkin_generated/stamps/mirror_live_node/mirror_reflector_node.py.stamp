#!/usr/bin/env python3
import rospy
import ros_numpy
import numpy as np
from sensor_msgs.msg import PointCloud2
from dynamic_reconfigure.server import Server
from mirror_live_node.cfg import MirrorParamsConfig
from visualization_msgs.msg import Marker

class MirrorReflector:
    def __init__(self):
        rospy.init_node("mirror_reflector_node")

        # Dynamic reconfigure параметры
        self.mirror_center_x = 0.0
        self.mirror_center_y = 0.306
        self.mirror_yaw_deg = 31.6

        # Подписка и публикация
        self.sub = rospy.Subscriber("/velodyne_points", PointCloud2, self.cloud_callback, queue_size=1)
        self.pub = rospy.Publisher("/reflected_cloud", PointCloud2, queue_size=1)
        self.marker_pub = rospy.Publisher("/mirror_marker", Marker, queue_size=1)

        # Dynamic reconfigure сервер
        Server(MirrorParamsConfig, self.reconfig_cb)

        rospy.loginfo("✅ Mirror reflector node started")
        rospy.spin()

    def reconfig_cb(self, config, level):
        self.mirror_center_x = config["mirror_center_x"]
        self.mirror_center_y = config["mirror_center_y"]
        self.mirror_yaw_deg = config["mirror_yaw_deg"]
        rospy.loginfo(f"🔧 Updated mirror: x={self.mirror_center_x}, y={self.mirror_center_y}, yaw={self.mirror_yaw_deg}°")
        return config

    def cloud_callback(self, msg):
        pc = ros_numpy.point_cloud2.pointcloud2_to_array(msg)
        pts = np.vstack((pc['x'], pc['y'], pc['z'])).T

        mirror_center = np.array([self.mirror_center_x, self.mirror_center_y])
        yaw_rad = np.deg2rad(self.mirror_yaw_deg)
        normal = np.array([np.cos(yaw_rad), np.sin(yaw_rad)])

        rel = pts[:, :2] - mirror_center
        dot = np.dot(rel, normal)

        behind_mask = dot > 0
        reflected_pts = pts[behind_mask]

        if reflected_pts.shape[0] == 0:
            return

        rel = reflected_pts[:, :2] - mirror_center
        proj = np.outer(np.dot(rel, normal), normal)
        reflected_pts[:, :2] = reflected_pts[:, :2] - 2 * proj

        reflected_cloud = np.zeros(reflected_pts.shape[0], dtype=pc.dtype)
        reflected_cloud['x'] = reflected_pts[:, 0]
        reflected_cloud['y'] = reflected_pts[:, 1]
        reflected_cloud['z'] = reflected_pts[:, 2]

        msg_out = ros_numpy.point_cloud2.array_to_pointcloud2(
            reflected_cloud,
            stamp=msg.header.stamp,
            frame_id=msg.header.frame_id
        )
        self.pub.publish(msg_out)
        self.publish_mirror_marker()

    def publish_mirror_marker(self):
        marker = Marker()
        marker.header.frame_id = "velodyne"
        marker.header.stamp = rospy.Time.now()
        marker.ns = "mirror"
        marker.id = 0
        marker.type = Marker.LINE_STRIP
        marker.action = Marker.ADD

        # Параметры линии
        marker.scale.x = 0.05  # толщина линии
        marker.color.r = 0.8
        marker.color.b = 0.8
        marker.color.a = 1.0

        # Длина отрезка (в обе стороны от центра зеркала)
        half_len = 1.0

        # Центр и угол (используем правильные поля)
        center_x = self.mirror_center_x
        center_y = self.mirror_center_y
        yaw = np.deg2rad(self.mirror_yaw_deg)

        dx = np.cos(yaw + np.pi / 2) * half_len
        dy = np.sin(yaw + np.pi / 2) * half_len

        pt1 = [center_x - dx, center_y - dy, 0.0]
        pt2 = [center_x + dx, center_y + dy, 0.0]

        from geometry_msgs.msg import Point
        marker.points = [Point(*pt1), Point(*pt2)]

        self.marker_pub.publish(marker)


if __name__ == "__main__":
    MirrorReflector()
