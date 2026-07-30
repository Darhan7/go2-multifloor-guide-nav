# 先认识这套工程里的四类文件

刚接触 ROS 2 项目时，最容易困惑的不是某一行代码，而是：**为什么有些东西写在 launch 里，有些写在 YAML，有些又包进 Shell 脚本？**

这套工程基本由四类文件组成。先分清它们各自的职责，后面读代码会轻松很多。

在进入文件类型以前，建议先看 [ROS 2 基础概念](ros2-primer.md) 和 [TF 与坐标系](tf-primer.md)。后面的讲解会按“它是什么 → 为什么存在 → 代码怎样调用 → 在本项目里承担什么职责”展开，而不是只摆出函数名。

## 1. Launch 文件：描述“要启动哪些节点”

例如 `go2_start.launch.py` 没有亲自处理点云，也没有实现 SLAM。它做的是把已有功能组合起来：

```python
return LaunchDescription([
    go2_driver_launch,
    use_slamtoolbox,
    go2_robot_localization,
    go2_pointcloud_launch,
    go2_slamtoolbox_launch,
    rviz_node,
])
```

可以把 launch 文件理解成一张**可执行的系统结构图**。每一个 `Node(...)` 或 `IncludeLaunchDescription(...)` 都对应一个要启动的进程或子系统。

## 2. YAML：把算法和场地参数从代码里分离出来

下面这段不是在“实现” Navfn，而是在告诉 `planner_server`：加载哪个 planner plugin，并给它什么参数。

```yaml
planner_server:
  ros__parameters:
    planner_plugins: [GridBased]

    GridBased:
      plugin: nav2_navfn_planner/NavfnPlanner
      tolerance: 0.5
      use_astar: false
      allow_unknown: true
```

这样做的好处是：换地图、换机器人尺寸或调整速度时，通常只需要改配置，不必重新编译 C++。

## 3. Shell 脚本：把一串容易漏掉的操作变成稳定流程

例如 `floor3_localize.sh` 会按顺序启动里程计桥、点云、地图服务器、AMCL 和 lifecycle manager，并把日志和 PID 保存下来。

```bash
nohup ros2 run nav2_map_server map_server --ros-args \
  -p yaml_filename:=$MAP \
  > $LOG_DIR/map_server.log 2>&1 &
echo $! > $LOG_DIR/map_server.pid
```

这里的重点不是 `nohup` 本身，而是工程化习惯：

- 后台运行节点；
- 把标准输出和错误写入日志；
- 保存 PID，便于后续准确停止；
- 启动后留出时间，再启动依赖它的节点。

## 4. Python/C++ 节点：真正处理消息和执行逻辑

例如 `send_path_goal.py` 同时创建两个 action client：

```python
self.compute_client = ActionClient(
    self, ComputePathToPose, "compute_path_to_pose"
)
self.follow_client = ActionClient(
    self, FollowPath, "follow_path"
)
```

它先请求一条全局路径，再把得到的 `nav_msgs/Path` 交给 controller 执行。这里才是“读取 TF、构造消息、调用 action、检查结果”的程序逻辑。

## 按什么顺序阅读

比较自然的顺序是：

```text
Shell 脚本：先看整个流程
→ launch：看它启动了哪些节点
→ YAML：看每个节点用了什么参数和 plugin
→ Python/C++：看消息怎样进入、处理和输出
```

本网站后面的代码导读都遵循这个顺序。代码片段来自项目归档中的真实文件；为了突出核心逻辑，展示时会省略不相关的日志打印和重复分支。每段关键代码旁边还会解释它调用的 ROS 2 / Nav2 API，例如 `create_subscription()` 创建了什么端点、`lookup_transform()` 查询的方向、`send_goal_async()` 为什么返回 future，以及 lifecycle server 在 active 前做了什么。

## 对照官方资料

- [ROS 2 Foxy Tutorials](https://docs.ros.org/en/foxy/Tutorials.html)：节点、话题、service、action、参数与 colcon。
- [Nav2 Concepts](https://docs.nav2.org/concepts/)：planner、controller、costmap、lifecycle 与 plugin 架构。
- [Unitree ROS 2](https://github.com/unitreerobotics/unitree_ros2)：Unitree 消息、CycloneDDS 配置和 Go2 示例。

Foxy 已进入历史维护状态，但它与本项目拓展坞上的实际环境一致；学习概念时也可以对照当前 ROS 2 文档。

## 读一段陌生 ROS 代码时的六个问题

1. 这是 launch、配置、脚本还是 node？
2. Node 名和 package 名是什么？
3. 它创建了哪些 publisher、subscription、service、action 或 TF 对象？
4. callback 由什么消息或 future 触发？
5. parameter 和 remapping 从哪里传入？
6. 失败时会返回状态、抛异常、打印日志，还是静默等待？

回答完这六个问题，通常已经能把文件放回系统数据流中，而不必一开始理解每个算法细节。
