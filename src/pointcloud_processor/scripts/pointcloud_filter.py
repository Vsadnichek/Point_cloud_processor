#!/home/vsadnik/venv/bin/python3

import rospy
import numpy as np
import open3d as o3d
import sensor_msgs.point_cloud2 as pc2
from sensor_msgs.msg import PointCloud2
import ros_numpy
import time

class PointCloudFilter:
    def __init__(self):
        # Params 
        self.input_topic = rospy.get_param("~input_topic", "/points_raw")
        self.output_dense_topic = rospy.get_param("~output_dense_topic", "/dense_cloud")
        self.output_objects_topic = rospy.get_param("~output_objects_topic", "/points_filtered")
        self.output_plane_topic = rospy.get_param("~output_plane_topic", "/points_plane")

        # Accumulation params
        self.accumulation_frames = rospy.get_param("~accumulation_frames", 50)
        self.raw_buffer = []

        # Voxel grid params
        self.voxel_leaf_size = rospy.get_param("~voxel_leaf_size", 0.3)

        # RANSAC params
        self.ransac_distance_threshold = rospy.get_param("~ransac_distance_threshold", 0.02)
        self.ransac_accumulation_frames = rospy.get_param("~ransac_accumulation_frames", 4)
        self.ransac_max_iterations = rospy.get_param("~ransac_max_iterations", 1000)
        self.ransac_min_plane_points = rospy.get_param("~ransac_min_plane_points", 500)
        self.ransac_min_inlier_ratio = rospy.get_param("~ransac_min_inlier_ratio", 0.05)

        # Phases
        self.phase = 'init' # 'init' -> 'online'
        self.plane_model = None
        self.init_voxel_buffer = [] # буфер вокселизированных облаков для фазы 'init' 
        self.last_header = None # заголовок последнего кадра (для публикации в init-фазе)

        # Publishers & Subscribers
        self.sub = rospy.Subscriber(self.input_topic, PointCloud2, self.cloud_callback, queue_size = 10)
        self.pub_dense = rospy.Publisher(self.output_dense_topic, PointCloud2, queue_size=10)
        self.pub_objects = rospy.Publisher(self.output_objects_topic, PointCloud2, queue_size=10)
        self.pub_plane = rospy.Publisher(self.output_plane_topic, PointCloud2, queue_size=10)

        self.print_configuration()


    def print_configuration(self):
        rospy.loginfo("=" * 60)
        rospy.loginfo("Pointcloud_filter Node Started")
        
        # Params
        rospy.loginfo(f"Input topic: {self.input_topic}")
        rospy.loginfo(f"Output dense topic: {self.output_dense_topic}")
        rospy.loginfo(f"Output objects topic: {self.output_objects_topic}")
        rospy.loginfo(f"Output plane topic: {self.output_plane_topic}")
        rospy.loginfo(f"Accumulation frames: {self.accumulation_frames}")
        rospy.loginfo(f"Voxel leaf size: {self.voxel_leaf_size}")
        rospy.loginfo(f"RANSAC distance threshold: {self.ransac_distance_threshold}")
        rospy.loginfo(f"RANSAC accumulation frames: {self.ransac_accumulation_frames}")
        rospy.loginfo(f"RANSAC max iterations: {self.ransac_max_iterations}")
        rospy.loginfo(f"RANSAC min plane points: {self.ransac_min_plane_points}")
        rospy.loginfo(f"RANSAC min inlier ratio: {self.ransac_min_inlier_ratio}")

        rospy.loginfo("=" * 60)


    def cloud_callback(self, cloud_msg):
        """Основной callback для обработки облака точек"""
        try:
            points = self.ros_to_numpy(cloud_msg)
            if len(points) == 0:
                return

            self.raw_buffer.append(points)
            self.last_header = cloud_msg.header

            if len(self.raw_buffer) >= self.accumulation_frames:
                self.process_dense_cloud()
        
        except Exception as e:
            rospy.logerr(f"Error in cloud_callback: {e}")
        

    def process_dense_cloud(self):
        t_start = time.time()
        # 1. Собрать накопленные кадры в одно плотное облако
        merged_raw = np.vstack(self.raw_buffer)
        self.raw_buffer = [] # очищаем буфер

        rospy.loginfo(f"Dense cloud: {len(merged_raw)} points from {self.accumulation_frames} frames")
        
        # 2. Всегда публиковать сырое плотное облако (отдельный топик)
        if self.last_header is not None and len(merged_raw) > 0:
            dense_msg = self.numpy_to_ros(merged_raw, self.last_header)
            self.pub_dense.publish(dense_msg)


        # 3. Применить воксельный фильтр
        voxelized = self.apply_voxel_grid(merged_raw)


        # 4. Фазы инициализации RANSAC и обработки
        if self.phase == 'init':
            # Копим вокселизированное облако в буфер
            self.init_voxel_buffer.append(voxelized)
            rospy.loginfo(f"Init: {len(self.init_voxel_buffer)}/{self.ransac_accumulation_frames} voxelized frames")
        
            if len(self.init_voxel_buffer) >= self.ransac_accumulation_frames:
                # Запускаем RANSAC один раз
                self.ransac_find_plane()
            # В init-фазе разделённые облака не публикуем (нет модели)
            return
        
        # 5. Online-фаза: у нас уже есть модель плоскости
        if self.plane_model is not None:
            plane_points, objects_points = self.split_by_plane(voxelized)
        
        else: 
            # если плоскость не нашлась
            plane_points = np.empty((0, 3), dtype=np.float32)
            objects_points = voxelized

        # 6. Публикуем два вокселизированных облака + сырое уже опубликовано
        self.publish_results(objects_points, plane_points)

        t_end = time.time()
        rospy.loginfo(f"Processing time: {(t_end - t_start)*1000:.1f} ms")
        rospy.loginfo("=" * 60)

    def apply_voxel_grid(self, points):
        """Применяет воксельную фильтрацию с помощью Open3D"""

        if len(points) == 0:
            return points

        # Создаем open3d облако
        o3d_cloud = o3d.geometry.PointCloud()
        o3d_cloud.points = o3d.utility.Vector3dVector(points.astype(np.float64))

        # Воксельная фильтрация
        downsampled = o3d_cloud.voxel_down_sample(self.voxel_leaf_size)

        # Возвращаем как numpy
        return np.asarray(downsampled.points, dtype=np.float32)


    def ransac_find_plane(self):
        merged_vox = np.vstack(self.init_voxel_buffer)
        rospy.loginfo(f"Running RANSAC on {len(merged_vox)} points from {len(self.init_voxel_buffer)} frames")

        # Создаем open3d облако
        o3d_cloud = o3d.geometry.PointCloud()
        o3d_cloud.points = o3d.utility.Vector3dVector(merged_vox.astype(np.float64))

        try:
            plane_model, inliers = o3d_cloud.segment_plane(
            distance_threshold=self.ransac_distance_threshold,
            ransac_n=3,
            num_iterations=self.ransac_max_iterations 
            )
        
        except Exception as e:
            rospy.logerr(f"RANSAC failed: {e}")
            self.init_voxel_buffer = []
            return

        # Плоскости может и не быть, тогда возвращаем точки
        inlier_count = len(inliers)
        inlier_ratio = inlier_count / len(merged_vox)

        if (
            inlier_count < self.ransac_min_plane_points
            or
            inlier_ratio < self.ransac_min_inlier_ratio
        ):
            self.publish_results(
            objects_points=merged_vox,
            plane_points=np.empty((0, 3), dtype=np.float32)
            )
            # Переходим в online-фазу БЕЗ модели плоскости
            self.phase = 'online'
            self.plane_model = None
            self.init_voxel_buffer = []
            return

        
        self.plane_model = plane_model
        rospy.loginfo(f"Plane found: {plane_model}")
        
        # Публикуем первый результат
        plane_pts, objects_pts = self.split_by_plane(merged_vox)
        self.publish_results(objects_pts, plane_pts)

        self.phase = 'online'
        self.init_voxel_buffer = []  # больше не нужен


    def split_by_plane(self, points):
        a, b, c, d = self.plane_model
        distances = np.abs(np.dot(points, [a, b, c]) + d)
        plane_mask = distances < self.ransac_distance_threshold
        return points[plane_mask], points[~plane_mask]


    def publish_results(self, objects_points, plane_points):
        if self.last_header is None:
            return
        
        # Публикуем основное облако
        if len(objects_points) > 0:
            objects_msg = self.numpy_to_ros(objects_points, self.last_header)
            rospy.loginfo(f"Objects cloud: {len(objects_points)} points")
            self.pub_objects.publish(objects_msg)
        
        # Публикуем облако плоскости если оно есть
        if len(plane_points) > 0:
            plane_msg = self.numpy_to_ros(plane_points, self.last_header)
            rospy.loginfo(f"Plane cloud: {len(plane_points)} points")
            self.pub_plane.publish(plane_msg)


    def ros_to_numpy(self, cloud_msg):
        
        xyz_array = ros_numpy.point_cloud2.pointcloud2_to_xyz_array(cloud_msg, remove_nans=True)
        return xyz_array
        

    def numpy_to_ros(self, points, header):
        """Конвертирует nampy array в ROS PointCloud2"""
        
        # Убеждаемся, что точки в правильном формате
        if points.dtype != np.float32:
            points = points.astype(np.float32)

        # Создаем сообщение
        return pc2.create_cloud_xyz32(header, points)


if __name__ == "__main__":
    try:
        rospy.init_node("PointCloudFilter", anonymous=False)
        filter_node = PointCloudFilter()
        rospy.spin()

    except rospy.ROSInterruptException:
        rospy.loginfo("Node terminated")
    
    except Exception as e:
        rospy.logfatal(f"Failed to start node: {e}")