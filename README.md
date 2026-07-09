# Point Cloud Processor

ROS workspace for point cloud preprocessing and filtering.

## Overview

This project contains ROS Python nodes for:

- voxel grid downsampling
- RANSAC-based plane detection and separation
- dense cloud accumulation and publishing

The Python dependencies are managed with a local virtual environment in `.venv`, while ROS packages such as `rospy` and `sensor_msgs` are provided by ROS Noetic.

## Requirements

- Ubuntu with ROS Noetic
- Python 3.8
- `python3-venv`

## Quick start

1. Go to the workspace root:

	```bash
	cd /home/vsadnik/catkin_ws
	```

2. Source ROS and activate the project virtual environment:

	```bash
	source /opt/ros/noetic/setup.bash
	source .venv/bin/activate
	```

3. Install Python dependencies:

	```bash
	pip install -r src/pointcloud_processor/requirements.txt
	```

4. Build the workspace:

	```bash
	catkin_make
	```

5. Source the workspace setup:

	```bash
	source devel/setup.bash
	```

6. Run the node you need, for example:

	```bash
	rosrun pointcloud_processor voxel_grid_filter.py
	```

## Notes

- The repository does not track `.venv`, `build/`, or `devel/`.
- Script entrypoints use a portable shebang, so they work with the active Python environment on each machine.
