# Nav2 configuration: plugins and costmaps

## Task and learning goals

YAML is not a bag of numbers that should never be touched. It separates node names, ROS parameters, plugin types, and scene-specific values. Understanding the hierarchy explains why a parameter may silently fail to apply and which layer should change for another robot.

The planner server loads an algorithm plugin:

```yaml
planner_plugins: ["GridBased"]
GridBased:
  plugin: nav2_navfn_planner/NavfnPlanner
  tolerance: 0.5
  use_astar: false
  allow_unknown: true
```

The same alias is used by the action client:

```python
goal.planner_id = "GridBased"
```

The global costmap covers the map and combines static, live obstacle, and inflation layers. The local costmap is a rolling `3 m × 3 m` window in `odom` used by the controller.

```text
static_layer    ← occupancy map
obstacle_layer  ← /scan
inflation_layer ← safety cost around obstacles
```

The archived DWB controller configuration samples candidate velocities and scores them with critics such as `BaseObstacle`, `PathDist`, and `GoalDist`.

The planner is explicitly renamed when launched:

```bash
ros2 run nav2_planner planner_server --ros-args \
  -r __node:=planner_server \
  --params-file $NAV_CFG
```

This aligns the process name with the YAML namespace and lifecycle manager target. Without that alignment, a process can be running while the intended parameters are applied to a different node name.

`check_grids_mixed_qos.py` uses transient-local durability for `/map` and volatile durability for the costmap, then counts occupied, free, unknown, and inflated values. This checks content rather than merely confirming that a topic name exists.

See [Nav2 Concepts](https://docs.nav2.org/concepts/) and the [Configuration Guide](https://docs.nav2.org/configuration/).

## Parameter hierarchy and node names

```yaml
planner_server:
  ros__parameters:
    planner_plugins: ["GridBased"]
```

The outer key must match the runtime node name. A process can run while reading defaults if its parameters are stored under another name, which is why the project explicitly remaps the planner node name.

`GridBased` is an instance ID, `nav2_navfn_planner/NavfnPlanner` is a pluginlib class identifier, and the action goal's `planner_id` selects the instance. They are related but not interchangeable.

Record tuning changes by category and keep before/after artifacts. Robot geometry, inflation preference, gait motion, sensing error, and stopping distance are distinct safety considerations.
