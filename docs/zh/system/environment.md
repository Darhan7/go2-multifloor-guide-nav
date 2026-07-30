# 环境配置：先分清“在哪台机器上运行什么”

这个项目同时出现 Windows、Ubuntu 虚拟机和 Go2 拓展坞。初学者最容易犯的错误，是在正确的终端里运行错误的命令，或者把“能编辑代码”误认为“已经具备机器人运行环境”。

## 三个计算环境各自负责什么

| 位置 | 已确认环境 | 主要职责 |
|---|---|---|
| Windows 主机 | Windows 11 | 运行 VMware，管理物理网络和文件下载 |
| Ubuntu 虚拟机 | Ubuntu 24.04.4、Python 3.12.3、Git 2.43.0；安装过 ROS 2 Jazzy | 双网卡接入、SSH、编辑、归档、文档网站；不是本项目 Foxy/Nav2 的主要运行端 |
| Go2 拓展坞 | Ubuntu 20.04.5、ARM64 Jetson、Python 3.8.10、ROS 2 Foxy | 连接 Go2 DDS 数据，运行点云、SLAM、AMCL、Nav2 和运动桥接 |

!!! important "先记住"
    文档里的 `/home/unitree/...` 命令属于拓展坞；`/home/<vm-user>/...` 属于虚拟机。两边的 Ubuntu 版本、ROS 发行版和 CPU 架构都不同。

## ROS 2 发行版是什么

ROS 2 不是单个 Python 库，而是一组按发行版发布的软件包、消息定义、命令行工具和中间件接口。`Foxy`、`Humble`、`Jazzy` 类似一整套相互匹配的版本集合。

本项目在拓展坞上使用 Foxy，因此包名通常带：

```text
ros-foxy-...
```

不能把 Humble 或 Jazzy 的 launch、参数名称和 API 默认视为与 Foxy 完全一致。教程引用新版 Nav2 文档时，会解释概念；真正运行仍以归档的 Foxy 文件为准。

## DDS、RMW 和 CycloneDDS 分别是什么

ROS 2 节点并不直接通过一个中央服务器传消息。多数通信由 DDS 中间件完成：它负责发现其他参与者、匹配 publisher/subscriber，并在网络上传输序列化消息。

- **DDS**：底层通信规范与实现体系；
- **RMW**：ROS 2 对不同 DDS 实现的统一适配层；
- **CycloneDDS**：本项目实际选择的 DDS 实现；
- `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`：告诉 ROS 2 通过 CycloneDDS 的 RMW 插件工作；
- `CYCLONEDDS_URI`：告诉 CycloneDDS 从哪份 XML 读取网卡等配置。

拓展坞归档中确认：

```bash
source ~/cyclonedds_ws/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=~/cyclonedds_ws/cyclonedds.xml
```

`ROS_DOMAIN_ID` 没有被明确设置，因此不应声称项目使用了自定义 Domain ID。

## Workspace、package 与 `colcon build`

一个 ROS 2 workspace 通常长这样：

```text
workspace/
├── src/       源码 package
├── build/     编译中间文件
├── install/   安装后的可执行文件、库、share 和环境脚本
└── log/       构建日志
```

`package` 是 ROS 2 的最小发布和查找单元。`colcon build` 会按依赖顺序编译 `src/` 中的 package，并把结果放到 `install/`。运行时，ROS 2 查找的是安装空间，不是随便一个源码目录。

## `source setup.bash` 到底做了什么

项目脚本使用：

```bash
source /opt/ros/foxy/setup.bash
source /home/unitree/graph_pid_ws/install/setup.bash
source /home/unitree/go2_nav_official_ws/install/setup.bash
```

`source` 在**当前 shell** 中执行脚本，主要把 package 索引、可执行文件、Python 模块和动态库路径加入环境变量。它不安装软件，也不会永久修改所有终端。

后 source 的 workspace 形成 overlay，可以覆盖先前环境中同名 package。顺序因此很重要：

```text
ROS 2 基础环境
→ 拓展坞已有依赖工作空间
→ 本项目编译工作空间
```

可以用下面的命令确认实际加载的是哪一份 package：

```bash
ros2 pkg prefix nav2_planner
ros2 pkg prefix go2_perception
ros2 pkg prefix go2_twist_bridge
```

## 克隆仓库与安装环境不是一回事

```bash
git clone <repository-url>
cd go2-multifloor-guide-nav
```

这会取得项目文件，但不会自动生成 `/opt/ros/foxy`、Unitree 消息包或 CycloneDDS。当前仓库提供：

```text
tools/build_docs.sh                  文档环境
tools/configure_vm_dual_nic.sh       虚拟机网络
tools/preflight_check.sh             运行前检查
dependencies/apt-foxy.txt             依赖参考清单
config/examples/dock_environment.sh.example
config/examples/cyclonedds.xml.example
```

由于历史 `graph_pid_ws` 源码没有完整归档，仓库不会假装能从一台空白拓展坞“一键恢复所有环境”。更可靠的方式是：安装一层、检查一层，再进入下一层。

## 实际环境加载示例

复制示例文件：

```bash
cp config/examples/dock_environment.sh.example \
   ~/go2_dock_environment.sh
```

根据真实路径和网卡修改后：

```bash
source ~/go2_dock_environment.sh
```

然后运行：

```bash
./tools/preflight_check.sh dock
```

检查脚本不会替你安装软件，它会明确告诉你操作系统、ROS、RMW、package、地图和关键接口中的哪一层还没有准备好。

## 为什么虚拟机装了 Jazzy，却不能直接运行 Foxy 项目

ROS 2 节点之间能否通信，不只取决于“都叫 ROS 2”。消息定义、二进制 ABI、依赖版本、launch API 和插件版本都可能不同。虚拟机的 Jazzy 更适合编辑、独立测试或现代 ROS 2 学习；本项目的真实归档运行环境仍是拓展坞 Foxy。

## 进一步阅读

- [Unitree ROS 2 官方仓库](https://github.com/unitreerobotics/unitree_ros2)
- [ROS 2 Foxy 安装与基础教程](https://docs.ros.org/en/foxy/)
- [另一套 Go2 机器狗实验指导书](https://ztl3106742440-hub.github.io/go2-tutorial/)
- [更多学习路线](../reference/further-learning.md)
