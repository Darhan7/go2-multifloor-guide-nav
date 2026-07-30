# Reproduce the planner-only preview

## Task and learning goals

Call the real Nav2 Planner Server with the motion bridge disabled, obtain a `nav_msgs/Path`, and save it as CSV and PNG. This separates planning validity from physical execution.

This mode calls the real Nav2 `ComputePathToPose` action but does not start the Go2 motion bridge.

In the project Foxy interface, the planner obtains its start pose from TF. The script therefore publishes a temporary `map → base_footprint` transform for the chosen semantic start anchor. It must not be mixed with a live AMCL TF tree.

The actual action client is:

```python
self.client = ActionClient(
    self, ComputePathToPose, "compute_path_to_pose"
)
goal = ComputePathToPose.Goal()
goal.pose = goal_pose
goal.planner_id = "GridBased"
```

After receiving `nav_msgs/Path`, the script writes both CSV coordinates and a PNG overlay. World coordinates are converted with:

```python
u = int(round((x - origin[0]) / resolution))
v = int(round(height - 1 - (y - origin[1]) / resolution))
```

Run:

```bash
cd /home/unitree/go2_nav_official_ws
./floor3_nav_test.sh start
sleep 10
./floor3_nav_test.sh status
python3 scripts/nav2_virtual_preview_3f.py \
  hci_lab_view_test_left elevator_3f_safe
```

Before planning, verify lifecycle and grid content:

```bash
ros2 lifecycle get /planner_server
python3 scripts/check_grids_mixed_qos.py \
  /map /global_costmap/costmap
```

The script currently contains project-specific absolute paths. A reusable version would expose map, semantic YAML, and output directory as arguments or ROS parameters; this site keeps the archived code visible rather than pretending it was already generalized.

## Why Foxy needs a virtual TF start

The planner queries the current pose from TF. Without AMCL or a real robot, the script temporarily publishes `map → base_footprint` as the virtual start. It must not compete with real localization.

PNG supports visual inspection; CSV preserves numeric poses for analysis. Neither proves controller tracking or real-robot safety. Generalization requires parameterizing the map, start, goal, planner ID, output path, resolution, and origin.
