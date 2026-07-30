# planner-only 虚拟预览：真实 Nav2，不让机器狗移动

## 当前任务与知识目标

在不启动运动 bridge 的情况下调用真实 Nav2 Planner Server，得到一条 `nav_msgs/Path`，并保存为 CSV 与 PNG。这个模式把“规划是否合理”与“真机是否执行”彻底分开。

这个模式不是自己画一条直线，而是调用真实 `planner_server` 的 `ComputePathToPose` action。区别在于：只启动地图和 planner 相关组件，不启动运动桥。

## 1. 为什么需要一个虚拟起点

Foxy 版本的 `ComputePathToPose.Goal` 在本项目环境中只设置目标位姿，planner 默认从当前机器人 TF 获取起点。因此脚本临时发布：

```text
map → base_footprint
```

让 planner 把指定语义点当作当前机器人位置。

实际脚本通过独立进程启动静态 TF publisher，结束后再终止它。这种办法适合离线预览，但不能与真实 AMCL 的 `map → odom → base_footprint` 同时混用。

## 2. Action client 的核心代码

```python
self.client = ActionClient(
    self,
    ComputePathToPose,
    "compute_path_to_pose",
)

 goal = ComputePathToPose.Goal()
 goal.pose = goal_pose
 goal.planner_id = "GridBased"

future = self.client.send_goal_async(goal)
rclpy.spin_until_future_complete(self, future)
```

`send_goal_async` 不代表结果已经返回。先得到 goal handle，再等待 result future，最终取出：

```python
path = result.path
```

其中 `path.poses` 是一系列 `PoseStamped`，不是一张图片。

## 3. 世界坐标如何画到 PGM 上

脚本从地图 YAML 读取 `resolution` 和 `origin`：

```python
u = int(round((x - origin[0]) / resolution))
v = int(round(height - 1 - (y - origin[1]) / resolution))
```

随后将路径位姿转换成像素点，逐段连成红线；起点画蓝色，目标画绿色。

## 4. 为什么同时保存 CSV

```python
writer.writerow(["x", "y", "yaw"])
for pose_stamped in path.poses:
    writer.writerow([
        pose_stamped.pose.position.x,
        pose_stamped.pose.position.y,
        yaw_from_q(pose_stamped.pose.orientation),
    ])
```

PNG 适合展示，CSV 则保留可计算的路径数据。以后可以用它分析长度、曲率、离墙距离或比较不同参数。

## 5. 实际运行

```bash
source /opt/ros/foxy/setup.bash
source /home/unitree/graph_pid_ws/install/setup.bash
source /home/unitree/go2_nav_official_ws/install/setup.bash

cd /home/unitree/go2_nav_official_ws
./floor3_nav_test.sh start
sleep 10
./floor3_nav_test.sh status

python3 scripts/nav2_virtual_preview_3f.py \
  hci_lab_view_test_left \
  elevator_3f_safe
```

运行前确认：

```bash
ros2 lifecycle get /planner_server
python3 scripts/check_grids_mixed_qos.py \
  /map /global_costmap/costmap
ros2 topic info /cmd_vel
```

不启动 `go2_twist_bridge`，即使 controller 或其他节点误发 `/cmd_vel`，也不会进入 Go2 Sport API。

## 6. 这段代码怎样迁移到别的地图

真正需要替换的不是 planner 算法，而是：

```text
MAP_YAML
SEMANTIC_YAML
OUT_DIR
语义点名称
```

当前脚本把它们写成了 `/home/unitree/...` 绝对路径。更通用的版本应改为命令行参数或 ROS parameters；教程保留原始写法，是为了让代码和实际归档完全对应。

## 为什么 Foxy 版本需要虚拟 TF 起点

当前 action 定义主要提供目标 pose，planner 从 TF 查询机器人当前 pose。离线预览没有 AMCL 和真实机器人，因此脚本临时发布：

```text
map → base_footprint
```

来表示虚拟起点。这个 TF 只服务于规划请求，不应与真实定位同时发布，否则会产生两个来源争夺同一坐标关系。

## PNG 与 CSV 分别回答什么

- PNG 适合人快速判断是否穿墙、绕行和靠近边界；
- CSV 保留每个 `PoseStamped` 的数值，可计算长度、曲率、离障碍距离，或供其他程序使用；
- 两者都不证明 controller 能够跟踪，也不证明真机安全。

## 脚本泛化的关键

要把当前工具变成通用命令，应把地图 YAML、起点、终点、planner ID 和输出目录变成参数，并从 YAML 自动读取 resolution/origin。绝对路径是项目归档值，不是 Nav2 的要求。
