# AMCL localization: how maps, scans, and particles produce pose

## Task and learning goals

During SLAM, map and trajectory are estimated together. During navigation, the map is fixed and the system must continuously answer where the robot is within it. AMCL maintains multiple pose hypotheses using motion and laser models, then publishes the correction between map and odometry coordinates.

Mapping answers what the environment looks like. Localization answers where the robot is in that map. AMCL—Adaptive Monte Carlo Localization—represents possible robot poses using weighted particles.

Read [TF and coordinate frames](../system/tf-primer.md) first if the frame chain is unfamiliar.

## What a particle represents

A particle is one pose hypothesis:

```text
(x, y, yaw, weight)
```

After motion and new scan data, the filter performs a motion update, a measurement update against the map, and resampling. Hypotheses that better explain the observed scan receive more weight and produce more descendants. “Adaptive” refers to adjusting the particle population according to uncertainty and distribution complexity.

## Inputs and outputs

```text
inputs
├── /map             static occupancy grid
├── /scan            current laser scan
├── odom → base      continuous motion relationship
└── /initialpose     initial global hypothesis

outputs
├── /amcl_pose       pose with covariance
├── particle cloud   pose distribution
└── map → odom       correction between map and odometry
```

AMCL does not compute paths or publish velocity commands.

## Why the localization script starts components in order

```bash
python3 $WS/scripts/odom_tf_bridge.py
ros2 launch go2_perception go2_pointcloud.launch.py
ros2 run nav2_map_server map_server --ros-args \
  -p yaml_filename:=$MAP
ros2 run nav2_amcl amcl --ros-args \
  --params-file $AMCL_CFG
ros2 run nav2_lifecycle_manager lifecycle_manager --ros-args \
  -p autostart:=true \
  -p node_names:="[map_server, amcl]"
```

AMCL depends on map, scan, and odometry/TF. Both map server and AMCL are lifecycle nodes and must become active.

## ROS APIs used by `odom_tf_bridge.py`

`create_publisher()` creates the `/odom` endpoint; `publish(msg)` sends a sample. `create_subscription()` registers the input type, topic, and callback. The executor invokes `odom_callback()` when data arrives. `sendTransform()` publishes the dynamic `odom → base_footprint` relationship.

The bridge does not reintegrate velocity into a new odometry solution. It reshapes existing odometry into the frame and topic conventions required by the navigation stack.

[Open the complete `odom_tf_bridge.py`](../../assets/source/odom_tf_bridge.py)

## Why the initial pose contains covariance

```python
msg.pose.covariance[0] = 0.25 * 0.25
msg.pose.covariance[7] = 0.25 * 0.25
msg.pose.covariance[35] = 0.20 * 0.20
```

The 6×6 covariance matrix is flattened row by row. Indices 0, 7, and 35 represent x, y, and yaw variance. Variance is standard deviation squared. A narrow covariance expresses strong confidence in the initial guess; a broad covariance lets particles explore a larger region but may take longer to converge.

The script publishes repeatedly to reduce the chance that a one-shot sample is missed while discovery and subscription setup are still completing.

[Open the initial-pose publisher](../../assets/source/publish_initial_pose_from_yaml.py)

## Why AMCL publishes `map → odom`

Odometry is smooth but drifts. AMCL estimates global pose from map and scan, then publishes a correction between `map` and `odom`. Combining it with `odom → base_footprint` yields a globally meaningful pose without replacing the continuous local odometry link.

## What common AMCL parameter groups mean

The exact field file used on site was not preserved, but parameter categories can still be understood:

- particle limits control how many simultaneous pose hypotheses are retained;
- motion-model alpha values describe odometry uncertainty;
- laser-model parameters define how predicted and observed beams are scored;
- beam count controls how many scan samples are used per update;
- update distance and angle determine when the filter performs a new measurement update;
- transform tolerance affects the timing window of the published map correction.

These values depend on map geometry, scan quality, and odometry behavior, not only on robot model.

## Verification

```bash
ros2 topic echo --once /map
ros2 topic hz /scan
ros2 topic echo --once /amcl_pose
ros2 run tf2_ros tf2_echo map base_footprint
ros2 lifecycle get /amcl
```

Localization is meaningfully available only when pose updates and the complete TF chain are present.

## Official references

- [Nav2 AMCL configuration](https://docs.nav2.org/configuration/packages/configuring-amcl.html)
- [Nav2 lifecycle concepts](https://docs.nav2.org/concepts/)
- [ROS 2 interface concepts](https://docs.ros.org/en/foxy/Concepts/About-ROS-Interfaces.html)

## Why localization is probabilistic

Sensors are noisy, corridors may look similar, and the initial pose may be approximate. A single pose estimate can lose alternative explanations too early. Particles preserve multiple hypotheses; observations weight them and resampling concentrates probability in supported regions.

Odometry provides smooth short-term motion but drifts. AMCL references the static map but updates more slowly. `map → odom` composes these strengths.

Starting `nav2_amcl amcl` creates a lifecycle node; configuration loads frames, topics, and models, while activation enables outputs and TF. `/initialpose` is a prior distribution, not a guaranteed answer.
