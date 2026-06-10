cmake_minimum_required(VERSION 3.0.2)
project(pointcloud_processor)

## Find catkin macros and libraries
find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  sensor_msgs
  geometry_msgs
)

## Python dependencies are handled via package.xml, not find_package
# catkin_python_setup()

###################################
## catkin specific configuration ##
###################################
catkin_package(
  # INCLUDE_DIRS - оставить пустым для Python-пакетов
  # LIBRARIES - оставить пустым для Python-пакетов
  CATKIN_DEPENDS rospy std_msgs sensor_msgs geometry_msgs
  # DEPENDS system_lib - удалить, если не используется
)

###########
## Build ##
###########
# Для Python скриптов не нужно ничего компилировать

#############
## Install ##
#############

# Устанавливаем Python скрипты
install(PROGRAMS
  scripts/voxel_grid_filter.py
  scripts/pointcloud_filter.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

# Устанавливаем launch-файлы
install(DIRECTORY launch/
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/launch
  PATTERN ".svn" EXCLUDE
)

# Устанавливаем конфиги (если есть)
if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/config)
  install(DIRECTORY config/
    DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/config
    PATTERN ".svn" EXCLUDE
  )
endif()