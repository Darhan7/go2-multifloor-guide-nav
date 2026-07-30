# 实机工作流：从路径到 Go2 运动请求

## 当前任务与知识目标

这一阶段才真正把导航栈的输出交给机器狗。前面的地图和规划可以离线验证；从 `/cmd_vel` 开始，软件输出会影响实体运动，因此必须理解通用速度消息、厂商接口、订阅关系和停止策略。

!!! danger
    实机导航只能在开阔、可控区域运行，并保持遥控器随时可用。Planner-only 预览不启用运动接口；实机执行才启动 bridge。

这一页不只说明运行顺序，也解释 `/cmd_vel` 为什么还不能直接驱动 Go2。

## 一条编排命令背后发生了什么

```bash
cd /home/unitree/go2_nav_official_ws
./guide_floor3.sh prepare_hci
```

内部顺序：

```bash
$WS/floor3_nav_test.sh stop
$WS/floor3_localize.sh stop
$WS/floor3_localize.sh start
$WS/floor3_localize.sh init_hci
wait_tf
$WS/floor3_nav_test.sh start
$WS/floor3_nav_test.sh bridge
wait_cmd_subscriber
```

Shell 脚本本身不是导航算法。它把节点启动、日志、PID、等待条件和失败退出变成可重复流程。

## 为什么先检查 TF

```bash
timeout 8s ros2 run tf2_ros tf2_echo \
  map base_footprint > /tmp/floor3_tf_check.log 2>&1 || true
```

Planner 需要从 TF 获得当前起点，controller 需要不断获得当前 pose。只有 map topic 没有完整 TF，仍然无法导航。

脚本通过查找 `tf2_echo` 的有效输出避免在定位尚未建立时直接发 goal。它比固定 `sleep 10` 更有依据，但仍是 Shell 层的简化检查。

## 为什么检查 `/cmd_vel` subscriber

```bash
info=$(ros2 topic info /cmd_vel || true)
```

Nav2 controller 是 publisher，运动 bridge 是 subscriber：

```text
controller_server --publish--> /cmd_vel --subscribe--> go2_twist_bridge
```

Topic 名出现在列表里，只说明 graph 中存在相关 endpoint 或历史发现；检查 subscription count 更接近“速度是否有接收端”。

## `geometry_msgs/Twist` 是什么

Nav2 controller 发布：

```text
linear.x   前后速度，m/s
linear.y   侧向速度，m/s
angular.z  转向角速度，rad/s
```

对于常见二维底盘，主要使用 `linear.x` 和 `angular.z`。Go2 是腿式机器人，但 bridge 仍可把这两个通用速度量解释为 Sport Move 的前进和转向请求。

`Twist` 不包含：

- 目标地图坐标；
- 完整路径；
- 步态状态；
- Unitree API ID；
- 电机级命令。

它只是当前控制周期希望机器人达到的机身速度。

## `go2_twist_bridge` 为什么存在

Nav2 是机器人无关的。它不知道 Go2 的 DDS API、Sport service 或请求格式。Bridge 负责适配：

```text
geometry_msgs/Twist
→ 读取 linear / angular 分量
→ 构造 unitree_api::msg::Request
→ 填入 Sport Move 对应 API 和参数
→ 发布 /api/sport/request
```

因此 bridge 是“通用导航栈”和“特定机器人运动接口”之间的适配层。换成其他机器人时，planner、controller 和语义层可以保留，而最可能需要替换的就是这层。

项目中的 package 依赖也反映了它的职责：

```text
rclcpp
geometry_msgs
unitree_api
```

它不依赖地图或 AMCL，因为它只翻译速度命令。

在 Unitree SDK2 的高层运动接口中，同类能力以 `Move(vx, vy, vyaw)` 的形式出现：前两个量描述机身平面速度，`vyaw` 描述转向角速度。本项目没有让 Nav2 直接调用这个 C++ client，而是通过 `unitree_api::msg::Request` 和 `/api/sport/request` 走 ROS 2 / DDS 请求链。两者表达的是同一类高层运动意图，但调用封装不同。

## 为什么先规划，再执行

```python
goal = ComputePathToPose.Goal()
goal.pose = goal_pose
goal.planner_id = "GridBased"
```

得到非空 `Path` 后：

```python
goal = FollowPath.Goal()
goal.path = path
goal.controller_id = "FollowPath"
```

[查看完整 `send_path_goal.py`](../assets/source/send_path_goal.py)

这种设计可以把故障分成：

```text
路径计算失败
→ 查 global costmap、起终点、planner、TF

路径存在但控制失败
→ 查 local costmap、controller、progress checker

有 Twist 但机器人不动
→ 查 bridge、Unitree 接口、步态和有效速度
```

详见 [Nav2 内部分工](nav2-internals.md)。

## 语义目标如何进入导航

```bash
python3 scripts/send_path_goal.py \
  anchor semantic/floor_3_semantic.yaml \
  elevator_3f_safe
```

YAML 中保存人可读名称和 pose：

```python
pose = data["anchors"][anchor_name]["pose"]
goal_pose = self.make_pose(
    pose["x"],
    pose["y"],
    pose["yaw"],
)
```

这层把应用语义与 Nav2 的 `PoseStamped` 接口分开。调整一个点的安全位置时，修改 YAML 即可，不需要改 planner 或 voice parser。

## 停止命令为什么先发零速度

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

先发送明确零速度，再结束 bridge 和 server，可以减少最后一条非零命令仍被底层维持的风险。不过实际机器人安全仍应依赖遥控器、急停和受控场地，而不是只依赖软件退出顺序。

## 项目观察值怎样理解

约 `0.18 m/s` 当时不能稳定产生明显运动，而约 `0.30 m/s` 能够移动。这可能与底层接口死区、步态状态、速度映射或现场观察有关。它是项目实测记录，不是 Unitree 官方通用阈值。

## 官方资料

- [ROS `geometry_msgs/Twist`](https://docs.ros2.org/foxy/api/geometry_msgs/msg/Twist.html)
- [Unitree ROS 2](https://github.com/unitreerobotics/unitree_ros2)
- [Unitree SDK2](https://github.com/unitreerobotics/unitree_sdk2)
- [Nav2 Controller Server](https://docs.nav2.org/configuration/packages/configuring-controller-server.html)

## 控制回路为什么需要持续更新

Controller 不是只发布一次“前进 10 米”。它在固定频率下读取当前 pose、路径和局部障碍，每个周期产生短时间速度意图。若 TF、costmap 或 progress checker 异常，控制器应停止或报告失败，而不是继续执行旧命令。

## Bridge 应当承担什么，不应承担什么

Bridge 应做：

- 接收通用 `Twist`；
- 检查速度范围和时间；
- 转换为 Unitree 请求；
- 在停止或超时条件下输出零运动。

Bridge 不应重新规划路径，也不应把语义地点写死在厂商 API 层。这样更换控制器或语音模块时，硬件适配层仍保持单一职责。

## 真机前的最小证据链

```text
planner 返回非空 Path
→ controller action active
→ /cmd_vel 有合理频率和数值
→ bridge 是真实 subscriber
→ /api/sport/request 有输出
→ 遥控器和急停可用
→ 开阔区域低速测试
```

任何一层缺失，都不应直接以“机器人可能自己会动”为依据继续测试。
