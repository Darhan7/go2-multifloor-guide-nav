# Real-robot workflow: from path to a Go2 motion request

## Task and learning goals

This stage finally connects navigation output to physical motion. Maps and planning can be validated offline; `/cmd_vel` can affect a real robot, so the generic velocity message, vendor interface, subscriptions, and stopping behavior must be understood.

!!! danger
    Real navigation must run in a controlled open area with the remote available. Planner-only validation keeps the motion interface disabled; real execution enables the bridge.

## What the orchestration command does

```bash
./guide_floor3.sh prepare_hci
```

The script stops stale processes, starts localization, publishes the initial pose, waits for TF, starts Nav2, enables the bridge, and verifies a `/cmd_vel` subscriber. It is orchestration rather than a navigation algorithm.

## Why TF is checked first

The planner needs a current start pose, and the controller repeatedly needs robot pose. A map topic without a valid `map → base_footprint` chain is insufficient. The Shell check reads actual `tf2_echo` output instead of relying only on a fixed sleep.

## Why the `/cmd_vel` subscriber is checked

```text
controller_server --publish--> /cmd_vel --subscribe--> go2_twist_bridge
```

The topic name alone does not prove that a robot adapter is receiving commands. Subscription count is a simple confirmation that the bridge endpoint is present.

## What `geometry_msgs/Twist` represents

For planar control, `linear.x` is forward speed and `angular.z` is yaw rate. A `Twist` does not contain a map goal, complete path, gait state, Unitree API identifier, or motor-level command. It represents the body velocity desired for the current control cycle.

## Why `go2_twist_bridge` is required

Nav2 is robot-neutral. It does not know the Go2 DDS API or Sport request format. The bridge adapts:

```text
geometry_msgs/Twist
→ read linear and angular components
→ construct unitree_api::msg::Request
→ encode the Sport Move operation
→ publish /api/sport/request
```

This is the boundary between generic navigation and robot-specific actuation. A different robot can retain much of the mapping and Nav2 stack while replacing this adapter.

Its package dependencies—`rclcpp`, `geometry_msgs`, and `unitree_api`—match that narrow role.

At the Unitree SDK2 level, the corresponding high-level concept is exposed as `Move(vx, vy, vyaw)`. This project does not call that C++ client directly from Nav2; the bridge expresses the equivalent motion request through `unitree_api::msg::Request` and `/api/sport/request`. The motion intent is similar, while the transport wrapper is different.

## Why planning and execution are separate

The client first requests `ComputePathToPose`, verifies a non-empty `Path`, and then sends it through `FollowPath`.

[Open the complete `send_path_goal.py`](../../assets/source/send_path_goal.py)

This separates failure domains:

```text
planning failure
→ global costmap, start/goal, planner, TF

path exists but control fails
→ local costmap, controller, progress checking

Twist exists but robot does not move
→ bridge, Unitree interface, gait state, effective speed
```

See [Nav2 internals](nav2-internals.md).

## How a semantic destination becomes a Nav2 goal

The command selects an anchor from YAML. Python reads the pose and constructs a `PoseStamped`. Semantic naming is therefore independent of planner implementation. Moving a safe approach point changes the YAML rather than the voice parser or planner source.

## Why stop publishes zero velocity first

The stop sequence publishes one explicit zero `Twist` before terminating the bridge and servers. This reduces the chance that the last nonzero command remains effective. Physical safety must still rely on the remote, emergency controls, and a controlled test area.

## Interpreting the observed speed threshold

Approximately `0.18 m/s` did not produce clearly visible motion in the tested state, while approximately `0.30 m/s` did. This may reflect an interface dead band, gait state, command mapping, or observation conditions. It is a project observation, not a universal Unitree specification.

## Official references

- [ROS `geometry_msgs/Twist`](https://docs.ros2.org/foxy/api/geometry_msgs/msg/Twist.html)
- [Unitree ROS 2](https://github.com/unitreerobotics/unitree_ros2)
- [Unitree SDK2](https://github.com/unitreerobotics/unitree_sdk2)
- [Nav2 Controller Server](https://docs.nav2.org/configuration/packages/configuring-controller-server.html)

## Why control is a continuous loop

The controller does not publish “drive ten meters” once. At a configured rate it reads pose, path, and local obstacles, then produces a short-horizon velocity command. Broken TF, costmaps, or progress checks should stop or fail the action rather than preserve an old command.

A bridge should translate and validate velocity intent; it should not re-plan routes or hard-code semantic destinations. Before real motion, establish the chain from a non-empty path through controller output, a real `/cmd_vel` subscriber, Unitree requests, and physical safety controls.
