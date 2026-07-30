# 语音怎样接入语义导航：定义清楚模块契约

## 当前任务

让现有语音模块识别“去人机交互实验室”一类指令，但不让语音代码直接依赖地图像素、Nav2 plugin 或 Unitree API。

## 一个最小、清晰的接口

语音侧输出：

```yaml
intent: navigate
place: hci_lab
```

语义解析层读取：

```text
semantic/floor_3_semantic.yaml
```

得到：

```yaml
floor: 3
anchor: hci_lab_nav
```

任务协调层再决定是同楼层直接导航，还是先执行电梯 transition。

## 为什么不把坐标放在语音规则中

地图重新采集后，`x/y/yaw` 会变化；地点名称和讲解内容通常仍然成立。把坐标集中在 semantic YAML 中，可以独立维护：

```text
ASR 词汇与规则
语义地点
导航安全 pose
地图版本
```

这也是软件工程中的“关注点分离”：一个模块只拥有自己需要知道的数据。

## 现有导航 client 如何被复用

项目入口：

```bash
python3 scripts/send_path_goal.py \
  anchor semantic/floor_3_semantic.yaml \
  elevator_3f_safe
```

语音 adapter 不必重写 action client，只需完成：

1. 校验 intent；
2. 将 place 映射为 anchor name；
3. 选择 floor semantic file；
4. 调用受控的 Python API 或 subprocess；
5. 监听结果并生成回复。

更长期的实现可以把 `send_path_goal.py` 封装为 ROS 2 node/service，避免每次启动新进程，但当前脚本接口适合快速集成和调试。

## 同楼层任务的数据流

```text
ASR text
→ intent parser
→ semantic resolver
→ PoseStamped
→ ComputePathToPose
→ FollowPath
→ task result
→ TTS response
```

## 跨楼层任务的数据流

```text
resolve destination floor
→ navigate to current-floor elevator safe anchor
→ stop and request human assistance
→ detect/confirm target floor
→ switch map and localization
→ navigate to destination anchor
```

这里 coordinator 需要保存当前状态，不能只依赖一句函数调用是否返回。

## 错误和取消如何传回语音层

至少区分：

- 未识别地点；
- 地点存在但当前地图未加载；
- planner 无路径；
- controller 执行失败；
- 用户取消；
- 等待人工电梯操作超时。

只有明确错误类型，TTS 才能给出有用反馈，而不是统一说“导航失败”。

## 合作模块与引用

语音识别和命令分发与合作同学的 [go2-hci](https://github.com/PYH1107/go2-hci) 衔接；本项目侧重点是语义 anchor、Nav2 client、多楼层任务结构与工程集成。具体来源统一记录在技术来源页面与 `THIRD_PARTY_NOTICE.md`。
