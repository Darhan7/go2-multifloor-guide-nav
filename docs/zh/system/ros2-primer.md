# ROS 2 里的这些词到底是什么

很多教程会直接写“启动节点”“发布话题”“调用 action”，仿佛这些词天然就应该懂。这里先把它们拆开。后面的代码并不是孤立的技巧，而是在使用 ROS 2 提供的一套通信和运行机制。

## Node：加入 ROS graph 的功能单元

下面两行来自项目中的 `odom_tf_bridge.py`：

```python
class OdomTFBridge(Node):
    def __init__(self):
        super().__init__("odom_tf_bridge")
```

`Node` 是 `rclpy` 提供的基类。调用 `super().__init__(...)` 后，这个 Python 对象会以 `odom_tf_bridge` 的名字加入 ROS graph，随后才能创建 publisher、subscription、timer、parameter 或 client。

可以把 node 理解为“具有明确名字和通信接口的功能单元”，但不要把它简单等同于操作系统进程：

- 一个 Python 程序通常创建一个 node；
- 一个进程也可以承载多个 node；
- launch 文件启动的每个 executable 往往会创建一个或多个 node。

在本项目中，`odom_tf_bridge` 只负责整理里程计和 TF；它不负责建图，也不负责路径规划。把职责拆开后，某一层出问题时才能单独检查。

## Message：节点之间传递的数据结构

`Odometry`、`PoseStamped`、`LaserScan` 和 `Twist` 都是 message type。它们不是“某条具体数据”，而是数据格式的定义。

例如：

```python
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
```

`Odometry` 规定了里程计消息里可以放什么：时间戳、参考坐标系、子坐标系、位姿、速度和协方差。发布者和订阅者只有使用兼容的 message type，才能正确解释同一串字节。

很多 ROS message 都带有 `header`：

```text
header.stamp     数据对应的时间
header.frame_id  数据在哪个坐标系中表达
```

这两个字段对机器人系统非常重要。只知道“点在哪里”还不够，还必须知道“它在哪个坐标系、哪个时刻成立”。

## Topic：持续的数据流

项目中的发布者：

```python
self.odom_pub = self.create_publisher(
    Odometry,
    "/odom",
    10,
)
```

这三个主要参数分别是：

1. `Odometry`：消息类型；
2. `/odom`：topic 名称；
3. `10`：这里使用的 QoS depth 简写，表示队列最多保留若干条尚未处理的消息。

订阅者：

```python
self.sub = self.create_subscription(
    Odometry,
    "/utlidar/robot_odom",
    self.odom_callback,
    20,
)
```

每当 `/utlidar/robot_odom` 到达一条新消息，ROS 2 会安排执行 `self.odom_callback(msg)`。它不是普通函数被你手工循环调用，而是由 ROS executor 在消息到达后触发。

Topic 适合：

- LiDAR、相机、里程计等连续数据；
- 速度命令；
- 地图或状态更新。

发布者通常不知道有几个订阅者，订阅者也不要求发布者等待自己处理完成。这种异步结构适合传感器流。

## Service：一次请求，一次回答

Service 使用 request/response 模型。客户端发出一个问题，服务端处理后返回一个结果。它更像一次远程函数调用，适合短时间完成的操作。

本项目的 Shell 脚本没有直接写很多 service client，但 Nav2 lifecycle 管理本身会通过 service 请求节点进行 `configure`、`activate`、`deactivate` 等状态切换。

Service 不适合持续导航任务，因为它没有天然的长时间反馈和取消语义。需要执行数秒甚至数分钟的机器人任务时，通常使用 action。

## Action：带状态的长任务

`send_path_goal.py` 创建两个 action client：

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

Action 可以看成由几部分组成：

```text
goal      客户端希望服务端完成什么
feedback  执行过程中不断返回的进展
result    任务结束后的最终结果
cancel    客户端要求中途取消
```

规划路径和执行路径都不是简单的瞬时查询，因此 Nav2 把它们设计成 action。

实际调用顺序是：

```python
future = self.compute_client.send_goal_async(goal)
rclpy.spin_until_future_complete(self, future)
goal_handle = future.result()
```

这里第一层 `future` 只表示“服务端是否接受这个 goal”。接受以后，还要再等待结果：

