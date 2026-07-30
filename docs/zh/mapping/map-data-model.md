# PointCloud2、LaserScan 与 OccupancyGrid 到底装了什么

## 当前任务与知识目标

这一页回答“消息里到底存了什么”。理解数据模型以后，读者才能解释：为什么一个 topic 有数据却画不出地图、为什么 PGM 与 YAML 必须配套、为什么同一个坐标在图片和 ROS 世界中方向不同。

建图链路里最重要的不是记住三个 message 名称，而是理解数据在每一步怎样改变。

```text
三维离散点
PointCloud2
→ 按高度和角度压缩
二维极坐标距离数组
LaserScan
→ SLAM 结合运动估计
二维占据概率网格
OccupancyGrid
→ 保存
PGM + YAML
```

## `PointCloud2`：一批带字段的三维点

`PointCloud2` 不是普通图片，也不一定只是 `(x, y, z)`。它是一块结构化二进制数据，每个点可以带有：

```text
x, y, z
intensity
ring
时间或其他传感器字段
```

它还包含：

```text
header.frame_id  点坐标属于哪个传感器 frame
header.stamp     这批点的采集时间
height / width   点阵组织方式
fields           每个点有哪些字段、字段偏移和类型
point_step       每个点占多少字节
row_step         每行占多少字节
```

因此处理 `PointCloud2` 时不能简单假设“每 12 个字节就是 xyz”，而要按 `fields` 定义读取。

本项目先经过 `cloud_accumulation`，再将结果 remap 为 `/trans_cloud`。累积可以增加空间覆盖，但也要求坐标变换和时间处理正确，否则运动中的多帧点会被错误叠加。

## `LaserScan`：按角度排列的一维距离数组

`LaserScan` 主要字段：

```text
angle_min
angle_max
angle_increment
ranges[]
range_min
range_max
scan_time
```

第 `i` 个距离对应的角度近似为：

```text
angle_i = angle_min + i × angle_increment
```

`ranges[i]` 表示在这个方向上最近的有效障碍距离。二维 SLAM 并不需要保留每个三维点，而是关心机器人周围每个水平角度上“最近撞到什么”。

## 点云怎样压缩为 LaserScan

项目参数：

```python
"target_frame": "base_link",
"min_height": 0.1,
"max_height": 0.5,
"angle_min": -3.14,
"angle_max": 3.14,
"angle_increment": 0.0087,
"range_min": 0.0,
"range_max": 10.0,
```

转换逻辑可以概括为：

1. 使用 TF 把每个点转换到 `base_link`；
2. 丢弃高度低于 `min_height` 或高于 `max_height` 的点；
3. 对剩余点计算水平角度 `atan2(y, x)`；
4. 计算平面距离 `sqrt(x² + y²)`；
5. 找到对应的角度 bin；
6. 同一 bin 有多个点时保留最近距离；
7. 无有效点的方向填充无穷远或约定的空值。

这就是为什么高度范围会直接改变地图：它决定哪些三维结构被视为二维墙体或障碍物。

`angle_increment: 0.0087` 约等于 0.5°。角分辨率更细会产生更多 bin，也会增加数据量；它不会自动创造 LiDAR 原本没有测到的信息。

## `OccupancyGrid`：每个格子存一份占据判断

ROS 中的 `nav_msgs/OccupancyGrid` 包括：

```text
header
info.resolution
info.width / height
info.origin
data[]
```

`data` 通常按行展开，常见值是：

```text
-1       unknown，尚未观察
0        free，认为可通行
1..99    中间概率或代价值
100      occupied，认为被占据
```

静态地图和 costmap 都可使用网格消息，但含义并不完全相同：

- 静态 `/map` 主要表达建图得到的 free / occupied / unknown；
- costmap 还会加入膨胀、实时障碍和其他中间代价值。

## PGM 为什么能保存地图

`map_saver_cli` 将 `/map` 中的网格写成灰度图：

```text
黑色附近   occupied
白色附近   free
灰色       unknown
```

PGM 只保存像素，不知道每个像素代表多少米，也不知道地图原点。因此必须配套 YAML：

