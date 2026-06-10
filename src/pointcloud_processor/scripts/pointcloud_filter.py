#!/home/vsadnik/venv/bin/python3

import rospy
import numpy as np
import open3d as o3d
import sensor_msgs.point_cloud2 as pc2
from sensor_msgs.msg import PointCloud2
import ros_numpy

class PointCloudFilter:
    def __init__(self):
        # Params 
        self.input_topic = rospy.get_param("~input_topic", "/points_raw")
        self.output_topic = rospy.get_param("~output_topic", "/points_filtered")
        self.output_plane_topic = rospy.get_param("~output_plane_topic", "/points_plane")
        filters_str = rospy.get_param("~filters", "vr")

        # Accumulation params
        self.accumulation_time = rospy.get_param("~accumulation_time", 1.0)
        self.max_points = rospy.get_param("~max_points", 1_000_000)


        # Voxel params
        voxel_leaf_size = rospy.get_param("~voxel_leaf_size", 0.05)

        # Ransac params
        ransac_distance_threshold = rospy.get_param("~ransac_distance_threshold", 0.02)
        ransac_max_iterations = rospy.get_param("~ransac_max_iterations", 1000)
        ransac_publish_mode = rospy.get_param("~ransac_publish_mode", "objects")  # 'objects', 'plane', 'both'
        ransac_min_points = rospy.get_param("~ransac_min_points", 100)
        ransac_min_plane_points = rospy.get_param("~ransac_min_plane_points", 500)
        ransac_min_inlier_ratio = rospy.get_param("~ransac_min_inlier_ratio", 0.05)

        self.filters = self.create_filters(
            filters_str,
            voxel_leaf_size,
            ransac_distance_threshold,
            ransac_max_iterations,
            ransac_publish_mode,
            ransac_min_points,
            ransac_min_plane_points,
            ransac_min_inlier_ratio
        )

        # Accumulation variables
        self.accumulated_points = []
        self.last_reset_time = rospy.Time.now()
        self.is_processing = False

        # Publishers & Subscribers
        self.sub = rospy.Subscriber(self.input_topic, PointCloud2, self.cloud_callback, queue_size = 10)
        self.pub = rospy.Publisher(self.output_topic, PointCloud2, queue_size=10)
        self.pub_plane = rospy.Publisher(self.output_plane_topic, PointCloud2, queue_size=10)

        self.print_configuration()


    def print_configuration(self):
        rospy.loginfo("=" * 60)
        rospy.loginfo("Pointcloud_filter Node Started")
        
        # Params
        rospy.loginfo(f"Input topic: {self.input_topic}")
        rospy.loginfo(f"Output topic: {self.output_topic}")
        rospy.loginfo(f"Output plane topic: {self.output_plane_topic}")
        rospy.loginfo(f"Accumulation time: {self.accumulation_time}")
        rospy.loginfo(f"Max points: {self.max_points}")

        #Filters
        rospy.loginfo("Filters: ")
        
        for i, filter_obj in enumerate(self.filters):
            rospy.loginfo(f"\t {i+1}: {filter_obj.__class__.__name__}")
        
        rospy.loginfo("=" * 60)


    def create_filters(self, filters_str, voxel_leaf_size, ransac_distance_threshold, 
                   ransac_max_iterations, ransac_publish_mode, ransac_min_points, ransac_min_plane_points, ransac_min_inlier_ratio):
        """Создает список фильтров на основе строки filters_str"""
        
        filter_registry = {
        'v': {
            'class': VoxelGridFilter,
            'params': {'leaf_size': voxel_leaf_size}
        },
        'r': {
            'class': RansacFilter,
            'params': {
                'distance_threshold': ransac_distance_threshold,
                'max_iterations': ransac_max_iterations,
                'publish_mode': ransac_publish_mode,
                'min_points': ransac_min_points,
                'min_plane_points': ransac_min_plane_points,
                'min_inlier_ratio': ransac_min_inlier_ratio
                }
            }
        }
    
        filters = []
        
        # Последовательно перебираем каждый символ в строке
        for char in filters_str.lower():
            if char in filter_registry:
                # Создаем экземпляр фильтра с его параметрами
                filter_class = filter_registry[char]['class']
                filter_params = filter_registry[char]['params']
                filter_instance = filter_class(**filter_params)
                filters.append(filter_instance)
            else:
                rospy.logwarn(f"Unknown filter character '{char}' in filters string, skipping")
        
        if not filters:
            rospy.logwarn(f"No valid filters found in '{filters_str}', using default 'vr'")
            
            # Добавляем фильтр по умолчанию
            voxel_filter = VoxelGridFilter(leaf_size=voxel_leaf_size)
            ransac_filter = RansacFilter(
                distance_threshold=ransac_distance_threshold,
                max_iterations=ransac_max_iterations,
                publish_mode=ransac_publish_mode,
                min_points=ransac_min_points,
                min_plane_points=ransac_min_plane_points,
                min_inlier_ratio=ransac_min_inlier_ratio
            )

            filters.append(voxel_filter)
            filters.append(ransac_filter)
        
        return filters

    def cloud_callback(self, cloud_msg):
        """Основной callback для обработки облака точек"""
        
        if self.is_processing:
            # Пропускаем новые сообщения во время обработки
            return

        try:
            # Конвертируем ROS message в numpy array
            points = self.ros_to_numpy(cloud_msg)

            if len(points) == 0:
                rospy.logwarn("Received empty point cloud")
                return
            
            # Добавляем точки в буфер
            self.accumulated_points.append(points)

            # Проверяем, не пора ли обработать накопленные данные
            current_time = rospy.Time.now()
            elapsed_time = (current_time - self.last_reset_time).to_sec()

            # Проверяем общее количество точек
            total_points = sum(len(p) for p in self.accumulated_points)

            if elapsed_time >= self.accumulation_time or total_points >= self.max_points:
                self.process_accumulated_data(cloud_msg.header)
            
        except Exception as e:
            rospy.logerr(f"Error processing cloud: {e}")


    def process_accumulated_data(self, header):
        """Обрабатывает накопленные облака точек"""

        if self.is_processing:
            return
        
        self.is_processing = True

        try:
            # Объединяем все накопленные облака
            if not self.accumulated_points:
                rospy.logwarn("No accumulated points to process")
                return
            
            # Конкатенируем все точки
            all_points = np.vstack(self.accumulated_points)
            total_points = len(all_points)

            rospy.loginfo(f"Processing accumulated data: {len(self.accumulated_points)} frames, {total_points} total points")

            # Применяем все фильтры последовательно
            filtered_points = all_points
            plane_points = None

            for filter_obj in self.filters:
                if isinstance(filter_obj, VoxelGridFilter):
                    filtered_points = filter_obj.apply(filtered_points)
                    rospy.loginfo(f"After {filter_obj.__class__.__name__}: {len(filtered_points)} points")
                    continue
                
                elif isinstance(filter_obj, RansacFilter):
                    filtered_points, plane_points, _ = filter_obj.apply(filtered_points)
                    rospy.loginfo(f"After {filter_obj.__class__.__name__}: {len(filtered_points)} points")
                    continue
            
            # Публикуем результаты
            self.publish_results(header, filtered_points, plane_points)

            # Очищаем буфер и сбрасываем таймер
            self.accumulated_points = []
            self.last_reset_time = rospy.Time.now()

        except Exception as e:
            rospy.logerr(f"Error processing accumulated data: {e}")
            
            # В случае ошибки очищаем буфер, чтобы не накапливать мусор
            self.accumulated_points = []
            self.last_reset_time = rospy.Time.now()
        
        finally:
            self.is_processing = False


    def publish_results(self, header, filtered_points, plane_points):
        # Публикуем основное облако
        if len(filtered_points) > 0:
            filtered_msg = self.numpy_to_ros(filtered_points, header)
            self.pub.publish(filtered_msg)
        
        # Публикуем облако плоскости если оно есть
        if plane_points is not None and len(plane_points) > 0:
            plane_msg = self.numpy_to_ros(plane_points, header)
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


