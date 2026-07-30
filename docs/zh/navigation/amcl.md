# AMCL 定位：地图、激光和粒子怎样给出机器人位姿

## 当前任务与知识目标

SLAM 建图时，地图和轨迹一起被估计；导航时地图已经固定，系统需要持续回答“机器人现在在这张地图的哪里”。AMCL 通过运动模型和激光观测维护一组位姿假设，并输出地图坐标到里程计坐标之间的校正。

建图解决“环境是什么样”，定位解决“机器人现在在这张地图的哪里”。AMCL 是 Adaptive Monte Carlo Localization：使用一组带权重的粒子表示机器人可能的位姿分布。

不熟悉 TF 时，先阅读 [TF 与坐标系](../system/tf-primer.md)。

## 粒子是什么

一个粒子可以理解为一种假设：

```text
(x, y, yaw, weight)
```

系统同时保留很多个假设，而不是只维护一个点。每次机器人运动和获得新 scan 后，粒子经历：

### 1. Motion update

根据里程计变化，把每个粒子向前传播，同时加入运动模型的不确定性。直走、转弯和侧向误差的噪声通常不同。

### 2. Measurement update

对每个粒子假设的位置，预测激光束应该看到什么，再与真实 `/scan` 和静态地图比较。越符合地图的粒子，权重越高。

### 3. Resampling

高权重区域产生更多新粒子，低权重假设逐渐消失。粒子云因而向较可信的位置集中。

“Adaptive” 表示粒子数量可以根据不确定性和分布复杂度调整，而不是永远固定一个数量。

## AMCL 输入和输出

```text
输入
├── /map             静态 OccupancyGrid
├── /scan            当前 LaserScan
├── odom → base      连续运动关系
└── /initialpose     初始全局猜测

输出
├── /amcl_pose       带协方差的位姿估计
├── particle cloud   粒子分布
└── map → odom       全局地图与里程计的校正关系
```

AMCL 不负责生成 `/cmd_vel`，也不负责计算路径。

## 定位脚本为什么按这个顺序启动

```bash
python3 $WS/scripts/odom_tf_bridge.py
ros2 launch go2_perception go2_pointcloud.launch.py
ros2 run nav2_map_server map_server --ros-args \
  -p yaml_filename:=$MAP
ros2 run nav2_amcl amcl --ros-args \
  --params-file $AMCL_CFG
ros2 run nav2_lifecycle_manager lifecycle_manager --ros-args \
  -p autostart:=true \
  -p node_names:="[map_server, amcl]"
```

依赖关系：

```text
AMCL 需要 map、scan 和 odom/TF
map_server 与 AMCL 又必须进入 active
```

## `odom_tf_bridge.py` 的 ROS API

### Publisher

```python
self.odom_pub = self.create_publisher(
    Odometry,
    "/odom",
    10,
)
```

创建 `/odom` 输出端点，但真正发数据要调用：

```python
self.odom_pub.publish(msg)
```

### Subscription 与 callback

```python
self.sub = self.create_subscription(
    Odometry,
    "/utlidar/robot_odom",
    self.odom_callback,
    20,
)
```

收到消息后，executor 调用：

```python
def odom_callback(self, msg: Odometry):
    ...
```

桥接节点没有重新积分速度，而是修改 frame 和 timestamp，并转发已有 pose。

### TF broadcaster

```python
self.tf_broadcaster.sendTransform(tf_msg)
```

发布 `odom → base_footprint`，让其他节点能按时间查询机器人相对里程计 frame 的位姿。

[查看完整 `odom_tf_bridge.py`](../assets/source/odom_tf_bridge.py)

## 初始位姿为什么带协方差

AMCL 的 `/initialpose` 使用 `PoseWithCovarianceStamped`：

```python
msg.pose.covariance[0] = 0.25 * 0.25
msg.pose.covariance[7] = 0.25 * 0.25
msg.pose.covariance[35] = 0.20 * 0.20
```

6×6 covariance 按行展开。这里设置：

```text
index 0   x 方差
index 7   y 方差
index 35  yaw 方差
```