```yaml
image: floor_3.pgm
resolution: 0.05
origin: [-31.1969, -6.0832, 0.0]
occupied_thresh: 0.65
free_thresh: 0.25
negate: 0
```

### `resolution`

```text
0.05 m/pixel
```

表示一个像素边长是 5 cm。像素距离乘以 0.05 才是米制距离。

### `origin`

`origin: [x, y, yaw]` 描述图像左下角在 `map` 世界坐标中的位置和方向。它不是机器人的起点。

### 阈值

加载 PGM 时，灰度值先转成占据概率，再根据 `occupied_thresh` 和 `free_thresh` 分类。两个阈值之间的像素可以作为 unknown。

## 世界坐标和像素坐标怎样转换

项目预览脚本使用：

```python
u = int(round((x - origin[0]) / resolution))
v = int(round(height - 1 - (y - origin[1]) / resolution))
```

其中：

- `u` 从图像左侧向右增加；
- 地图世界坐标的 y 向上；
- 图像行号 `v` 向下增加；
- 所以 y 转图像行时需要翻转。

如果地图 YAML 的 origin 或 resolution 用错，语义点会整体偏移，即使数值本身看起来合理。

## `/map` 与 global costmap 为什么看起来不一样

Global costmap 会把静态地图作为一层，再叠加：

```text
实时 /scan 障碍
障碍清除与标记
inflation 中间代价
```

因此 `/map` 中大量 free 像素，在 costmap 中可能变成 1–254 的中间值。这不是地图损坏，而是导航器在表达“可以走，但越靠近障碍越不理想”。

## 完整配置与官方资料

- [项目中的 `go2_pointcloud.launch.py`](https://github.com/rbgyhjn/go2-nav2-amcl/blob/8a022d5ca389af2a9b793849e28956992f6a52a5/src/go2_perception/launch/go2_pointcloud.launch.py)
- [项目使用的 `pointcloud_to_laserscan_node.cpp`](https://github.com/rbgyhjn/go2-nav2-amcl/blob/8a022d5ca389af2a9b793849e28956992f6a52a5/src/go2_perception/src/pointcloud_to_laserscan_node.cpp)
- [项目中的 `nav2_virtual_preview_3f.py`](../assets/source/nav2_virtual_preview_3f.py)
- [ROS `sensor_msgs/PointCloud2` message](https://docs.ros2.org/foxy/api/sensor_msgs/msg/PointCloud2.html)
- [ROS `sensor_msgs/LaserScan` message](https://docs.ros2.org/foxy/api/sensor_msgs/msg/LaserScan.html)
- [ROS `nav_msgs/OccupancyGrid` message](https://docs.ros2.org/foxy/api/nav_msgs/msg/OccupancyGrid.html)
- [Nav2 Map Server configuration](https://docs.nav2.org/configuration/packages/map_server/configuring-map-server.html)

## `OccupancyGrid.data` 为什么是一维数组

二维网格在消息中按行展开：

```text
index = row * width + column
```

这样便于序列化和跨语言传输。`info.width`、`info.height` 和 `info.resolution` 决定如何把一维数组还原成空间网格。访问前必须检查索引范围，不能只凭图片尺寸猜测。

## 地图不是代价地图

`OccupancyGrid /map` 表示静态占据判断；Nav2 costmap 还会加入实时障碍、膨胀代价和未知区域策略。因而一个像素在 PGM 中是白色，不保证在 global costmap 中代价为零。调试时应分别保存 `/map` 和 costmap，而不是只看一张截图。

## 官方 API 在项目中的落点

- `nav_msgs/msg/OccupancyGrid`：`map_server`、`slam_toolbox` 和诊断脚本交换网格；
- `nav_msgs/msg/MapMetaData`：携带分辨率、尺寸和原点；
- `nav2_map_server map_saver_cli`：把消息落盘为 YAML/PGM；
- `map_server`：按 YAML 重新发布地图。

这些组件共享消息契约，因此地图文件可以从 SLAM 阶段交给 AMCL 和 Nav2，而不需要重新实现地图读取器。
