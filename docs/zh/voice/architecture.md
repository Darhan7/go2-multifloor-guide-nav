# 语音交互链：每一层分别做什么

## 当前任务与知识目标

这一阶段把“用户说了一句话”拆成可验证的中间结果。语音识别、意图理解、地点解析和机器人任务不是同一件事；分层后，每一层都可以单独测试和替换。

“加一个大模型”并不会自动得到可用的导览机器人。语音交互至少要把声音、文字、目的地和机器人任务分成几层，每层只解决一种问题。

```text
Microphone
→ VAD / audio capture
→ ASR
→ wake word or interaction state
→ intent parsing
→ semantic resolution
→ task coordination
→ Nav2 action client
→ optional TTS response
```

## Audio capture 与 VAD

麦克风产生连续音频流。系统通常先按固定采样率切成音频块。VAD（Voice Activity Detection）判断当前是否有人声，用于减少长时间静音输入和确定一句话的边界。

VAD 不理解“去实验室”的含义，它只判断声音片段更像语音还是背景噪声。

## ASR：声音转文字

ASR（Automatic Speech Recognition）输入音频，输出文本和可能的时间戳、置信度或候选结果。例如：

```text
音频 → “带我去人机交互实验室”
```

`faster-whisper` 是 Whisper 模型的一种高效推理实现。它解决识别，不负责地图查询，也不应该直接发布导航 goal。

## Wake word：何时开始把话当命令

唤醒词例如“小白”用于降低误触发。它可以是独立关键词检测器，也可以在 ASR 文本中匹配。唤醒层决定当前语音是否进入命令处理，而不是决定机器人去哪里。

## Intent parser：用户想做什么

Intent parser 将自然语言归纳为结构化意图：

```yaml
intent: navigate
place: hci_lab
```

它可以使用规则、关键词、分类模型或大语言模型。无论采用哪种方法，输出最好是受约束的结构，而不是让生成模型直接拼接 Shell 命令。

## Semantic resolver：名称对应哪个地图对象

Resolver 查询项目的语义配置：

```text
“人机交互实验室”
→ floor: 3
→ display anchor: hci_lab_view
→ safe navigation anchor: hci_lab_nav
```

这一层解决“语言名称”和“地图坐标”之间的关系。地图重新采集后，更新 semantic YAML，而不是重新训练 ASR。

## Task coordinator：一个目的地是否需要多段任务

同楼层可能只需要：

```text
resolve anchor → send Nav2 goal
```

跨楼层则需要：

```text
导航到 3F 电梯安全点
→ 提示并等待人工协助
→ 到达 1F 后切换地图与初始位姿
→ 导航到 1F 目标
```

Coordinator 管理状态、失败和人工交接。它与单纯的 intent parser 不同：parser 判断用户意图，coordinator 决定机器人完成该意图需要执行哪些步骤。

## TTS：把系统状态说出来

TTS（Text-to-Speech）将文本回复转为音频。例如：

```text
“好的，我们先前往三楼电梯。”
```

TTS 不应阻塞导航安全检查。较合理的实现是将语音播放和任务状态协调起来，并允许高优先级停止指令打断。

## 为什么语音层不直接保存坐标

```text
ASR / intent
不应该硬编码 x, y, yaw
```

否则地图调整后，语音程序、导航程序和讲解内容都要一起修改。项目使用语义 YAML 将应用名称与 pose 分离，使语音模块只输出受控的 anchor name。

## 现有代码怎样被调用

当前导航入口：

```bash
python3 scripts/send_path_goal.py \
  anchor semantic/floor_3_semantic.yaml \
  elevator_3f_safe
```

语音集成最小只需可靠地产生：

```text
semantic file
anchor name
```

然后复用已经处理 TF、planner action 和 controller action 的导航 client。

## 参考实现与资料

- [合作模块 go2-hci](https://github.com/PYH1107/go2-hci)
- [项目语音集成说明](integration.md)
- [项目 `send_path_goal.py`](../assets/source/send_path_goal.py)
- [ROS 2 Actions](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Actions/Understanding-ROS2-Actions.html)

## 为什么结构化输出比自由文本更安全

导航系统更适合接收受约束的数据：

```yaml
intent: navigate
place: hci_lab
floor: 3
```

而不是让语言模型直接生成 shell 命令或坐标。解析器可以拒绝未知 intent、模糊地点和危险动作，coordinator 只调用预先允许的任务接口。

## 语音模块与 ROS 2 怎样连接

常见方式包括：

- 发布自定义 `Intent` topic；
- 调用短时 resolver service；
- 对长时间导航使用 Nav2 action；
- 对停止命令使用高优先级 topic/service，并在运动层实现超时保护。

选择接口应根据任务时长和是否需要反馈，而不是所有功能都用 topic。
