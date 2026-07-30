# Voice Interaction Integration / 语音交互衔接

## 中文

本仓库不重新分发语音交互模块的完整源代码。

语音识别、唤醒与命令分发部分与合作同学维护的 `go2-hci`
项目衔接：

- 上游仓库：https://github.com/PYH1107/go2-hci
- 参考版本：`77520f4d3fda1f46ddc71355a76bf66ac56fc6b9`

本项目主要负责将语音模块输出的地点或动作意图，继续转换为：

1. 语义地点名称；
2. 对应楼层与导航坐标；
3. Nav2 导航任务；
4. 多楼层及电梯交接流程。

需要运行或研究完整语音模块时，请前往其原始仓库查看。

## English

This repository does not redistribute the complete source code of the
voice-interaction module.

Wake-word detection, speech recognition and command dispatch connect
with the collaborator-maintained `go2-hci` project:

- Upstream repository: https://github.com/PYH1107/go2-hci
- Reference commit: `77520f4d3fda1f46ddc71355a76bf66ac56fc6b9`

This project focuses on translating the resulting place or action
intent into semantic destinations, floor information, Nav2 tasks and
multi-floor transition logic.

Please refer to the original repository for the complete voice module.
