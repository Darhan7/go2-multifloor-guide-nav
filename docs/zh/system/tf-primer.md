# TF 与坐标系：机器人到底“在哪里”

在机器人程序里，一个坐标 `(x, y)` 单独出现几乎没有意义。它必须附带一个坐标系：这是地图中的位置、启动点附近的里程计位置，还是机器狗机身上的相对位置？TF2 负责维护这些坐标系之间随时间变化的关系。

## Frame 是一套坐标轴

本项目主要使用：

| Frame | 它代表什么 | 是否会漂移 |
|---|---|---|
| `map` | 静态地图的全局坐标系 | 作为全局参考，不随机器人漂移 |
| `odom` | 里程计连续坐标系 | 连续平滑，但长期可能漂移 |
| `base_footprint` | 机器人在地面上的二维参考点 | 随机器人运动 |
| `base_link` | 机器人机身参考坐标系 | 随机器人运动 |
| LiDAR frame | 雷达自身的测量坐标系 | 固定安装在机身上 |

TF tree 要保持树状关系，不能出现同一个 child 同时由两个互相冲突的 parent 驱动。

## Transform 是两个 frame 之间的位姿关系

一个 `TransformStamped` 包含：

```text
parent frame
child frame
translation x, y, z
rotation quaternion x, y, z, w
timestamp
```

项目中的动态变换：

```python
tf_msg.header.frame_id = "odom"
tf_msg.child_frame_id = "base_footprint"

tf_msg.transform.translation.x = msg.pose.pose.position.x
tf_msg.transform.translation.y = msg.pose.pose.position.y
tf_msg.transform.rotation = msg.pose.pose.orientation

self.tf_broadcaster.sendTransform(tf_msg)
```

这表示：在当前时间，`base_footprint` 相对于 `odom` 位于什么位置和朝向。

## 动态 TF 与静态 TF

动态 TF 会持续更新，例如：

```text
odom → base_footprint
```

机器人每移动一次，这个关系就变化。

静态 TF 适合固定安装关系，例如本项目暂时设置的：

```python
self.static_tf_broadcaster = StaticTransformBroadcaster(self)
self.static_tf_broadcaster.sendTransform(tf_msg)
```

```text
base_footprint → base_link
```

当前归档中它是单位变换，即两个 frame 的平移和旋转都设为零。这样做是为了补齐导航链路，并不等于真实机器几何上两个参考点完全重合。更精确的系统应从 URDF 或实测安装尺寸给出高度偏移。

## Broadcaster、Listener、Buffer 分别是什么

### Broadcaster：发布坐标关系

```python
self.tf_broadcaster = TransformBroadcaster(self)
self.tf_broadcaster.sendTransform(tf_msg)
```

Broadcaster 把 transform 发布到 TF 系统。动态变换通常走 `/tf`，静态变换通常走 `/tf_static`。

### Listener：接收 TF 更新

```python
self.tf_buffer = Buffer()
self.tf_listener = TransformListener(self.tf_buffer, self)
```

Listener 订阅 TF 数据，并把它们交给 Buffer 保存。

### Buffer：回答坐标查询

```python
tf = self.tf_buffer.lookup_transform(
    "map",
    "base_footprint",
    rclpy.time.Time(),
)
```

这次查询可以读成：

> 请给我 `base_footprint` 在 `map` 坐标系中的变换，使用当前可用的最新数据。

返回结果中的 translation 就是机器狗在地图中的位置，rotation 就是地图中的朝向。`map_pose_logger.py`、`send_path_goal.py` 都依赖这个查询。

## 为什么导航需要 `map → odom → base_footprint`

里程计提供：

```text
odom → base_footprint
```

它短时间平滑，适合 controller 连续运动，但会累积误差。

AMCL 使用静态地图和激光扫描估计机器人全局位置，然后发布：

```text
map → odom
```

两段相乘以后，系统就能得到：

```text
map → base_footprint
```

这样既保留里程计的连续性，又通过 AMCL 修正它相对于地图的长期漂移。AMCL 通常不直接发布 `map → base_footprint`，因为那会与里程计链路争夺同一个 child frame。

## 四元数为什么看起来不像角度

ROS 中姿态常用 quaternion：

```text
x, y, z, w
```

二维导航只关心绕 z 轴的 yaw。项目把 yaw 转成 quaternion：

```python
qz = math.sin(yaw / 2.0)
qw = math.cos(yaw / 2.0)
```

因为 roll 和 pitch 设为零，所以 `qx = qy = 0`。反向读取 yaw 时使用：

```python
siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
yaw = math.atan2(siny_cosp, cosy_cosp)
```

不能把 quaternion 的 `z` 字段直接当作 yaw；它只是四元数的一个分量。

## 时间戳为什么会让“明明有 TF”仍然报错

传感器消息记录的是某一时刻看到的数据。将点云从 LiDAR frame 转到 `base_link` 时，TF2 需要对应时间附近的 transform。如果 TF 来得过晚、时间戳不一致或缓存中没有那一刻的数据，就会出现 extrapolation/lookup 错误。

项目把：

```yaml
transform_tolerance: 0.3
```

作为当时 Foxy 和拓展坞链路的工程容忍值。它不是把错误 transform 变正确，而是允许系统在有限时间窗口内等待或接受相近的坐标数据。

## 常用诊断命令

```bash
ros2 run tf2_ros tf2_echo map base_footprint
ros2 run tf2_ros tf2_echo odom base_footprint
ros2 topic echo --once /tf
ros2 topic echo --once /tf_static
```

排查顺序：

```text
先确认 odom → base_footprint
→ 再确认 base_footprint → base_link
→ 定位启动后确认 map → odom
→ 最后检查 map → base_footprint
```

## 完整源码与官方资料

- [项目中的 `odom_tf_bridge.py`](../assets/source/odom_tf_bridge.py)
- [项目中的 `send_path_goal.py`](../assets/source/send_path_goal.py)
- [ROS 2 Foxy TF2 tutorials](https://docs.ros.org/en/foxy/Tutorials/Intermediate/Tf2/Tf2-Main.html)
- [ROS 2 Foxy: Writing a TF2 broadcaster in Python](https://docs.ros.org/en/foxy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Broadcaster-Py.html)
- [ROS 2 Foxy: Writing a TF2 listener in Python](https://docs.ros.org/en/foxy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Listener-Py.html)
