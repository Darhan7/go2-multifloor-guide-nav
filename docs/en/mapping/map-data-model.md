# What PointCloud2, LaserScan, and OccupancyGrid contain

## Task and learning goals

This page answers what the messages actually contain. With the data model in mind, it becomes possible to explain why a visible topic may still fail to produce a map, why PGM and YAML belong together, and why image and ROS coordinates use different axis conventions.

The important part of the mapping pipeline is not memorizing three message names, but understanding how the representation changes at each stage.

```text
3D discrete points
PointCloud2
→ height and angle reduction
2D polar range array
LaserScan
→ SLAM plus motion estimate
2D occupancy probability grid
OccupancyGrid
→ persistence
PGM + YAML
```

## `PointCloud2`: a structured batch of 3D points

`PointCloud2` is not an image and is not necessarily only `(x, y, z)`. Each point may contain position, intensity, ring index, timing, or other sensor-specific fields. The message also carries its frame, timestamp, field layout, byte strides, and dimensions.

A consumer must interpret the binary data according to the `fields` description rather than assuming a fixed memory layout.

The project first runs `cloud_accumulation` and remaps its result to `/trans_cloud`. Accumulation can improve spatial coverage, but it also relies on correct timing and transforms; otherwise points collected while the robot moves may be combined in the wrong pose.

## `LaserScan`: ranges indexed by angle

Important fields include:

```text
angle_min
angle_max
angle_increment
ranges[]
range_min
range_max
scan_time
```

The angle represented by element `i` is approximately:

```text
angle_i = angle_min + i × angle_increment
```

`ranges[i]` is the nearest valid obstacle distance in that direction. A planar SLAM system therefore receives a compact description of surrounding boundaries rather than all original 3D points.

## How the cloud becomes a scan

The project configures:

```python
"target_frame": "base_link",
"min_height": 0.1,
"max_height": 0.5,
"angle_min": -3.14,
"angle_max": 3.14,
"angle_increment": 0.0087,
"range_min": 0.0,
"range_max": 10.0,
```

Conceptually, the converter:

1. transforms each point into `base_link`;
2. removes points outside the selected height band;
3. computes horizontal angle with `atan2(y, x)`;
4. computes planar range with `sqrt(x² + y²)`;
5. selects the corresponding angle bin;
6. keeps the nearest point when several points fall in one bin;
7. fills directions with no valid return using the configured empty value.

The height band therefore determines which 3D structures become 2D walls or obstacles. The `0.0087 rad` increment is roughly 0.5 degrees; a finer binning increases array size but cannot recover information the LiDAR never measured.

## `OccupancyGrid`: one occupancy estimate per cell

`nav_msgs/OccupancyGrid` contains map metadata and a flattened cell array. Typical values are:

```text
-1       unknown
0        free
1..99    intermediate probability or cost
100      occupied
```

A static map and a Nav2 costmap are both grids, but they serve different purposes. `/map` represents mapping output, while costmaps may include inflation and live obstacle costs.

## Why the map is saved as PGM plus YAML

`map_saver_cli` writes the grid to a grayscale image and stores metric metadata separately:

```yaml
image: floor_3.pgm
resolution: 0.05
origin: [-31.1969, -6.0832, 0.0]
occupied_thresh: 0.65
free_thresh: 0.25
negate: 0
```

The PGM stores pixels only. The YAML explains how those pixels relate to meters and world coordinates.

- `resolution` is meters per pixel.
- `origin` places the image's lower-left reference in the `map` frame; it is not the robot starting pose.
- occupancy thresholds classify image intensity into free, occupied, and possibly unknown cells.

## World coordinates to image pixels

The preview script uses:

```python
u = int(round((x - origin[0]) / resolution))
v = int(round(height - 1 - (y - origin[1]) / resolution))
```

World y increases upward, while image row indices increase downward, so the vertical axis must be flipped. Incorrect origin or resolution values shift every semantic point and route overlay.

## Why `/map` and the global costmap differ

The global costmap starts with the static map, then adds live scan obstacles, clearing/marking behavior, and inflation costs. Cells that are free in `/map` may therefore hold intermediate costs in the costmap. This represents “traversable but increasingly undesirable near an obstacle”, not a corrupted map.

## Full configuration and official references

- [Project `go2_pointcloud.launch.py`](https://github.com/rbgyhjn/go2-nav2-amcl/blob/8a022d5ca389af2a9b793849e28956992f6a52a5/src/go2_perception/launch/go2_pointcloud.launch.py)
- [Project `pointcloud_to_laserscan_node.cpp`](https://github.com/rbgyhjn/go2-nav2-amcl/blob/8a022d5ca389af2a9b793849e28956992f6a52a5/src/go2_perception/src/pointcloud_to_laserscan_node.cpp)
- [Project `nav2_virtual_preview_3f.py`](../../assets/source/nav2_virtual_preview_3f.py)
- [ROS `sensor_msgs/PointCloud2`](https://docs.ros2.org/foxy/api/sensor_msgs/msg/PointCloud2.html)
- [ROS `sensor_msgs/LaserScan`](https://docs.ros2.org/foxy/api/sensor_msgs/msg/LaserScan.html)
- [ROS `nav_msgs/OccupancyGrid`](https://docs.ros2.org/foxy/api/nav_msgs/msg/OccupancyGrid.html)
- [Nav2 Map Server configuration](https://docs.nav2.org/configuration/packages/map_server/configuring-map-server.html)

## Why `OccupancyGrid.data` is one-dimensional

The 2D grid is flattened row by row:

```text
index = row * width + column
```

`width`, `height`, and `resolution` reconstruct the spatial grid. Code must validate indices rather than infer them from a displayed image.

## A map is not a costmap

The static `/map` stores occupancy. Nav2 costmaps add live obstacles, inflation costs, and unknown-space policy. A white PGM pixel therefore does not guarantee zero cost in the global costmap.

The shared official interfaces—`OccupancyGrid`, `MapMetaData`, `map_saver_cli`, and `map_server`—allow mapping output to flow into localization and navigation without a custom map format.
