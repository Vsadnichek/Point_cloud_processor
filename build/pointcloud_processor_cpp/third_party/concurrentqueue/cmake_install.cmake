# Install script for directory: /home/vsadnik/catkin_ws/src/pointcloud_processor_cpp/third_party/concurrentqueue

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/home/vsadnik/catkin_ws/install")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "RelWithDebInfo")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Install shared libraries without execute permission?
if(NOT DEFINED CMAKE_INSTALL_SO_NO_EXE)
  set(CMAKE_INSTALL_SO_NO_EXE "1")
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xDevelx" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/concurrentqueue/concurrentqueueTargets.cmake")
    file(DIFFERENT EXPORT_FILE_CHANGED FILES
         "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/concurrentqueue/concurrentqueueTargets.cmake"
         "/home/vsadnik/catkin_ws/build/pointcloud_processor_cpp/third_party/concurrentqueue/CMakeFiles/Export/lib/cmake/concurrentqueue/concurrentqueueTargets.cmake")
    if(EXPORT_FILE_CHANGED)
      file(GLOB OLD_CONFIG_FILES "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/concurrentqueue/concurrentqueueTargets-*.cmake")
      if(OLD_CONFIG_FILES)
        message(STATUS "Old export file \"$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/concurrentqueue/concurrentqueueTargets.cmake\" will be replaced.  Removing files [${OLD_CONFIG_FILES}].")
        file(REMOVE ${OLD_CONFIG_FILES})
      endif()
    endif()
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/concurrentqueue" TYPE FILE FILES "/home/vsadnik/catkin_ws/build/pointcloud_processor_cpp/third_party/concurrentqueue/CMakeFiles/Export/lib/cmake/concurrentqueue/concurrentqueueTargets.cmake")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xDevelx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/concurrentqueue" TYPE FILE FILES
    "/home/vsadnik/catkin_ws/build/pointcloud_processor_cpp/third_party/concurrentqueue/concurrentqueueConfig.cmake"
    "/home/vsadnik/catkin_ws/build/pointcloud_processor_cpp/third_party/concurrentqueue/concurrentqueueConfigVersion.cmake"
    )
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/concurrentqueue/moodycamel" TYPE FILE FILES
    "/home/vsadnik/catkin_ws/src/pointcloud_processor_cpp/third_party/concurrentqueue/blockingconcurrentqueue.h"
    "/home/vsadnik/catkin_ws/src/pointcloud_processor_cpp/third_party/concurrentqueue/concurrentqueue.h"
    "/home/vsadnik/catkin_ws/src/pointcloud_processor_cpp/third_party/concurrentqueue/lightweightsemaphore.h"
    "/home/vsadnik/catkin_ws/src/pointcloud_processor_cpp/third_party/concurrentqueue/LICENSE.md"
    )
endif()

