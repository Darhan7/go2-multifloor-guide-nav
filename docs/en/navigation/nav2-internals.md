# How Nav2 is divided internally

## Task and learning goals

This page opens Nav2's black box into servers, plugins, costmaps, lifecycle states, and actions. The goal is to classify failures as planning, control, environmental representation, coordinate transforms, or robot adaptation.

“Starting Nav2” does not launch one monolithic algorithm. Nav2 is a collection of lifecycle servers, algorithm plugins, costmaps, and action interfaces. Understanding those layers makes it possible to identify whether a failure belongs to mapping, planning, control, or the robot-specific bridge.

## Server and plugin are different layers

The Planner Server exposes planning actions, owns the global costmap, loads planner plugins, and dispatches each goal to the requested plugin. The Controller Server exposes path-following actions, owns the local costmap, loads controller plugins, and publishes velocity commands.

The project configures:

```yaml
planner_plugins: ["GridBased"]

GridBased:
  plugin: nav2_navfn_planner/NavfnPlanner
```

`GridBased` is the instance ID used by this configuration. `NavfnPlanner` is the actual plugin implementation. The same pattern applies to the controller:

```yaml
controller_plugins: ["FollowPath"]

FollowPath:
  plugin: dwb_core::DWBLocalPlanner
```

A different plugin can be selected without rewriting the action client as long as it implements the same Nav2 interface.

## Lifecycle nodes: why a running process may still be unusable

Managed Nav2 servers move through states such as:

```text
unconfigured → inactive → active
```

During configuration, a server reads parameters, constructs plugins and costmaps, and creates communication interfaces. Activation enables the server to process tasks and publish through lifecycle-aware publishers.

A process visible in `ps` is not necessarily active. The project checks:

```bash
ros2 lifecycle get /planner_server
```

and uses a lifecycle manager to request the required transitions.

## Costmap: the traversability cost space

A costmap assigns a cost to each cell rather than merely displaying black and white pixels. Low cost is preferred, high cost indicates danger or proximity to obstacles, lethal cost is blocked, and unknown handling depends on configuration.

- The static layer reads the occupancy map.
- The obstacle layer marks and clears live scan obstacles.
- The inflation layer creates a decaying cost field around obstacles.

The global costmap supports route planning over the map. The local rolling costmap supports short-horizon collision-aware control around the robot.

## What `ComputePathToPose` returns

The project sends:

```python
goal = ComputePathToPose.Goal()
goal.pose = goal_pose
goal.planner_id = "GridBased"
```

The result is primarily a `nav_msgs/Path`, which contains a sequence of `PoseStamped` entries. It is geometric path data, not motor control and not a command that moves the robot.

### `wait_for_server`

```python
self.compute_client.wait_for_server(timeout_sec=10.0)
```

This checks whether a compatible action server is discoverable. It does not prove that the costmap is ready or that the requested path is feasible.

### `send_goal_async`

```python
future = self.compute_client.send_goal_async(goal)
```

This initiates communication and returns immediately with a future. ROS events must continue to be processed for acceptance and results to arrive.

### Goal handle and result future

The goal handle identifies the task and reports acceptance. Acceptance is not success. The final planning result arrives through another future returned by `get_result_async()`.

## How `FollowPath` becomes velocity commands

```python
goal = FollowPath.Goal()
goal.path = path
goal.controller_id = "FollowPath"
```

A DWB control cycle conceptually:

1. reads the current robot pose and local costmap;
2. samples candidate linear and angular velocities;
3. forward-simulates each candidate over `sim_time`;
4. scores trajectories with critics;
5. selects a collision-free candidate with a favorable score;
6. publishes `geometry_msgs/Twist` on `/cmd_vel`;
7. repeats on the next control cycle.

DWB is therefore a closed-loop local controller, not a one-time conversion of the entire path into a fixed speed table.

## What a `Twist` contains

```text
geometry_msgs/Twist
├── linear.x, y, z
└── angular.x, y, z
```

For planar motion, `linear.x` is forward speed in meters per second and `angular.z` is yaw rate in radians per second. Nav2 publishes a robot-neutral velocity command. The project still requires `go2_twist_bridge` to translate that command into the Unitree motion request interface.

## Why planning, control, and bridging are debugged separately

```text
ComputePathToPose succeeds
= map, start/goal, global costmap, and planner are broadly functional

FollowPath is accepted but no /cmd_vel appears
= controller, local costmap, or TF still needs investigation

/cmd_vel exists but Go2 does not move
= bridge, Unitree API, gait state, or effective speed threshold is the next layer
```

The project deliberately separates planning and following actions to preserve this diagnostic boundary.

## QoS and invisible delivery failures

DDS endpoints must be compatible in both message type and QoS. A static map commonly uses transient-local durability, while live sensor streams use volatile durability. The diagnostic code creates an explicit profile for `/map`:

```python
QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)
```

An incompatible subscriber may see the topic name but never receive the retained map sample.

## How to approach the official server source

Nav2 planner and controller servers are lifecycle nodes that load algorithm classes through pluginlib. Therefore the YAML `plugin:` value is not a decorative label; it identifies a registered C++ plugin type.

A useful source-reading path is:

```text
constructor
→ on_configure
→ plugin loader
→ action callback
→ costmap and pose lookup
→ createPlan or computeVelocityCommands
→ action result
```

This reveals how the official ROS interface is connected to the selected algorithm without requiring a line-by-line reading of the entire package.

## Full source and official references

- [Project `send_path_goal.py`](../../assets/source/send_path_goal.py)
- [Project `check_grids_mixed_qos.py`](../../assets/source/check_grids_mixed_qos.py)
- [Project Nav2 parameters](../../assets/source/nav2_foxy_floor3.yaml)
- [ROS 2 Foxy Actions](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Actions/Understanding-ROS2-Actions.html)
- [Nav2 concepts](https://docs.nav2.org/concepts/)
- [Planner Server](https://docs.nav2.org/configuration/packages/configuring-planner-server.html)
- [Controller Server](https://docs.nav2.org/configuration/packages/configuring-controller-server.html)
- [Costmap 2D](https://docs.nav2.org/configuration/packages/configuring-costmaps.html)
- [Nav2 plugins](https://docs.nav2.org/plugins/index.html)

## Why official servers are structured this way

A Planner Server roughly declares plugin parameters, owns a global costmap, loads planner classes through pluginlib, provides the `ComputePathToPose` action, obtains the current pose, calls the selected planner, and returns a `Path` or error. The Controller Server follows the same framework pattern with a local costmap and repeated `computeVelocityCommands` calls.

ROS 2 actions combine goal/result/cancel services with feedback and status topics. `send_goal_async` returns a future so the executor can keep processing communication. `spin_until_future_complete` services callbacks until completion; it does not implement the planner itself.

Costmaps contain graded costs, not just free and occupied cells. That distinction explains why visually free map pixels may still be rejected by the planner.
