# 从底层组件到导览系统

理解这个项目最好的方式，不是问“用了哪个仓库”，而是看每一层分别解决了什么问题。

## ROS 2 Foxy：节点与接口

ROS 2 提供 topic、service、action、parameters、lifecycle 和 TF。项目中的实际例子包括：

```text
Topic   /scan, /map, /odom, /cmd_vel
Action  compute_path_to_pose, follow_path
Service lifecycle 状态切换和参数接口
TF      map → odom → base_footprint → base_link
```

## CycloneDDS 与 Unitree API：连接 Go2

拓展坞实际使用 `rmw_cyclonedds_cpp`。Unitree ROS 2 的 `unitree_go` 和 `unitree_api` 提供消息和 Sport 请求；运动桥把标准 `/cmd_vel` 转成 `/api/sport/request`。

## 感知与建图组件

```text
PointCloud2 + TF
→ 二维 LaserScan
→ slam_toolbox
→ OccupancyGrid
→ map_saver_cli
```

项目没有从头实现 SLAM，而是对现有组件进行 Go2/Foxy 适配、参数组织和真实场地验证。

## 定位与导航组件

```text
map_server + AMCL
→ global/local costmap
→ Navfn planner
→ DWB controller
→ /cmd_vel
```

Nav2 的核心是 server + plugin。项目根据 Foxy 和走廊环境重组启动流程、节点名称、lifecycle、参数和调试工具。

## 项目新增的导览层

- 真实一楼、三楼地图与版本管理；
- 面向任务范围的静态地图边界；
- 定位、planner、controller 和运动桥的编排脚本；
- 语义兴趣点与机器人安全点；
- 楼层图、电梯交接和地图对齐；
- planner-only 路线预览、CSV/PNG 输出和 QoS/costmap 调试；
- 语音目的地到语义导航任务的接口设计。

## 可追溯的 Go2 专用 package 来源

归档中部分 driver、点云和运动桥 package 可追溯到：

```text
rbgyhjn/go2-nav2-amcl
commit 8a022d5ca389af2a9b793849e28956992f6a52a5
```

这里把它记录为**部分 Go2 专用 package 的代码来源与工程参考**。最终导览系统没有直接采用该仓库的完整导航方案；Foxy 启动、项目参数、地图、语义、多楼层和调试流程都按当前任务重新组织。

本地兼容修改保存在：

```text
patches/go2_nav2_amcl_foxy_compat.patch
```

## 语音合作模块

```text
PYH1107/go2-hci
commit 77520f4d3fda1f46ddc71355a76bf66ac56fc6b9
```

合作模块提供 ASR、唤醒和命令分发基础；本项目负责把目的地接入楼层、语义坐标和 Nav2 工作流。

## 官方参考入口

- [ROS 2 Foxy Tutorials](https://docs.ros.org/en/foxy/Tutorials.html)
- [Nav2 Concepts](https://docs.nav2.org/concepts/)
- [Nav2 Configuration Guide](https://docs.nav2.org/configuration/)
- [slam_toolbox documentation](https://docs.ros.org/en/ros2_packages/humble/api/slam_toolbox/)
- [Unitree ROS 2](https://github.com/unitreerobotics/unitree_ros2)
- [Unitree Go2 开发文档](https://support.unitree.com/home/zh/developer/Quick_start)

这些链接用于继续学习底层组件；网站中的操作和代码解释仍以项目实际归档为准。
