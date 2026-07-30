# Collecting and saving a map: what the launch entry actually starts

## Task and learning goals

This stage composes sensors, odometry, and SLAM into a live system and saves `/map` for later use. Launch is orchestration; SLAM is the estimation process. Odometry provides short-term continuity, while scan matching and loop constraints reduce accumulated drift.

The entry command is:

```bash
ros2 launch go2_core go2_start.launch.py
```

`ros2 launch` locates the installed package share directory, loads the Python launch file, and calls its `generate_launch_description()` function. The returned `LaunchDescription` is an orchestration plan, not the mapping algorithm itself.

## `get_package_share_directory`

```python
go2_driver_pkg = get_package_share_directory("go2_driver")
go2_core_pkg = get_package_share_directory("go2_core")
go2_slam_pkg = get_package_share_directory("go2_slam")
```

The ament index records where built and installed packages place launch, configuration, and resource files. This avoids hard-coded workspace paths. If the workspace `install/setup.bash` has not been sourced, its packages are absent from the active ament index.

## `IncludeLaunchDescription`

The top-level launch reuses subsystem launch files:

```python
go2_pointcloud_launch = IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        os.path.join(
            go2_perception_pkg,
            "launch",
            "go2_pointcloud.launch.py",
        )
    )
)
```

This is composition. The main file expresses system structure while each child launch owns one subsystem. The point-cloud pipeline can therefore run independently or as part of mapping.

## Launch arguments and conditions

```python
use_slamtoolbox = DeclareLaunchArgument(
    name="use_slamtoolbox",
    default_value="true",
)
```

A user can override it on the command line. `IfCondition(LaunchConfiguration(...))` then decides whether the SLAM subsystem is included. A launch argument changes the process graph; a ROS parameter configures a node after it is created.

## The actual LaunchDescription

```python
return LaunchDescription([
    go2_driver_launch,
    use_slamtoolbox,
    go2_robot_localization,
    go2_pointcloud_launch,
    go2_slamtoolbox_launch,
    rviz_node,
])
```

[Open the complete `go2_start.launch.py`](https://github.com/rbgyhjn/go2-nav2-amcl/blob/8a022d5ca389af2a9b793849e28956992f6a52a5/src/base/go2_core/launch/go2_start.launch.py)

The subsystems provide driver data, continuous motion estimation, `/scan`, `slam_toolbox`, and visualization.

## Calling the official `online_async_launch.py`

The project includes the launch interface shipped by `slam_toolbox` and passes a project configuration file:

```python
slam_toolbox_launch = IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        os.path.join(
            get_slam_toolbox_pkg,
            "launch",
            "online_async_launch.py",
        )
    ),
    launch_arguments=[
        ("slam_params_file", slam_toolbox_config),
        ("use_sim_time", "false"),
    ],
)
```

[Open the complete `go2_slamtoolbox.launch.py`](https://github.com/rbgyhjn/go2-nav2-amcl/blob/8a022d5ca389af2a9b793849e28956992f6a52a5/src/go2_slam/launch/go2_slamtoolbox.launch.py)

“Online” means the map is updated as data arrives. “Async” refers to the package's asynchronous processing arrangement. The project configures the official node rather than reimplementing scan matching and graph optimization.

```yaml
slam_toolbox:
  ros__parameters:
    odom_frame: odom
    map_frame: map
    base_frame: base_link
    scan_topic: /scan
    resolution: 0.05
```

[Open the real parameter file](https://github.com/rbgyhjn/go2-nav2-amcl/blob/8a022d5ca389af2a9b793849e28956992f6a52a5/src/go2_slam/config/mapper_params_online_async.yaml)

At a functional level, `slam_toolbox` consumes scans and motion estimates, aligns observations, builds and optimizes pose/scan constraints, projects the result into `/map`, and maintains the relevant map relationship.

## Why collection still uses manual driving

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

The teleoperation node converts key presses into `geometry_msgs/Twist`. The operator chooses the coverage path while SLAM estimates and builds the map. Excessive speed, abrupt turns, repetitive corridors, weak loop closure, and missing coverage can all reduce map quality.

## What `map_saver_cli` does

```bash
ros2 run nav2_map_server map_saver_cli \
  -f /home/unitree/go2_guide_project/maps/floor_3/floor_3
```

This executable subscribes to `/map`, waits for an `OccupancyGrid`, and writes PGM plus YAML. It does not rerun SLAM or optimize the map. See [Map data models](map-data-model.md) for resolution, origin, and thresholds.

## The two Floor 3 acquisitions

The first pass verified the pipeline. The second was collected more deliberately and became the basis for operational boundaries, semantic annotation, and planner validation. The historical name `recovered` does not mean recovery from a corrupted file or rosbag.

## Official references

- [ROS 2 Launch tutorials](https://docs.ros.org/en/foxy/Tutorials/Intermediate/Launch/Launch-Main.html)
- [slam_toolbox documentation](https://docs.ros.org/en/ros2_packages/humble/api/slam_toolbox/)
- [Nav2 Map Server](https://docs.nav2.org/configuration/packages/map_server/configuring-map-server.html)

## Why SLAM is not “drawing points on an image”

Simply placing scans according to odometry accumulates error and produces duplicated or shifted walls. SLAM combines local scan matching with longer-range constraints such as loop closures, then optimizes the trajectory before projecting it into an occupancy grid.

`online` means processing while the robot moves. `async` avoids making every scan block the entire executor; it does not remove the need for consistent timestamps and TF.

Before saving, inspect `/scan`, `/map`, and `odom → base_link`. After saving, verify YAML paths, resolution, origin, and successful reload through `map_server`.
