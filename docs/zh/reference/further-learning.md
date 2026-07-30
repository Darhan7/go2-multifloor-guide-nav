# 进一步学习与其他 Go2 路线

这份项目文档记录的是一套围绕**多楼层导览需求**逐步摸索出来的 Foxy 工程方案。它不是唯一做法。不同操作系统、ROS 发行版、硬件接口和学习目标，可能更适合其他路线。

## 另一套完整中文路线：Go2 机器狗实验指导书

[Go2 机器狗实验指导书](https://ztl3106742440-hub.github.io/go2-tutorial/) 提供了另一套系统化中文教程，覆盖环境搭建、ROS 2 消息与通信、键盘控制、Twist 桥、可视化、驱动、话题、服务、动作，以及后续感知、SLAM 和 Nav2。

两者可以互补：

| 本项目 | Go2 实验指导书 |
|---|---|
| 从真实导览任务和现场问题出发 | 从完整课程式学习路线出发 |
| 实际运行端是拓展坞 Ubuntu 20.04 + Foxy | 主要提供 Ubuntu 22.04 + Humble 路线 |
| 强调双网卡、地图工作区、语义点、多楼层和调试案例 | 覆盖更广的基础通信、驱动和实验章节 |
| 保存项目真实代码、参数和路径结果 | 提供另一套可以对照的实现与解释 |

读者可以先用实验指导书补齐 Go2 基础，再回到本项目理解一个具体导览系统如何把这些组件组织起来；也可以反过来，从项目遇到的概念跳到对应章节继续学习。

## Unitree 官方资料

- [unitree_ros2](https://github.com/unitreerobotics/unitree_ros2)：Unitree 消息、CycloneDDS 工作空间、网络和 ROS 2 通信；
- [unitree_sdk2](https://github.com/unitreerobotics/unitree_sdk2)：厂商高层客户端和 DDS 接口；
- Unitree 开发者文档：硬件、接口和安全要求应以官方说明为准。

## ROS 2 Foxy 基础

- [ROS 2 Foxy Documentation](https://docs.ros.org/en/foxy/)
- [Nodes and Topics](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools.html)
- [Services](https://docs.ros.org/en/foxy/Tutorials/Services/Understanding-ROS2-Services.html)
- [Actions](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Actions/Understanding-ROS2-Actions.html)
- [TF2 tutorials](https://docs.ros.org/en/foxy/Tutorials/Intermediate/Tf2/Tf2-Main.html)

Foxy 已结束官方支持，因此阅读时要注意：概念仍然适用，安装源和安全更新不再是最新状态。项目为复现历史环境保留 Foxy；新项目可评估更现代发行版。

## Nav2 与 SLAM

- [Nav2 Concepts](https://docs.nav2.org/concepts/)
- [Planner Server](https://docs.nav2.org/configuration/packages/configuring-planner-server.html)
- [Controller Server](https://docs.nav2.org/configuration/packages/configuring-controller-server.html)
- [Costmap 2D](https://docs.nav2.org/configuration/packages/configuring-costmaps.html)
- [slam_toolbox](https://github.com/SteveMacenski/slam_toolbox)

Nav2 当前文档版本可能高于 Foxy。学习 server/plugin/costmap/lifecycle 概念时非常有用；复制参数前应回到 Foxy package 的实际接口核对。

## 怎样读官方代码而不被淹没

不要从仓库第一行开始逐字阅读。围绕当前调用追踪：

```text
公开 action/service/topic 接口
→ server 构造和 lifecycle 回调
→ parameter 声明
→ plugin loader
→ 核心算法函数调用
→ result / publisher
```

例如项目调用 `ComputePathToPose`，就先看 action 定义、Planner Server 的 action callback，再看它怎样调用 planner plugin，而不是先阅读所有 behavior tree 和 controller 文件。
