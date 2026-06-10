cmake_minimum_required(VERSION 3.0.2)
project(mirror_live_node)

find_package(catkin REQUIRED COMPONENTS
  rospy
  sensor_msgs
  std_msgs
  dynamic_reconfigure
  velodyne_pointcloud
)

generate_dynamic_reconfigure_options(
  cfg/MirrorParams.cfg
  cfg/FilterBox.cfg
)

catkin_package()

catkin_install_python(PROGRAMS
  scripts/mirror_reflector_node.py
  scripts/cloud_filter_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
