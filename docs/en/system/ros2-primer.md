# What the ROS 2 building blocks actually are

Many tutorials begin with phrases such as “start the node”, “publish a topic”, or “call an action” without first explaining the objects behind those words. This page connects those concepts directly to the real code in this project.

## Node: a named functional participant in the ROS graph

From `odom_tf_bridge.py`:

```python
class OdomTFBridge(Node):
    def __init__(self):
        super().__init__("odom_tf_bridge")
```

`Node` is the base class supplied by `rclpy`. Calling the parent constructor registers this object in the ROS graph under the name `odom_tf_bridge`, after which it can create publishers, subscriptions, timers, parameters, services, and clients.

A node is best understood as a named unit of functionality, not simply as an operating-system process. A process may contain one node or several nodes. In this project, `odom_tf_bridge` has one narrow responsibility: reshape existing odometry and publish the TF links expected by the rest of the navigation stack.

## Message: the schema of exchanged data

`Odometry`, `PoseStamped`, `LaserScan`, and `Twist` are message types. They define the fields and meanings of the data exchanged between nodes.

```python
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
```

An `Odometry` message can carry a timestamp, parent frame, child frame, pose, velocity, and covariance. Publisher and subscriber must use compatible message types to interpret the same serialized data.

The common `header` fields are particularly important in robotics:

```text
header.stamp     when the measurement is valid
header.frame_id  the coordinate frame in which it is expressed
```

## Topic: an asynchronous stream

A publisher in the project is created as follows:

```python
self.odom_pub = self.create_publisher(
    Odometry,
    "/odom",
    10,
)
```

The arguments specify the message type, topic name, and a simple QoS queue depth. The corresponding subscription is:

```python
self.sub = self.create_subscription(
    Odometry,
    "/utlidar/robot_odom",
    self.odom_callback,
    20,
)
```

Whenever a new message arrives, the ROS executor schedules `odom_callback(msg)`. Topics are therefore appropriate for continuous sensor streams, odometry, velocity commands, and changing state.

## Service: one request and one response

A service is a short request/response interaction, similar to a remote function call. Nav2 lifecycle transitions are exposed through services: a lifecycle manager asks nodes to configure, activate, deactivate, or clean up.

Services are not the best fit for long robot tasks because they do not naturally represent progress, cancellation, and a final task state. That is the role of actions.

## Action: a stateful, long-running task

`send_path_goal.py` creates two action clients:

```python
self.compute_client = ActionClient(
    self,
    ComputePathToPose,
    "compute_path_to_pose",
)

self.follow_client = ActionClient(
    self,
    FollowPath,
    "follow_path",
)
```

An action has a goal, optional feedback, a final result, and cancellation semantics. Planning and path execution can take time, so Nav2 exposes them as actions rather than ordinary services.

The first future only reports whether the server accepted the goal:

```python
future = self.compute_client.send_goal_async(goal)
rclpy.spin_until_future_complete(self, future)
goal_handle = future.result()
```

The result is a second asynchronous stage:

```python
result_future = goal_handle.get_result_async()
rclpy.spin_until_future_complete(self, result_future)
path = result_future.result().result.path
```

Calling `send_goal_async()` does not mean the path has already been computed.

## Parameter: runtime configuration attached to a node

A Nav2 parameter file uses this structure:

```yaml
planner_server:
  ros__parameters:
    expected_planner_frequency: 5.0
    planner_plugins: ["GridBased"]
```

The top-level key identifies the target node. Values under `ros__parameters` are delivered to that node. Parameters keep environment-specific values separate from compiled implementation code.

This is why the project explicitly renames the planner process:

```bash
-r __node:=planner_server
```

If the runtime node name does not match the YAML section, the expected parameters may not reach the intended node.

## QoS: the delivery contract

ROS 2 uses DDS underneath. Topic name and message type are not the whole contract; publisher and subscriber also negotiate Quality of Service settings such as reliability, durability, history, and queue depth.

The project uses transient-local durability when inspecting `/map`:

```python
durability = (
    DurabilityPolicy.TRANSIENT_LOCAL
    if topic == "/map"
    else DurabilityPolicy.VOLATILE
)
```

A static map may be published before a diagnostic subscriber starts. Transient-local durability lets that late subscriber receive the retained map. A live costmap normally uses volatile delivery because only current and future updates matter.

## `spin()`: what actually drives callbacks

A normal ROS Python program ends with:

```python
rclpy.init()
node = OdomTFBridge()
rclpy.spin(node)
```

`spin()` gives the node to an executor. The executor waits for messages, timers, services, and action events, then invokes their callbacks. Without spinning, the subscription object exists but incoming work is not continuously processed.

The project also uses:

```python
rclpy.spin_once(self, timeout_sec=0.2)
rclpy.spin_until_future_complete(self, future)
```

The first processes one round of available events. The second keeps processing ROS events until an asynchronous operation finishes.

## Launch and remapping are orchestration, not algorithms

```python
Node(
    package="go2_perception",
    executable="pointcloud_to_laserscan_node",
    remappings=[
        ("cloud_in", "/trans_cloud"),
        ("scan", "/scan"),
    ],
)
```

This asks ROS 2 to start an executable from an installed package and rename its interfaces at runtime. The launch file does not implement point-cloud conversion. Remapping allows a reusable node to connect to robot-specific topic names without editing its algorithm source.

## How the pieces fit in this project

```text
Node creates communication endpoints
→ Message defines the data schema
→ Topic carries continuous sensing and control streams
→ Service handles short operations and lifecycle transitions
→ Action represents planning and execution tasks
→ Parameter configures nodes and plugins
→ QoS controls DDS delivery behavior
→ Executor / spin makes callbacks run
```

## Full source and official references

- [Project `odom_tf_bridge.py`](../../assets/source/odom_tf_bridge.py)
- [Project `send_path_goal.py`](../../assets/source/send_path_goal.py)
- [ROS 2 Foxy: Nodes](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Nodes/Understanding-ROS2-Nodes.html)
- [ROS 2 Foxy: Topics](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html)
- [ROS 2 Foxy: Services](https://docs.ros.org/en/foxy/Tutorials/Services/Understanding-ROS2-Services.html)
- [ROS 2 Foxy: Actions](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Actions/Understanding-ROS2-Actions.html)
- [ROS 2 Foxy: Python publisher and subscriber](https://docs.ros.org/en/foxy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.html)
