# 语义导航点：把“去实验室”变成坐标

## 当前任务与知识目标

Nav2 接受的是坐标，参观者说的是地点名称。语义导航层在两者之间建立一个稳定接口，并将“适合人观看的位置”和“适合机器人停靠的位置”分开。

Nav2 接收的是 `PoseStamped`，人说的却是“去实验室”“去电梯”。语义 YAML 就是两者之间最简单的一层翻译。

## 实际数据结构

```yaml
anchors:
  hci_lab_view:
    floor: 3
    type: poi
    pose:
      x: 4.3134
      y: 1.4932
      yaw: -3.019515

  elevator_3f_safe:
    floor: 3
    type: transition
    pose:
      x: -22.586
      y: 0.966
      yaw: -3.035
```

`floor` 用于多楼层决策，`type` 用于区分讲解点、导航点或楼层切换点，`pose` 才是 Nav2 真正需要的值。

## Python 怎样读取一个 anchor

`send_path_goal.py` 的实际逻辑很直接：

```python
with open(semantic_yaml, "r") as file:
    data = yaml.safe_load(file)

pose = data["anchors"][anchor_name]["pose"]

goal_pose = self.make_pose(
    float(pose["x"]),
    float(pose["y"]),
    float(pose["yaw"]),
)
```

这比把每个坐标写进多个 Shell/Python 文件更容易维护：位置变了，只改 YAML。

## 为什么讲解点和安全导航点要分开

`hci_lab_view` 最初表达的是人希望看到、面对的位置，但机器人圆形 footprint 和 inflation layer 可能让这个位置落入高代价区。调试时将起点向走廊自由空间移动约一米后，planner 才生成有效路线。

因此更清晰的建模方式是：

```yaml
hci_lab_view:
  type: poi
  description: 面向人的展示位置

hci_lab_nav:
  type: nav
  description: 机器人实际停靠的安全位置
```

语音说“去 HCI 实验室”时，语义层可以选择 `hci_lab_nav` 作为导航目标；到达后再根据需要调整朝向或播放讲解。

## Building graph 解决什么

单个 YAML 只描述一层楼中的点。`building_graph.yaml` 进一步描述：

```text
floor_1 elevator anchor
↕ human-assisted elevator transition
floor_3 elevator anchor
```

这样跨楼层任务可以拆成：

```text
当前楼层导航到电梯
→ 人协助进入并选择楼层
→ 切换地图和初始位姿
→ 新楼层继续导航
```

一楼的语义坐标目前仍是占位数据，文档不会把它描述成已完成现场标定的结果。

## Pose 里为什么同时有位置和朝向

一个二维导航目标至少包含：

```text
x, y       地图平面位置
yaw        到达后的朝向
frame_id   这些数值属于哪张地图坐标系
```

同一个位置面对不同方向，会影响讲解、传感器视野和离开时的控制。YAML 保存 yaw 更方便人编辑，发送 goal 时再转换为四元数。

## 配置文件为什么比代码常量更合适

语义点属于场地数据，不属于算法实现。地图重新采集或安全点微调时，更新 YAML 即可；ASR、planner 和 bridge 不必重新编译。读取时仍要验证字段、单位、frame 和点名，避免拼写错误变成运行时 KeyError。

## Building graph 与二维地图解决的问题不同

二维地图回答“同一楼层如何绕开障碍走过去”；building graph 回答“地点在哪一层、楼层之间通过哪个 transition 连接”。前者是连续几何规划，后者是离散拓扑任务规划。
