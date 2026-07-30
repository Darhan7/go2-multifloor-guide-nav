# From a 3D point cloud to a 2D LaserScan

## Task and learning goals

This stage converts the Go2 3D LiDAR stream into the `/scan` representation consumed by the 2D navigation stack. The goal is not merely to see a topic: understand why point clouds and scans differ, why TF is involved, what height slicing and angular bins do, and how Launch connects parameters and remappings to the real C++ node.

!!! note
    A `PointCloud2` is roughly a field-described table of 3D points. A `LaserScan` is an angle-indexed ring of ranges. Conversion deliberately discards 3D information to create a representation suitable for 2D algorithms.

The Go2 LiDAR publishes `sensor_msgs/PointCloud2`, while the 2D SLAM, AMCL, and Nav2 obstacle layer used here consume `sensor_msgs/LaserScan`. This is a representation change, not merely a topic rename. See [Map data models](map-data-model.md) first if the message structures are unfamiliar.

```text
/utlidar/cloud
→ cloud_accumulation
→ /trans_cloud
→ pointcloud_to_laserscan_node
→ /scan
→ slam_toolbox / AMCL / Nav2 obstacle layer
```

## What `cloud_accumulation` does

A single cloud contains what the LiDAR observed at one moment. Accumulation combines observations to improve structural coverage. It is not SLAM: it does not create an occupancy grid or estimate global pose. Correct TF and timestamps are essential so points from robot motion are placed consistently.

## How the launch file connects the nodes

```python
Node(
    package="go2_perception",
    executable="cloud_accumulation",
    remappings=[
        ("/utlidar/cloud_accumulated", "/trans_cloud")
    ],
    name="cloud_accumulation_node",
),
Node(
    package="go2_perception",
    executable="pointcloud_to_laserscan_node",
    remappings=[
        ("cloud_in", "/trans_cloud"),
        ("scan", "/scan"),
    ],
    parameters=[{
        "target_frame": "base_link",
        "transform_tolerance": 0.3,
        "min_height": 0.1,
        "max_height": 0.5,
        "angle_min": -3.14,
        "angle_max": 3.14,
        "angle_increment": 0.0087,
        "range_max": 10.0,
    }],
)
```

[Open the complete launch file](https://github.com/rbgyhjn/go2-nav2-amcl/blob/8a022d5ca389af2a9b793849e28956992f6a52a5/src/go2_perception/launch/go2_pointcloud.launch.py)

`package` identifies an installed ROS package in the ament index. `executable` names the installed program. `name` controls the runtime node identity. `parameters` supplies values the node implementation reads. `remappings` connects generic internal interface names to the topics used by this robot; it changes names, not message types or content.

## What the converter does internally

Conceptually:

```text
receive cloud_in
→ look up cloud-frame to base_link TF at the message time
→ transform points
→ filter by z height
→ compute angle with atan2(y, x)
→ compute planar range with hypot(x, y)
→ retain the nearest range per angular bin
→ publish /scan
```

[Open the full C++ file used by the project](https://github.com/rbgyhjn/go2-nav2-amcl/blob/8a022d5ca389af2a9b793849e28956992f6a52a5/src/go2_perception/src/pointcloud_to_laserscan_node.cpp)

## Why the project targets `base_link`

The archived Foxy adaptation changed the target frame from `base_footprint` to `base_link`, and the `slam_toolbox` base frame was changed consistently. This prevents part of the pipeline from requesting a different base frame than another part. `base_footprint` remains in the navigation TF chain through a static link. See [TF and coordinate frames](../system/tf-primer.md).

## Why the height slice shapes the map

```yaml
min_height: 0.1
max_height: 0.5
```

A slice that is too low may include ground or leg-adjacent noise. A slice that is too high may remove low boundaries. A wide slice causes structures at different heights to compete for the nearest range in the same direction. These values depend on sensor mounting and environment.

## Why `transform_tolerance` changed

Clouds and TF updates carry timestamps. The converter needs a transform valid near the cloud time. A very small tolerance can drop usable data when scheduling and transport are delayed. The project value of `0.3 s` is environment-specific and should not be treated as universally optimal.

## Verify each stage

```bash
ros2 topic info /utlidar/cloud
ros2 topic info /trans_cloud
ros2 topic info /scan
ros2 topic hz /scan
ros2 topic echo --once /scan
```

Also verify the sensor-to-body transform. Debug from upstream to downstream and locate the first missing or inconsistent stage.

## Official references

- [Unitree ROS 2](https://github.com/unitreerobotics/unitree_ros2)
- [ROS 2 TF2 tutorials](https://docs.ros.org/en/foxy/Tutorials/Intermediate/Tf2/Tf2-Main.html)
- [PointCloud2 message](https://docs.ros2.org/foxy/api/sensor_msgs/msg/PointCloud2.html)
- [LaserScan message](https://docs.ros2.org/foxy/api/sensor_msgs/msg/LaserScan.html)

## Following the official interfaces downward

The project relies on standard ROS 2 messages and TF APIs. A useful source-reading path is:

```text
sensor_msgs::msg::PointCloud2
→ tf2_ros::Buffer / TransformListener
→ x/y/z point access
→ sensor_msgs::msg::LaserScan
→ publisher->publish(scan)
```

`PointCloud2.data` is a byte array whose `fields` describe offsets and types. Robust C++ code uses field-aware iterators rather than assuming every cloud is an identical packed `x,y,z` array. For each angular bin, the nearest valid range is retained because it is the first obstacle constraining motion in that direction.

A native 2D LiDAR can provide `LaserScan` directly; a depth camera needs another preprocessing path. The transferable contracts are `/scan`, TF, and timing—not the project's exact height limits.
