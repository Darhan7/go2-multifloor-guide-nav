# Nav2 内部是怎样分工的

## 当前任务与知识目标

这一页把 Nav2 从“一个会导航的黑盒”拆成 server、plugin、costmap、lifecycle 和 action。读完后，应能判断故障属于规划、控制、地图表示、坐标系还是机器人适配层。

“启动 Nav2”听起来像是在运行一个程序，实际上 Nav2 是一组相互通信的 lifecycle server、算法 plugin、costmap 和 action 接口。理解这些层次以后，才能判断故障究竟发生在地图、规划、控制还是机器人接口。

## Server 与 plugin 不是同一个东西

### Server：提供 ROS 接口和运行框架

Planner Server 负责：

- 提供 `ComputePathToPose` 等 action server；
- 管理 global costmap；
- 加载一个或多个 planner plugin；
- 在收到 goal 时选择指定 plugin 计算路径。

Controller Server 负责：

- 提供 `FollowPath` action server；
- 管理 local costmap；
- 加载 controller plugin；
- 周期性计算速度并发布 `/cmd_vel`。

### Plugin：真正的算法实现

项目配置：

```yaml
planner_plugins: ["GridBased"]

GridBased:
  plugin: nav2_navfn_planner/NavfnPlanner
```

`GridBased` 是项目给实例起的 ID，`NavfnPlanner` 才是实际 C++ plugin 类型。Planner Server 是容器，Navfn 是装入容器的算法。

Controller 同理：

```yaml
controller_plugins: ["FollowPath"]

FollowPath:
  plugin: dwb_core::DWBLocalPlanner
```

这套 plugin 架构意味着更换算法时通常不需要重写 action client；只要新 plugin 实现相同接口，并在 YAML 中修改类型和参数即可。

## Lifecycle node：为什么“进程存在”还不代表能工作

Nav2 的主要 server 使用 managed lifecycle。典型状态：

```text
unconfigured
→ inactive
→ active
→ inactive
→ cleanup / shutdown
```

### `configure`

节点读取参数、创建 plugin、costmap、publisher、subscriber 和 action server 等资源，但还不正式处理任务。

### `activate`

节点开始对外提供有效功能，lifecycle publisher 被激活，action 请求才进入正常工作状态。

因此：

```bash
ps aux | grep planner_server
```

只能证明进程存在，不能证明它已经 active。项目使用：

```bash
ros2 lifecycle get /planner_server
```

来检查状态，并由 lifecycle manager 自动执行状态转换。

## Costmap 是规划器看到的“可行驶代价空间”

Costmap 不是普通地图图片。它把环境表示成离散格子，每格有代价值：

```text
低代价        更适合通行
高代价        接近障碍或风险更高
致命代价      不能通行
unknown       是否允许取决于配置
```

### Static layer

从 `/map` 读取静态 PGM/YAML 结构。

### Obstacle layer

从 `/scan` 接收实时障碍，执行 marking 和 clearing。

### Inflation layer

围绕障碍计算逐渐衰减的代价。它不是简单把黑墙画粗，而是在障碍附近形成一圈数值梯度，让 planner/controller 倾向于留出距离。

Global costmap 覆盖全局路线区域；local costmap 以机器人为中心滚动，服务于短时间控制。

## `ComputePathToPose` 到底返回什么

项目构造：

```python
goal = ComputePathToPose.Goal()
goal.pose = goal_pose
goal.planner_id = "GridBased"
```

`goal.pose` 是目标 `PoseStamped`；`planner_id` 告诉 Planner Server 使用哪个已加载 plugin。服务端返回的核心是：

```text
nav_msgs/Path
└── poses[]
    └── PoseStamped
```

它是一串带坐标系和时间信息的离散路径点，不包含电机控制命令，也不会让机器狗移动。

### `wait_for_server`

```python
self.compute_client.wait_for_server(timeout_sec=10.0)
```

检查 ROS graph 中是否出现兼容的 action server。它不能证明 costmap 已经更新，也不能保证给定目标一定可规划。

### `send_goal_async`

```python
future = self.compute_client.send_goal_async(goal)
```

将 goal 异步发送出去并立即返回 future。程序可以继续处理 ROS 事件，而不必让整个 executor 卡住。

### Goal handle

```python
goal_handle = future.result()
```

Goal handle 表示服务端对这次任务的身份和状态。`accepted` 只说明 server 接受了任务，不代表任务成功。

### Result future

```python
result_future = goal_handle.get_result_async()
```

继续等待最终路径和状态。规划过程中发生无路径、plugin 异常或取消时，最终状态会反映出来。

## `FollowPath` 怎样从路径生成速度

项目把 planner 输出直接交给 controller：

```python
goal = FollowPath.Goal()
goal.path = path
goal.controller_id = "FollowPath"
```

DWB controller 会不断进行类似流程：

