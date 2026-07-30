# How to read the code in this project

A ROS 2 repository can be confusing at first because launch files, YAML configuration, shell scripts, and Python/C++ nodes all appear side by side. They solve different problems. Read [ROS 2 building blocks](ros2-primer.md) and [TF and coordinate frames](tf-primer.md) first if the API names are unfamiliar. The walkthroughs use a four-part pattern: what the object is, why it exists, what the call actually does, and what role it plays in this project.

## Launch files describe which nodes should run

The real `go2_start.launch.py` composes existing subsystems:

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

A launch file is an executable system diagram. It starts nodes and includes other launch files; it does not implement SLAM itself.

## YAML separates runtime choices from algorithms

```yaml
planner_server:
  ros__parameters:
    planner_plugins: [GridBased]
    GridBased:
      plugin: nav2_navfn_planner/NavfnPlanner
      tolerance: 0.5
      use_astar: false
```

The algorithm is provided by a plugin. YAML selects that plugin and configures it without recompiling C++.

## Shell scripts orchestrate repeatable workflows

```bash
nohup ros2 run nav2_map_server map_server --ros-args \
  -p yaml_filename:=$MAP \
  > $LOG_DIR/map_server.log 2>&1 &
echo $! > $LOG_DIR/map_server.pid
```

The script runs the node in the background, records logs, stores the PID, and later stops the exact process. This is operational glue rather than a new navigation algorithm.

## Python/C++ nodes contain message-processing logic

```python
self.compute_client = ActionClient(
    self, ComputePathToPose, "compute_path_to_pose"
)
self.follow_client = ActionClient(
    self, FollowPath, "follow_path"
)
```

This node reads TF, constructs ROS messages, calls actions, and checks results.

A useful reading order is:

```text
shell workflow
→ launch composition
→ YAML parameters and plugins
→ Python/C++ message logic
```

All walkthrough snippets in this site come from the archived project files. Repetitive logging and unrelated branches may be omitted so that the central idea stays visible. Key calls are also explained at the API level—for example what endpoint `create_subscription()` creates, what direction `lookup_transform()` queries, why `send_goal_async()` returns a future, and what lifecycle servers prepare before becoming active.

Official references:

- [ROS 2 Foxy Tutorials](https://docs.ros.org/en/foxy/Tutorials.html)
- [Nav2 Concepts](https://docs.nav2.org/concepts/)
- [Unitree ROS 2](https://github.com/unitreerobotics/unitree_ros2)

## Six questions for unfamiliar ROS code

Ask what kind of file it is, which package and node names it uses, which publishers/subscriptions/services/actions/TF objects it creates, what triggers callbacks, where parameters and remappings enter, and how failure is reported. These answers place the file in the system before every algorithmic detail is understood.
