# 地图采集与保存：Launch 到底启动了什么

## 当前任务与知识目标

这一阶段把传感器、里程计和建图算法组合成一个实时系统，并把 `/map` 保存成可重复加载的文件。除了命令，还要理解：Launch 只是编排，SLAM 才是估计过程；里程计提供短时间连续运动，扫描匹配和回环约束修正累计误差。

实际入口：

```bash
ros2 launch go2_core go2_start.launch.py
```

`ros2 launch` 会先查找 `go2_core` package 的 share 目录，再加载其中的 Python launch 文件，并调用约定的：

```python
def generate_launch_description():
    ...
```

这个函数返回的 `LaunchDescription` 是一组启动动作。它不是建图算法本身。

## `get_package_share_directory` 是什么

真实代码：

```python
go2_driver_pkg = get_package_share_directory("go2_driver")
go2_core_pkg = get_package_share_directory("go2_core")
go2_slam_pkg = get_package_share_directory("go2_slam")
```

`ament_index_python` 会在已经 source 的工作空间中查询 package 安装位置。这样代码不需要把 `/home/unitree/...` 写死，package 无论安装到哪个 workspace，launch 都能找到它的 `launch/`、`config/` 和 `rviz/` 文件。

如果忘记：

```bash
source install/setup.bash
```

ament index 不知道这个工作空间中的 package，因而会报 package not found。

## `IncludeLaunchDescription` 是什么

主 launch 没有重复写 driver、EKF、点云和 SLAM 的所有节点，而是包含子 launch：

```python
go2_pointcloud_launch = IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        os.path.join(
            go2_perception_pkg,
            "launch",
            "go2_pointcloud.launch.py",
        )
    )
)
```

这相当于函数组合：主 launch 负责系统层结构，子 launch 负责一个子系统。这样点云模块可以单独启动，也能被建图入口复用。

## `DeclareLaunchArgument` 与 `IfCondition`

```python
use_slamtoolbox = DeclareLaunchArgument(
    name="use_slamtoolbox",
    default_value="true",
)
```

声明了运行时参数。用户可以：

```bash
ros2 launch go2_core go2_start.launch.py use_slamtoolbox:=false
```

条件：

```python
condition=IfCondition(
    LaunchConfiguration("use_slamtoolbox")
)
```

决定是否包含 `slam_toolbox` 子系统。Launch argument 与 ROS node parameter 不同：前者控制启动结构，后者配置已经启动的 node。

## 主 LaunchDescription 对应什么

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

