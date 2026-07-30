# TF and coordinate frames: what “where is the robot?” means

A coordinate pair such as `(x, y)` is incomplete unless its frame is known. Is it expressed in the building map, in a drifting odometry frame, or relative to the robot body? TF2 maintains those relationships over time.

## A frame is a coordinate system

| Frame | Meaning in this project | Behavior |
|---|---|---|
| `map` | global coordinates of the static occupancy map | global reference |
| `odom` | continuous local odometry coordinates | smooth but may drift |
| `base_footprint` | 2D ground reference of the robot | moves with the robot |
| `base_link` | body reference frame | moves with the robot |
| LiDAR frame | sensor measurement frame | fixed to the body |

The TF graph must form a coherent tree. Two independent publishers should not compete to provide conflicting parents for the same child frame.

## A transform is the pose relationship between two frames

A `TransformStamped` carries parent and child frame names, translation, quaternion rotation, and timestamp.

```python
tf_msg.header.frame_id = "odom"
tf_msg.child_frame_id = "base_footprint"

tf_msg.transform.translation.x = msg.pose.pose.position.x
tf_msg.transform.translation.y = msg.pose.pose.position.y
tf_msg.transform.rotation = msg.pose.pose.orientation

self.tf_broadcaster.sendTransform(tf_msg)
```

This publishes where `base_footprint` is relative to `odom` at the current time.

## Dynamic and static transforms

`odom → base_footprint` changes whenever the robot moves, so it is dynamic. The project also publishes a static identity transform:

```text
base_footprint → base_link
```

The archived implementation uses zero translation and identity rotation to complete the navigation frame chain. That is an engineering approximation, not proof that the physical reference points are exactly coincident. A refined system should derive the offset from the URDF or measured geometry.

## Broadcaster, listener, and buffer

A broadcaster publishes relationships:

```python
self.tf_broadcaster = TransformBroadcaster(self)
self.tf_broadcaster.sendTransform(tf_msg)
```

A listener receives TF updates and feeds a buffer:

```python
self.tf_buffer = Buffer()
self.tf_listener = TransformListener(self.tf_buffer, self)
```

The buffer answers coordinate queries:

```python
tf = self.tf_buffer.lookup_transform(
    "map",
    "base_footprint",
    rclpy.time.Time(),
)
```

This asks for the latest available pose of `base_footprint` expressed in `map`. The returned translation and rotation are used by the pose logger and navigation clients.

## Why navigation uses `map → odom → base_footprint`

Odometry provides `odom → base_footprint`. It is continuous and useful for control, but accumulates drift. AMCL compares laser scans with the map and publishes `map → odom`. Combining the two yields the robot pose in the map while preserving smooth local motion.

AMCL normally does not replace `odom → base_footprint`; doing so would mix global correction with the continuous local odometry relationship.

## Why orientation is stored as a quaternion

ROS messages normally represent orientation as quaternion components `(x, y, z, w)`. For planar motion, roll and pitch are zero, so yaw can be converted with:

```python
qz = math.sin(yaw / 2.0)
qw = math.cos(yaw / 2.0)
```

The quaternion `z` component alone is not the yaw angle. The project converts back using an `atan2` expression over the quaternion components.

## Why timestamps matter

A point cloud belongs to a particular measurement time. TF2 must find the sensor-to-body transform near that same timestamp. Missing, delayed, or inconsistent timestamps can produce lookup and extrapolation errors even when the frame names appear in the graph.

The project used:

```yaml
transform_tolerance: 0.3
```

as an environment-specific tolerance for the Foxy and expansion-dock pipeline. It permits a limited timing window; it does not repair an incorrect TF tree.

## Diagnostic commands

```bash
ros2 run tf2_ros tf2_echo map base_footprint
ros2 run tf2_ros tf2_echo odom base_footprint
ros2 topic echo --once /tf
ros2 topic echo --once /tf_static
```

A useful order is:

```text
odom → base_footprint
→ base_footprint → base_link
→ map → odom after localization starts
→ map → base_footprint as the complete chain
```

## Full source and official references

- [Project `odom_tf_bridge.py`](../../assets/source/odom_tf_bridge.py)
- [Project `send_path_goal.py`](../../assets/source/send_path_goal.py)
- [ROS 2 Foxy TF2 tutorials](https://docs.ros.org/en/foxy/Tutorials/Intermediate/Tf2/Tf2-Main.html)
- [Writing a TF2 broadcaster in Python](https://docs.ros.org/en/foxy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Broadcaster-Py.html)
- [Writing a TF2 listener in Python](https://docs.ros.org/en/foxy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Listener-Py.html)