class VoxelGridFilter:
    def __init__(self, leaf_size):
        self.leaf_size = leaf_size
        rospy.loginfo(f"VoxelGridFilter initialized with leaf_size={leaf_size}")


    def apply(self, points):
        """Применяет воксельную фильтрацию с помощью Open3D"""

        if len(points) == 0:
            return points

        # Создаем open3d облако
        o3d_cloud = o3d.geometry.PointCloud()
        o3d_cloud.points = o3d.utility.Vector3dVector(points.astype(np.float64))

        # Воксельная фильтрация
        downsampled = o3d_cloud.voxel_down_sample(self.leaf_size)

        # Возвращаем как numpy
        return np.asarray(downsampled.points, dtype=np.float32)


class RansacFilter:
    def __init__(self, distance_threshold, max_iterations, publish_mode, min_points, min_plane_points, min_inlier_ratio):
        self.distance_threshold = distance_threshold
        self.max_iterations = max_iterations
        self.publish_mode = publish_mode
        self.min_points = min_points
        self.min_plane_points = min_plane_points
        self.min_inlier_ratio = min_inlier_ratio

        rospy.loginfo(f"RANSACFilter initialized: threshold={distance_threshold}, "
                      f"iterations={max_iterations}, mode={publish_mode}")


    def apply(self, points):
        """Применяет RANSAC для поиска плоскости"""
        
        if len(points) < self.min_points:
            rospy.logwarn("Not enough points for RANSAC (need at least 50 for good result)")
            return points, None, None
        
        # Создаем open3d облако
        o3d_cloud = o3d.geometry.PointCloud()
        o3d_cloud.points = o3d.utility.Vector3dVector(points.astype(np.float64))

        plane_model, inliers = o3d_cloud.segment_plane(
            distance_threshold=self.distance_threshold,
            ransac_n=3,
            num_iterations=self.max_iterations 
        )

        # Плоскости может и не быть, тогда возвращаем точки
        inlier_count = len(inliers)
        inlier_ratio = inlier_count / len(points)

        if (
            inlier_count < self.min_plane_points
            or
            inlier_ratio < self.min_inlier_ratio
        ):
            rospy.logwarn("Plane not found")
            return points, None, None

        # Создаем маску inliers
        inlier_mask = np.zeros(len(points), dtype=bool)
        inlier_mask[inliers] = True

        # Разделяем точки
        plane_points = points[inlier_mask]
        object_points = points[~inlier_mask]

        # В зависимости от режима публикации возвращаем разные данные
        if self.publish_mode == "plane":
            return plane_points, None, plane_model
        
        elif self.publish_mode == "both":
            return object_points, plane_points, plane_model
        
        else:  # objects (default)
            return object_points, None, plane_model

if __name__ == "__main__":
    try:
        rospy.init_node("PointCloudFilter", anonymous=False)
        filter_node = PointCloudFilter()
        rospy.spin()

    except rospy.ROSInterruptException:
        rospy.loginfo("Node terminated")
    
    except Exception as e:
        rospy.logfatal(f"Failed to start node: {e}")


        