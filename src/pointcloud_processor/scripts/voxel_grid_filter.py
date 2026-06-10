#!/usr/bin/env python3

import rospy
import numpy as np
import open3d as o3d
import sensor_msgs.point_cloud2 as pc2
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Header

class VoxelGridFilter:
    def __init__(self):
        # Параметры
        self.leaf_size = rospy.get_param("~leaf_size", 0.05)
        self.input_topic = rospy.get_param("~input_topic", "/points_raw")
        self.output_topic = rospy.get_param("~output_topic", "/voxels_filtered")
        
        # Подписчики и издатели
        self.sub = rospy.Subscriber(self.input_topic, PointCloud2, self.cloud_callback, queue_size=10)
        self.pub = rospy.Publisher(self.output_topic, PointCloud2, queue_size=10)
        
        rospy.loginfo("=" * 50)
        rospy.loginfo("Voxel Grid Filter Node Started")
        rospy.loginfo(f"Leaf size: {self.leaf_size} m")
        rospy.loginfo(f"Input topic: {self.input_topic}")
        rospy.loginfo(f"Output topic: {self.output_topic}")
        rospy.loginfo("=" * 50)
    
    def cloud_callback(self, cloud_msg):
        try:
            # Конвертируем ROS message в numpy array
            points = self.ros_to_numpy(cloud_msg)
            
            if len(points) == 0:
                rospy.logwarn("Received empty point cloud")
                return
            
            rospy.loginfo(f"Received cloud with {len(points)} points")
            
            # Применяем воксельную фильтрацию
            filtered_points = self.voxel_grid_filter(points)
            
            # Конвертируем обратно в ROS message
            filtered_msg = self.numpy_to_ros(filtered_points, cloud_msg.header)
            
            # Публикуем
            self.pub.publish(filtered_msg)
            
            # Логирование
            reduction = (1.0 - len(filtered_points) / len(points)) * 100
            rospy.loginfo(f"Filtered: {len(points)} -> {len(filtered_points)} points ({reduction:.1f}% reduction)")
            
        except Exception as e:
            rospy.logerr(f"Error processing cloud: {e}")
    
    def ros_to_numpy(self, cloud_msg):
        """Конвертирует ROS PointCloud2 в numpy array"""
        # Получаем генератор точек
        points_gen = pc2.read_points(cloud_msg, field_names=("x", "y", "z"), skip_nans=True)
        # Конвертируем в список и затем в numpy
        points_list = list(points_gen)
        return np.array(points_list, dtype=np.float32)
    
    def voxel_grid_filter(self, points):
        """Применяет воксельную фильтрацию с помощью Open3D"""
        # Создаём open3d облако
        o3d_cloud = o3d.geometry.PointCloud()
        o3d_cloud.points = o3d.utility.Vector3dVector(points.astype(np.float64))
        
        # Воксельная фильтрация
        downsampled = o3d_cloud.voxel_down_sample(self.leaf_size)
        
        # Возвращаем как numpy
        return np.asarray(downsampled.points, dtype=np.float32)
    
    def numpy_to_ros(self, points, header):
        """Конвертирует numpy array в ROS PointCloud2"""
        # Убеждаемся, что точки в правильном формате
        if points.dtype != np.float32:
            points = points.astype(np.float32)
        
        # Создаём сообщение
        return pc2.create_cloud_xyz32(header, points)

if __name__ == '__main__':
    try:
        # Инициализация ноды
        rospy.init_node('voxel_grid_filter', anonymous=False)
        
        # Создаём объект фильтра
        filter_node = VoxelGridFilter()
        
        # Держим ноду запущенной
        rospy.spin()
        
    except rospy.ROSInterruptException:
        rospy.loginfo("Node terminated")
    except Exception as e:
        rospy.logfatal(f"Failed to start node: {e}")