方差是标准差平方。`0.25²` 表示初始位置的不确定尺度约 0.25 m，并不是说机器人一定误差正好 0.25 m。

如果协方差太小，粒子只分布在一个很窄区域，初始猜测稍有偏差就可能难以恢复；太大则搜索范围更广、收敛更慢。

脚本发布十次是为了降低启动阶段 publisher/subscriber 尚未完全发现时丢失一次性消息的概率：

```python
for _ in range(10):
    self.pub.publish(msg)
    time.sleep(0.2)
```

[查看完整初始位姿发布脚本](../assets/source/publish_initial_pose_from_yaml.py)

## AMCL 为什么发布 `map → odom`

里程计链 `odom → base_footprint` 平滑但会漂移。AMCL 算出机器人在地图中的全局位姿后，不直接抢占 base frame，而是求出一份校正：

```text
map → odom
```

这样：

```text
map → odom → base_footprint
```

就能同时满足全局正确性和局部连续性。

## 激光模型参数实际控制什么

现场 AMCL 参数文件没有完整归档，但常见参数可以这样理解：

- 粒子数范围：允许同时保留多少位姿假设；
- motion model alpha：里程计运动中各类噪声的大小；
- laser model：如何评价预测束和地图之间的符合程度；
- beam 数量：每次更新采样多少束激光用于评分；
- update distance/angle：移动多少后触发一次滤波更新；
- transform tolerance：发布 `map → odom` 时对时间的容忍。

这些参数不能只从机器人型号推导，还与地图、走廊重复结构、scan 质量和里程计误差有关。

## 状态检查

```bash
ros2 topic echo --once /map
ros2 topic hz /scan
ros2 topic echo --once /amcl_pose
ros2 run tf2_ros tf2_echo map base_footprint
ros2 lifecycle get /amcl
```

只有 `/amcl_pose` 不断更新且完整 TF 成立，才能说定位链真正工作。

## 官方资料

- [Nav2 AMCL configuration](https://docs.nav2.org/configuration/packages/configuring-amcl.html)
- [Nav2 lifecycle concepts](https://docs.nav2.org/concepts/)
- [ROS 2 covariance message conventions](https://docs.ros.org/en/foxy/Concepts/About-ROS-Interfaces.html)

## 为什么 AMCL 需要概率，而不是一个确定坐标

传感器有噪声，走廊可能长得相似，初始位姿也不一定精确。只保存一个 pose 容易在错误匹配后失去其他可能性。粒子集合显式保留多个假设；观测逐渐支持其中一部分，再通过重采样集中到更可信区域。

## 运动模型与传感器模型如何配合

- 运动模型根据 odom 预测每个粒子可能移动到哪里，并加入与机器人运动相关的不确定性；
- 传感器模型把粒子位置下预测的激光与静态地图比较，计算权重；
- 重采样复制高权重粒子、淘汰低权重粒子，但仍需要适量随机性避免完全失去恢复能力。

因此 odom 短期连续但会漂移，AMCL 绝对参照地图但更新较慢；`map → odom` 把两者组合起来。

## 官方节点调用在做什么

启动 `nav2_amcl amcl` 只是创建 lifecycle node。参数在 configure 阶段加载地图 frame、base frame、scan topic、运动模型和激光模型；进入 active 后才发布 pose、粒子云和 TF。`lifecycle_manager` 的职责是按依赖顺序完成这些状态转换。

## 初始位姿不是“告诉 AMCL 正确答案”

`/initialpose` 提供一份先验分布中心和协方差。AMCL 仍需用后续 scan 判断它是否与地图一致。协方差过小会让错误先验过于自信，过大则会增加收敛范围和计算负担。

## 怎样判断是 AMCL 问题还是 odom 问题

- `odom → base` 不连续：先查里程计/TF bridge；
- `/scan` 与 base frame 不一致：先查点云转换和 TF；
- 粒子长期分散：检查初始位姿、地图特征和激光模型；
- 粒子集中但机器人位置错误：检查地图 origin、frame 命名和对称环境误匹配。