```python
result_future = goal_handle.get_result_async()
rclpy.spin_until_future_complete(self, result_future)
path = result_future.result().result.path
```

所以 `send_goal_async()` 并不等于“路径已经算出来”。这也是初学者调 action 时最容易混淆的一点。

## Parameter：节点启动时读取的配置

Nav2 YAML 中常见结构：

```yaml
planner_server:
  ros__parameters:
    expected_planner_frequency: 5.0
    planner_plugins: ["GridBased"]
```

第一层 `planner_server` 是目标 node 名称，`ros__parameters` 下面才是传给该 node 的参数。参数让算法实现与场地数值分离：更换地图、机器人半径或速度限制时，可以先改 YAML，而不是重新编译代码。

这也解释了为什么项目启动 planner 时显式重命名：

```bash
-r __node:=planner_server
```

如果实际 node 名称与 YAML 顶层名称不一致，那份参数可能根本没有加载到预期节点。

## QoS：通信双方对“怎样送达”的约定

ROS 2 底层使用 DDS。除了 topic 名和 message type，发布者、订阅者还要在 QoS 上兼容。常见维度包括：

- **Reliability**：尽力发送，还是要求可靠交付；
- **Durability**：新订阅者能否拿到发布前已经存在的数据；
- **History / depth**：缓存多少条消息。

项目检查 `/map` 时使用 `TRANSIENT_LOCAL`：

```python
durability = (
    DurabilityPolicy.TRANSIENT_LOCAL
    if topic == "/map"
    else DurabilityPolicy.VOLATILE
)
```

静态地图通常不会高频重复发布。如果订阅者稍晚上线，`TRANSIENT_LOCAL` 可以让它收到发布者保留的最后一份地图。普通实时 costmap 则使用 `VOLATILE`，只关心当前之后的新数据。

## `spin()`：为什么写了 callback 还不会自动执行

程序最后通常有：

```python
rclpy.init()
node = OdomTFBridge()
rclpy.spin(node)
```

`rclpy.spin(node)` 把 node 交给 executor。executor 等待消息、timer、service 或 action 事件，再执行相应 callback。没有 spin，publisher 对象可以创建，但 subscription callback 不会持续被调度。

项目中还使用：

```python
rclpy.spin_once(self, timeout_sec=0.2)
rclpy.spin_until_future_complete(self, future)
```

- `spin_once`：处理一轮可用事件，然后返回；
- `spin_until_future_complete`：持续处理 ROS 事件，直到指定 future 完成。

后者很重要，因为 action 结果也是通过 ROS 通信返回的。只用普通的阻塞等待，反而可能没有 executor 去接收结果。

## Launch 与 remapping 不是算法

Launch 中的：

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

表示“从已安装 package 中启动这个 executable，并在运行时替换接口名称”。它没有实现点云转换算法，只是把现有节点接入当前系统。

Remapping 的意义是让通用节点不必把某台机器人上的 topic 名硬编码进源码：

```text
节点内部 cloud_in  ← 系统中的 /trans_cloud
节点内部 scan      → 系统中的 /scan
```

## 在本项目中如何串起来

```text
Node 创建通信端点
→ Message 定义数据结构
→ Topic 传递连续传感器和控制数据
→ Service 管理短操作和 lifecycle
→ Action 执行规划与跟踪等长任务
→ Parameter 配置节点和 plugin
→ QoS 决定 DDS 交付行为
→ Executor / spin 驱动 callback 真正运行
```

这些概念理解以后，后面的 launch、YAML 和 Python 代码就不再是一串陌生命令。

## 完整源码与官方资料

- [项目中的 `odom_tf_bridge.py`](../assets/source/odom_tf_bridge.py)
- [项目中的 `send_path_goal.py`](../assets/source/send_path_goal.py)
- [ROS 2 Foxy：Nodes](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Nodes/Understanding-ROS2-Nodes.html)
- [ROS 2 Foxy：Topics](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html)
- [ROS 2 Foxy：Services](https://docs.ros.org/en/foxy/Tutorials/Services/Understanding-ROS2-Services.html)
- [ROS 2 Foxy：Actions](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Actions/Understanding-ROS2-Actions.html)
- [ROS 2 Foxy：Writing a Python publisher and subscriber](https://docs.ros.org/en/foxy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.html)
