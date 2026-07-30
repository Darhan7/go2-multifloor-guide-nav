# 从三维点云到二维 LaserScan

## 当前任务与知识目标

这一阶段要把 Go2 的三维 LiDAR 数据变成二维导航栈能够消费的 `/scan`。完成后，读者不仅应当看到 topic，还应理解：

- 点云和激光扫描在数据结构上为什么不同；
- TF 为什么参与传感器转换；
- 高度切片、角度分桶和最近距离选择分别做什么；
- Launch 中 `Node`、parameter 和 remapping 怎样连接真实 C++ 节点。

!!! note "先建立一个直觉"
    `PointCloud2` 像一张没有固定行列的三维点表；`LaserScan` 像围绕机器人按角度排列的一圈距离尺。转换不是改名字，而是丢弃一部分三维信息，构造适合二维算法的表示。

Go2 LiDAR 输出 `sensor_msgs/PointCloud2`，而本项目使用的二维 SLAM、AMCL 和 Nav2 obstacle layer 主要读取 `sensor_msgs/LaserScan`。这不是简单改一个 topic 名，而是把三维点集合压缩成“每个水平角度上最近障碍距离”的二维表示。

不熟悉这些消息结构时，先阅读[地图数据模型](map-data-model.md)。

```text
/utlidar/cloud
→ cloud_accumulation
→ /trans_cloud
→ pointcloud_to_laserscan_node
→ /scan
→ slam_toolbox / AMCL / Nav2 obstacle layer
```

## `cloud_accumulation` 在做什么

单帧点云只包含 LiDAR 在那个时刻看到的点。累积节点将多帧数据整理到一个输出中，以提高墙面和结构的覆盖。它本身不是 SLAM：

- 不负责生成 OccupancyGrid；
- 不判断机器狗在地图中的全局位置；
- 主要负责点云时空整理。

累积必须依赖正确 TF。如果机器人移动了，但旧点没有转换到统一参考系，多帧结构就会错位。

## Launch 文件怎样把两个节点接起来

下面片段来自实际 `go2_pointcloud.launch.py`：

```python
Node(
    package="go2_perception",
    executable="cloud_accumulation",
    remappings=[
        ("/utlidar/cloud_accumulated", "/trans_cloud")
    ],
    name="cloud_accumulation_node",
),
Node(
    package="go2_perception",
    executable="pointcloud_to_laserscan_node",
    remappings=[
        ("cloud_in", "/trans_cloud"),
        ("scan", "/scan"),
    ],
    parameters=[{
        "target_frame": "base_link",
        "transform_tolerance": 0.3,
        "min_height": 0.1,
        "max_height": 0.5,
        "angle_min": -3.14,
        "angle_max": 3.14,
        "angle_increment": 0.0087,
        "range_max": 10.0,
    }],
)
```

