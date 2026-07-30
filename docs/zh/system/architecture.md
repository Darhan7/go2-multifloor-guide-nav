# 系统架构：先看数据怎样流动

这个系统不是一个“大程序”，而是一组通过 ROS 2 接口协作的节点。理解它的关键，是先跟着一份数据从传感器走到机器狗。

## 分层结构

```text
Windows 11 主机
└── VMware Ubuntu 24.04 虚拟机
    ├── 桥接网卡：Go2 局域网
    ├── NAT 网卡：互联网
    └── SSH、编辑代码、归档和构建文档

Go2 拓展坞 — Ubuntu 20.04、ROS 2 Foxy
├── CycloneDDS 与 Unitree 消息/API
├── PointCloud2、TF 与里程计
├── 点云累积和二维激光转换
├── slam_toolbox，或 map_server + AMCL
├── Nav2 planner、controller、costmap 与 lifecycle
└── 自定义脚本、语义 YAML、楼层图和预览工具

Unitree Go2 EDU
├── LiDAR 与机器人状态话题
└── Sport 运动接口
```

## 从 LiDAR 到运动指令

```text
Go2 LiDAR PointCloud2
→ 点云累积与坐标变换
→ LaserScan /scan
→ slam_toolbox（建图）或 AMCL（定位）
→ Nav2 costmap
→ planner 计算 Path
→ controller 计算 Twist
→ /cmd_vel
→ go2_twist_bridge
→ /api/sport/request
→ Go2 Sport Move
```

这条链里使用了三种不同的 ROS 2 通信方式。

### Topic：连续流动的数据

传感器、地图和速度指令都适合 topic：

```text
/utlidar/cloud
/scan
/map
/odom
/cmd_vel
```

发布者持续产生数据，订阅者在数据到达时处理它，不要求一问一答。

### Service：短时间完成的请求

lifecycle 状态切换、查询节点参数之类的操作适合 service。它们通常很快返回，不适合持续数十秒的导航任务。

### Action：需要等待、反馈和取消的任务

导航和路径规划使用 action。项目代码中实际创建了：

```python
ActionClient(self, ComputePathToPose, "compute_path_to_pose")
ActionClient(self, FollowPath, "follow_path")
```

`ComputePathToPose` 返回一条路径；`FollowPath` 可能运行较长时间，因此可以反馈、结束或被取消。ROS 2 官方也将 action 定位为适合机器人移动这类长时间任务的接口。

## 项目层做了什么

底层组件解决“如何通信、如何建图、如何规划”；项目层解决的是“如何把它们用于一栋真实建筑中的导览任务”：

- 一楼和三楼地图、地图版本与工作区域边界；
- Foxy 下的节点启动顺序、日志、PID 和安全停止；
- 语义讲解点与机器人安全导航点；
- 楼层图、电梯交接与语音目的地接口；
- planner-only 路线预览、CSV/PNG 输出和调试工具。

第一次接触这些名词，可以先看 [ROS 2 基础概念](ros2-primer.md) 和 [TF 与坐标系](tf-primer.md)，再进入 [如何阅读代码](code-guide.md)。

## 怎样把架构图用于排错

架构图不是展示用装饰。每个箭头都应对应一个可以检查的 ROS 接口或 TF：

```text
点云箭头      → ros2 topic info /utlidar/cloud
LaserScan     → ros2 topic echo --once /scan
地图          → ros2 topic echo --once /map
定位关系      → tf2_echo map base_footprint
规划任务      → ros2 action info /compute_path_to_pose
速度命令      → ros2 topic info /cmd_vel
Unitree 请求  → ros2 topic info /api/sport/request
```

故障排查就是沿箭头寻找第一个没有满足契约的节点。