[查看完整 `go2_start.launch.py`](https://github.com/rbgyhjn/go2-nav2-amcl/blob/8a022d5ca389af2a9b793849e28956992f6a52a5/src/base/go2_core/launch/go2_start.launch.py)

对应：

```text
driver
→ 获得机器人、LiDAR 和状态数据

robot_localization / EKF
→ 整理连续运动估计

pointcloud pipeline
→ 生成 /scan

slam_toolbox
→ 使用 /scan 和 TF 更新 /map

RViz
→ 观察数据链是否合理
```

## `online_async_launch.py` 是什么

项目没有复制 `slam_toolbox` 的实现，而是调用其公开 launch：

```python
slam_toolbox_launch = IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        os.path.join(
            get_slam_toolbox_pkg,
            "launch",
            "online_async_launch.py",
        )
    ),
    launch_arguments=[
        ("slam_params_file", slam_toolbox_config),
        ("use_sim_time", "false"),
    ],
)
```

[查看完整 `go2_slamtoolbox.launch.py`](https://github.com/rbgyhjn/go2-nav2-amcl/blob/8a022d5ca389af2a9b793849e28956992f6a52a5/src/go2_slam/launch/go2_slamtoolbox.launch.py)

`online` 表示随着传感器数据实时建图；`async` 表示扫描处理和部分内部工作采用异步结构。项目给官方 launch 传入自己的参数文件，而不是修改官方 package。

核心参数：

```yaml
slam_toolbox:
  ros__parameters:
    odom_frame: odom
    map_frame: map
    base_frame: base_link
    scan_topic: /scan
    resolution: 0.05
```

[查看实际参数文件](https://github.com/rbgyhjn/go2-nav2-amcl/blob/8a022d5ca389af2a9b793849e28956992f6a52a5/src/go2_slam/config/mapper_params_online_async.yaml)

这些参数告诉算法数据在哪里、坐标树怎么命名和输出网格分辨率，并没有重新实现 SLAM 的扫描匹配和图优化。

## `slam_toolbox` 本身在做什么

从功能层面可以理解为：

1. 从 `/scan` 获得当前二维环境轮廓；
2. 从 TF/odom 获得机器人运动的初始估计；
3. 将当前 scan 与已有地图或历史 scan 对齐；
4. 建立和优化机器人轨迹与扫描之间的约束；
5. 将结果投影为 `OccupancyGrid /map`；
6. 发布 `map → odom` 或相关建图 TF。

它不是简单把每帧 scan 直接画到图片上。扫描匹配和回环约束会修正累计误差。

## 采集时为什么仍要人工控制

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

键盘节点把按键转成 `geometry_msgs/Twist`。在建图模式下，操作者负责选择移动路线；SLAM 负责根据传感器和运动估计建图。

影响质量的因素包括：

- 运动过快导致 scan 与 TF 不同步；
- 转弯太急导致匹配困难；
- 长走廊重复结构使定位约束弱；
- 缺少回环导致累计漂移没有被校正；
- 路线没有观察到需要成为地图边界的区域。

## `map_saver_cli` 做了什么

```bash
mkdir -p /home/unitree/go2_guide_project/maps/floor_3
ros2 run nav2_map_server map_saver_cli \
  -f /home/unitree/go2_guide_project/maps/floor_3/floor_3
```

`map_saver_cli` 是 `nav2_map_server` package 提供的命令行 executable。它订阅当前 `/map`，等待一份 `OccupancyGrid`，再写出 PGM 和 YAML。它不重新运行 SLAM，也不会自动优化地图。

关于 PGM、resolution、origin 和阈值，见[地图数据模型](map-data-model.md)。

## 三楼的两个版本

第一版用于快速验证整条建图链；第二版进行了更认真、完整的采集，并成为后续边界整理、语义标注和 planner 验证的基础。历史目录名 `recovered` 不代表从损坏文件或 rosbag 恢复。

## 官方资料

- [ROS 2 Launch tutorials](https://docs.ros.org/en/foxy/Tutorials/Intermediate/Launch/Launch-Main.html)
- [slam_toolbox documentation](https://docs.ros.org/en/ros2_packages/humble/api/slam_toolbox/)
- [Nav2 Map Server](https://docs.nav2.org/configuration/packages/map_server/configuring-map-server.html)

## SLAM 为什么不是“把点画到图上”

若只根据 odom 把每帧 scan 叠加，里程计的微小误差会随路程累积，墙体会出现重影或错位。SLAM 至少包含两类估计：

- **局部扫描匹配**：寻找当前 scan 与已有局部结构最一致的位姿；
- **全局约束优化**：在再次看到旧区域时加入回环约束，重新分配整段轨迹误差。

可以把机器人轨迹看作一组待估计的 pose，scan 之间、odom 与 pose 之间形成约束。优化后再投影成栅格地图。

## `online_async` 的工程含义

`online` 表示节点在机器人移动时持续接收数据并更新状态；`async` 表示扫描处理不要求每一步都阻塞整个 ROS executor。异步并不等于“时间戳不重要”，反而更依赖 TF buffer 能在需要的时间回答变换。

## 保存前应检查什么

```bash
ros2 topic hz /scan
ros2 topic hz /map
ros2 run tf2_ros tf2_echo odom base_link
ros2 topic echo --once /map --field info
```

地图保存成功只证明文件写出来了。还要检查 YAML 的 `image` 路径、resolution、origin 与 PGM 是否匹配，并重新启动 `map_server` 验证能够加载。

## 采集策略为什么影响算法

长走廊和重复门框容易产生相似观测。更好的路线通常包含：平稳速度、适量转向、从不同方向观察结构、在可能的位置闭合回环。这里不是要求把整栋楼都走完，而是要让目标工作区域拥有足够约束。
