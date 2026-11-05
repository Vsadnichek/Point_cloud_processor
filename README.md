# Point Cloud Processor

ROS workspace for point cloud preprocessing and filtering.

## Overview

This project contains ROS Python nodes for:

- voxel grid downsampling
- RANSAC-based plane detection and separation
- DBSCAN clustering of the remaining objects
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

## Processing pipeline

The `pointcloud_processor` package implements the UAV detection pipeline as three
independent nodes chained by topics:

```
  raw LiDAR cloud
        │
        ▼
  voxel_grid_filter.py   ──►  /voxel_cloud   (down-sampled cloud)
        │                 └─►  /dense_cloud   (raw accumulated cloud)
        ▼
  ransac_filter.py       ──►  /objects_cloud (points above the ground plane)
        │                 └─►  /plane_points  (points of the ground plane)
        ▼
  dbscan_cluster.py      ──►  /dbscan_clusters (clusters, colour-coded)
```

The whole pipeline (including RViz) is started with a single command:

```bash
roslaunch pointcloud_processor uav_detection.launch
```

Available arguments: `input_topic`, `voxel_cloud_topic`, `dense_cloud_topic`,
`objects_topic`, `plane_topic`, `voxel_leaf_size`, `voxel_accumulation_frames`,
`ransac_distance_threshold`, `ransac_accumulation_frames`, `ransac_max_iterations`,
`ransac_min_plane_points`, `ransac_min_inlier_ratio`, `dbscan_eps`,
`dbscan_min_samples`.

## Datasets

The recorded data is stored in `datasets/`. Each bag was checked with `rosbag info`
and the actual `frame_id` / point rate / points per frame values are listed below.

| Dataset | Bag | Point cloud topic | `frame_id` | Points per frame | Rate |
|---|---|---|---|---|---|
| `Drone_livox` | `2026-05-28-18-47-11.bag` | `/livox/lidar` | `livox_frame` | 2 400 | 100 Hz |
| `Other` | `rosbag2_2023_03_09-13_42_46.bag` | `/livox/points` | `livox_frame` | 24 000 | 10 Hz |
| `Room` | `1_static.bag`, `1_dynamic.bag`, `2_static.bag`, `2_dynamic.bag` | `/velodyne_points` | `velodyne` | 27 000 – 28 000 | 20 Hz |

`Drone_livox` also contains `/livox/imu`; `Other` additionally contains `/image` and
`/camera_info`.

## RViz: Fixed Frame and ready-made config

### Fixed Frame

RViz only renders a point cloud if the cloud's `frame_id` can be resolved against the
configured **Fixed Frame**. Because the bags were recorded with different sensors,
the Fixed Frame depends on the dataset:

| Dataset | Fixed Frame to set in RViz |
|---|---|
| `Drone_livox` | `livox_frame` |
| `Other` | `livox_frame` |
| `Room` | `velodyne` |

Set it in RViz under **Global Options → Fixed Frame**. If the value does not match
the `frame_id` of the bag, RViz shows the warning
`No transform from [livox_frame] to [Fixed Frame]` and the clouds stay invisible.

All nodes of the pipeline inherit the `frame_id` of the incoming message, so
`/dense_cloud`, `/voxel_cloud`, `/objects_cloud`, `/plane_points` and
`/dbscan_clusters` are published in the same frame as the source bag.

> Note: the `Room` bags contain indoor Velodyne data, where the dominant plane is a
> wall rather than the floor. The RANSAC node rejects planes whose normal is not
> sufficiently vertical (`|c| > 0.8`), so on this dataset no ground plane is
> produced and all points are forwarded to `/objects_cloud`. Use the Livox datasets
> (`Drone_livox`, `Other`) for the ground-plane segmentation scenario.

### Ready-made RViz config

A preconfigured RViz setup is included in the package:

```
src/pointcloud_processor/config/uav_detection.rviz
```

It is already wired to the pipeline topics and is launched automatically by
`uav_detection.launch` (`rviz -d $(find pointcloud_processor)/config/uav_detection.rviz`).
To open it manually:

```bash
rviz -d $(find pointcloud_processor)/config/uav_detection.rviz
```

The config contains the following displays (all of them use the Fixed Frame
`livox_frame`):

| Display | Topic | Enabled by default | Colour |
|---|---|---|---|
| `Livox` | `/livox/lidar` | no | intensity rainbow |
| `DenseCloud` | `/dense_cloud` | no | flat green |
| `Objects` | `/objects_cloud` | no | flat green |
| `Plane` | `/plane_points` | no | flat red |
| `DBSCAN` | `/dbscan_clusters` | **yes** | RGB8 per cluster |

`/dbscan_clusters` is the only display enabled by default. Enable the other displays
in the RViz tree (checkbox in the left panel) to inspect the intermediate stages of
the pipeline.

If you work with the `Room` (Velodyne) bags, either change **Global Options → Fixed
Frame** to `velodyne` after loading the config, or start the pipeline with the
matching input topic:

```bash
roslaunch pointcloud_processor uav_detection.launch input_topic:=/velodyne_points
```

## Scientific article

The article source is [`article.tex`](article.tex) in the repository root.
It uses `misisarticle.cls`, the CSV files in `data/`, and images in `figures/`.

Source: [sadekovlar/misis-article-latex](https://github.com/sadekovlar/misis-article-latex),
revision `7b16e2c99fc8e0eab64be02f10fd2077c956dc6f`.

```bash
make article  # Tectonic: build/latex/article.pdf
make dist     # Overleaf: dist/misis-article.zip
```

With MiKTeX, run `xelatex article.tex` twice from the repository root.
This writes `article.pdf` beside the source. GitHub Actions builds the article
with Tectonic on pushes and pull requests and uploads the PDF as an artifact.
The workflow checks the article only. ROS packages require a separate build
in an environment with ROS Noetic.

## Notes

- The repository does not track `.venv`, `build/`, or `devel/`.
- Script entrypoints use a portable shebang, so they work with the active Python environment on each machine.