[查看完整 Launch 文件](https://github.com/rbgyhjn/go2-nav2-amcl/blob/8a022d5ca389af2a9b793849e28956992f6a52a5/src/go2_perception/launch/go2_pointcloud.launch.py)

## `Node(...)` 每一项是什么

### `package`

ROS 2 先在 ament index 中查找已安装的 package。它不是 Python import 路径，而是经过 `colcon build` 和 `source install/setup.bash` 后注册的 ROS package 名。

### `executable`

Package 安装出的可执行程序名。Launch 会创建操作系统进程来运行它。

### `name`

给运行中的 ROS node 指定名称。名称会影响参数匹配、日志、`ros2 node info` 和 lifecycle 管理。

### `parameters`

将 Python 字典作为 ROS parameter 传给节点。节点内部必须声明或读取这些参数，它们才会改变算法行为。

### `remappings`

节点源码使用通用接口名，Launch 在运行时把它接到当前系统：

```text
节点内部 cloud_in ← /trans_cloud
节点内部 scan     → /scan
```

Remap 只改名字，不改消息内容，也不会自动做类型转换。

## 转换节点内部的核心工作

使用 `pointcloud_to_laserscan_node.cpp` 时，转换过程大致是：

```text
等待 cloud_in
→ 根据时间戳查询 cloud frame → base_link TF
→ 转换点坐标
→ 按 z 高度过滤
→ 计算 atan2(y, x) 得到角度
→ 计算 hypot(x, y) 得到距离
→ 写入最近的 LaserScan range bin
→ 发布 /scan
```

[查看项目中使用的完整 C++ 文件](https://github.com/rbgyhjn/go2-nav2-amcl/blob/8a022d5ca389af2a9b793849e28956992f6a52a5/src/go2_perception/src/pointcloud_to_laserscan_node.cpp)

## 为什么统一为 `base_link`

归档中的 Foxy 兼容修改：

```diff
-target_frame: base_footprint
+target_frame: base_link
```

`slam_toolbox` 的 `base_frame` 也同步改为 `base_link`。转换和 SLAM 查询同一基座 frame，可以避免一部分“topic 有数据，但 TF 无法闭合”的问题。

这不表示 `base_footprint` 没有作用。导航链中仍使用它作为地面二维参考点，并通过静态 TF 连接到 `base_link`。详见 [TF 与坐标系](../system/tf-primer.md)。

## 高度切片为什么决定地图长什么样

```yaml
min_height: 0.1
max_height: 0.5
```

- 太低：地面、腿部或近地噪声可能进入 scan；
- 太高：低矮墙体或障碍可能消失；
- 范围过宽：同一角度不同高度的物体会竞争“最近点”。

这个范围与 LiDAR 安装位置、机器人姿态和场景相关，不是通用 Go2 常数。

## `transform_tolerance` 为什么从 0.05 改到 0.3

点云有采集时间，TF 有发布时间。节点需要找到与点云时间相符的变换。容忍时间过短时，拓展坞调度和消息延迟可能让有效点云被丢弃。`0.3 s` 是当时环境的工程取值；它不应被理解为越大越稳定。

## 怎样确认每一段都工作

```bash
ros2 topic info /utlidar/cloud
ros2 topic info /trans_cloud
ros2 topic info /scan
ros2 topic hz /scan
ros2 topic echo --once /scan
```

同时检查：

```bash
ros2 run tf2_ros tf2_echo base_link <lidar_frame>
```

排查原则始终是沿数据流向前找第一个消失的位置。

## 官方资料

- [Unitree ROS 2 repository](https://github.com/unitreerobotics/unitree_ros2)
- [ROS 2 TF2 tutorials](https://docs.ros.org/en/foxy/Tutorials/Intermediate/Tf2/Tf2-Main.html)
- [PointCloud2 message](https://docs.ros2.org/foxy/api/sensor_msgs/msg/PointCloud2.html)
- [LaserScan message](https://docs.ros2.org/foxy/api/sensor_msgs/msg/LaserScan.html)

## 从官方接口继续向下看

项目调用的是 ROS 2 通用消息和 TF API，而不是自己发明点云格式。读官方代码时，可沿着以下对象追踪：

```text
sensor_msgs::msg::PointCloud2
→ tf2_ros::Buffer / TransformListener
→ 点迭代器读取 x、y、z
→ sensor_msgs::msg::LaserScan
→ publisher->publish(scan)
```

`PointCloud2` 中的数据通常保存在字节数组 `data`，`fields` 描述每个点的字段偏移和类型。C++ 节点使用迭代器或字段访问器读取点，而不是假定内存永远只包含连续的三个 float。

转换到某个角度 bin 时，程序保留更近的有效距离，是因为二维激光在同一方向上首先撞到的障碍才会限制机器人运动。超出 `range_min/range_max`、不在高度范围或无法转换 TF 的点应被忽略，而不是悄悄写入地图。

## 换传感器时哪些部分会变

如果换成真正的二维 LiDAR，可以直接获得 `LaserScan`，不再需要高度切片；如果换深度相机，则需要先生成点云或实现其他障碍层输入。可迁移的是 `/scan`、TF 和时间同步约定，不是当前 `0.1–0.5 m` 的切片参数。
