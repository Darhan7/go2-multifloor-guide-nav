# Nav2 配置：从 plugin 到 costmap

## 当前任务与知识目标

YAML 不是一堆“能跑就不要动”的数字。它把节点名称、ROS 参数、plugin 类型和场地相关取值分离出来。理解层级后，读者才能知道参数为什么没有生效，以及换机器人时应该改哪一层。

最终 Foxy 配置没有直接采用一体化 launch，而是把 planner、controller 和 lifecycle 拆开启动。这样更容易确认每一层到底有没有工作，也方便单独做 planner-only 验证。

## 1. Planner server 只是容器，算法由 plugin 提供

```yaml
planner_server:
  ros__parameters:
    expected_planner_frequency: 5.0
    planner_plugins: ["GridBased"]

    GridBased:
      plugin: nav2_navfn_planner/NavfnPlanner
      tolerance: 0.5
      use_astar: false
      allow_unknown: true
```

`GridBased` 是当前配置给 plugin 起的别名，真正的实现类型是 `NavfnPlanner`。代码请求路径时必须使用同一个 ID：

```python
goal.planner_id = "GridBased"
```

如果 YAML 中改了别名，而 action client 仍发送旧名字，planner 会找不到对应 plugin。

## 2. Global costmap 与 local costmap 分工不同

### Global costmap

```yaml
global_frame: map
track_unknown_space: true
plugins: ["static_layer", "obstacle_layer", "inflation_layer"]
```

它覆盖整张地图，主要供全局 planner 搜索从起点到终点的路线。

### Local costmap

```yaml
global_frame: odom
rolling_window: true
width: 3
height: 3
plugins: ["obstacle_layer", "inflation_layer"]
```

它以机器人为中心滚动，主要供 controller 根据附近障碍生成短时间控制指令。

## 3. 三层 costmap 各自写入什么

```text
static_layer    ← PGM/YAML 静态地图
obstacle_layer  ← 实时 /scan
inflation_layer ← 在障碍周围扩展安全代价
```

项目配置：

```yaml
robot_radius: 0.30
inflation_radius: 0.65
cost_scaling_factor: 2.5
```

`robot_radius` 是圆形近似；`inflation_radius` 不是再把机器人尺寸加一次，而是让路径在障碍附近逐渐变“更贵”。这也是原语义点太靠墙时出现空路径的原因之一。

## 4. DWB 如何从路径变成 `/cmd_vel`

```yaml
FollowPath:
  plugin: dwb_core::DWBLocalPlanner
  max_vel_x: 0.38
  max_vel_theta: 0.85
  sim_time: 1.0
  vx_samples: 12
  vtheta_samples: 20
  critics:
    - RotateToGoal
    - Oscillation
    - BaseObstacle
    - GoalAlign
    - PathAlign
    - PathDist
    - GoalDist
```

DWB 会采样多组候选速度，在短时间内模拟运动，再用多个 critic 打分。`BaseObstacle` 关注碰撞，`PathDist` 关注是否贴近全局路径，`GoalDist` 关注是否朝目标前进。配置中的 scale 决定它们在总分中的相对权重。

这些数值是项目现场调参记录，不是通用 Go2 推荐参数。

## 5. 为什么显式重命名 planner 节点

真实启动命令：

```bash
ros2 run nav2_planner planner_server --ros-args \
  -r __node:=planner_server \
  --params-file $NAV_CFG
```

`-r __node:=planner_server` 保证：

- 参数文件中的 `planner_server:` 能匹配到节点；
- lifecycle manager 管理的是 `/planner_server`；
- 调试命令 `ros2 lifecycle get /planner_server` 指向正确对象。

早期未统一节点名称时，容易出现“进程在运行，但参数或 lifecycle 没有作用到它”的假象。

## 6. 怎样验证地图真的进入了 costmap

项目的 `check_grids_mixed_qos.py` 会分别使用适合 `/map` 与 costmap 的 QoS：

```python
durability = (
    DurabilityPolicy.TRANSIENT_LOCAL
    if topic == "/map"
    else DurabilityPolicy.VOLATILE
)
```

然后统计 occupied、free、unknown 和中间代价值。这样不仅知道“话题存在”，还可以确认 inflation layer 是否已经产生中间 cost。

## 官方延伸阅读

- [Nav2 concepts](https://docs.nav2.org/concepts/)
- [Nav2 configuration guide](https://docs.nav2.org/configuration/)

## ROS 参数文件的层级怎样匹配节点

典型结构：

```yaml
planner_server:
  ros__parameters:
    planner_plugins: ["GridBased"]
```

最外层名称必须匹配运行节点名；`ros__parameters` 是 ROS 2 参数命名约定。若进程实际叫 `/nav2_planner`，却把参数写在 `planner_server` 下，节点可能启动但读取默认值。

这也是项目显式使用：

```bash
-r __node:=planner_server
```

的原因。

## Plugin ID、类型字符串和运行时选择

```yaml
planner_plugins: ["GridBased"]
GridBased:
  plugin: "nav2_navfn_planner/NavfnPlanner"
```

- `GridBased` 是本配置中的实例 ID；
- 类型字符串告诉 pluginlib 加载哪个已注册的 C++ 类；
- action goal 中的 `planner_id="GridBased"` 选择这个实例。

三者名称含义不同，但必须对应。

## 参数调优应当怎样记录

建议每次只改一类假设，并保存 before/after：

```text
机器人尺寸与 footprint
→ 障碍膨胀
→ 速度与加速度
→ goal/progress checker
→ critics 权重
```

同时保存规划图、costmap 和日志。没有对照的“大量调参”很难判断真正起作用的是哪一项。

## 机器人半径不是唯一安全距离

`robot_radius` 或 footprint 描述几何外形；inflation radius 和 cost scaling 描述规划偏好；真实 Go2 还会有步态摆动、传感器误差和停止距离。静态参数需要结合低速现场验证，而不能只看地图尺寸。