1. 获取当前 robot pose 和 local costmap；
2. 在允许范围内采样候选线速度、角速度；
3. 在 `sim_time` 内前向模拟每组速度对应的轨迹；
4. 用 critics 对候选轨迹打分；
5. 选择得分较优且无碰撞的一组速度；
6. 发布 `geometry_msgs/Twist` 到 `/cmd_vel`；
7. 下一控制周期重新计算。

所以 DWB 不是把整条路径一次性变成固定速度表，而是闭环地反复观察当前位置和障碍。

## `Twist` 消息本身是什么

```text
geometry_msgs/Twist
├── linear.x, y, z
└── angular.x, y, z
```

二维移动通常使用：

```text
linear.x   前后速度，m/s
angular.z  绕竖直轴的角速度，rad/s
```

Nav2 发布的是通用机器人速度命令。Go2 不会仅因为 ROS 中出现 `/cmd_vel` 就自动运动，因此项目还需要 `go2_twist_bridge` 将它转换为 Unitree 的运动请求。

## 为什么 action、costmap、bridge 可以分开调试

```text
ComputePathToPose 成功
= 地图、起终点、global costmap、planner 基本可用

FollowPath 接受但无 /cmd_vel
= controller、local costmap 或 TF 仍有问题

有 /cmd_vel 但 Go2 不动
= bridge、Unitree API、步态或速度阈值需要检查
```

项目刻意把规划和执行拆成两个 action，就是为了把这些层次隔开。

## QoS 为什么会让“话题有名字但收不到数据”

DDS endpoint 必须在 message type 和 QoS 上兼容。静态地图常使用 transient-local durability，而实时传感器流可能使用 volatile。诊断脚本为 `/map` 和 costmap 分别创建不同 QoS：

```python
QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)
```

如果订阅者用不兼容的 durability，有时 `ros2 topic list` 能看到名称，却一直收不到那份已发布的地图。

## 为什么官方文档里的“server”代码值得看

官方 Nav2 Planner Server 和 Controller Server 都是 lifecycle node，并通过 pluginlib 动态加载算法。这说明项目 YAML 中的：

```yaml
plugin: nav2_navfn_planner/NavfnPlanner
```

不是普通字符串标签，而是 pluginlib 用于找到已注册 C++ 类的类型标识。Server 在 configure 阶段创建 plugin，在 active 阶段接收 action goal。

读官方源码时，不必从几千行开始逐行看。先沿着这条路径：

```text
构造函数
→ on_configure
→ plugin loader
→ action server callback
→ costmap / pose 获取
→ plugin createPlan 或 computeVelocityCommands
→ action result
```

就能理解它怎样把 ROS 接口连接到算法。

## 完整源码与官方资料

- [项目中的 `send_path_goal.py`](../assets/source/send_path_goal.py)
- [项目中的 `check_grids_mixed_qos.py`](../assets/source/check_grids_mixed_qos.py)
- [项目 Nav2 参数](../assets/source/nav2_foxy_floor3.yaml)
- [ROS 2 Foxy Actions](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Actions/Understanding-ROS2-Actions.html)
- [Nav2 concepts](https://docs.nav2.org/concepts/)
- [Planner Server](https://docs.nav2.org/configuration/packages/configuring-planner-server.html)
- [Controller Server](https://docs.nav2.org/configuration/packages/configuring-controller-server.html)
- [Costmap 2D](https://docs.nav2.org/configuration/packages/configuring-costmaps.html)
- [Nav2 plugins](https://docs.nav2.org/plugins/index.html)

## 官方 Server 代码为什么采用这种结构

以 Planner Server 为例，框架大致承担：

```text
声明参数与 plugin 名称
→ 创建 global costmap
→ pluginlib 加载规划算法类
→ 创建 ComputePathToPose action server
→ 接收 goal，查询当前 pose
→ 调用 plugin.createPlan(...)
→ 返回 Path 或错误状态
```

Controller Server 类似，但持有 local costmap，在控制循环中调用 `computeVelocityCommands(...)` 并发布速度。

这种设计使算法可替换而通信接口稳定。开发新的 planner 通常实现 plugin 接口并在 YAML 中选择，而不是重写整个 action server。

## Action 底层为什么同时用到 topic 和 service

ROS 2 Action 对外表现为 goal、feedback、result 和 cancel；实现上组合了 service 与 topic。`ActionClient.send_goal_async()` 返回 future，是因为目标接受和执行结果都可能稍后到达，executor 必须继续处理网络事件。

`spin_until_future_complete` 并不是“执行算法”，它只是持续处理 callback，直到 future 完成或超时。

## Costmap 的数值不是简单二值

规划代价通常包含自由、未知、膨胀、致命障碍等等级。Navfn 在网格上搜索累计代价；DWB 则在局部轨迹模拟中同时考虑障碍、路径偏离、目标方向等 critics。理解这些数值后，才能解释“地图上看着能走，planner 却拒绝”的情况。
