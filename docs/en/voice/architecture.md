# The voice interaction chain and the role of each layer

## Task and learning goals

This stage separates “a user spoke” into testable intermediate results. Speech recognition, intent parsing, place resolution, and robot task execution are different responsibilities that can be tested and replaced independently.

Adding a language model does not automatically create a guide robot. A practical voice interface separates audio, text, intent, semantic destinations, and robot task execution.

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

Audio capture produces sampled blocks. VAD detects speech activity and utterance boundaries; it does not interpret navigation meaning. ASR converts audio into text. `faster-whisper` is an efficient Whisper inference implementation, but recognition alone does not query maps or send goals.

A wake word controls when speech is treated as a command. An intent parser converts language into a constrained structure such as:

```yaml
intent: navigate
place: hci_lab
```

The parser may be rule-based or model-based, but its output should be validated rather than directly generating arbitrary shell commands.

The semantic resolver maps a human place name to floor and anchors. The task coordinator then decides whether one Nav2 goal is enough or whether the task requires an elevator hand-off, map switch, initial pose, and a second navigation segment.

TTS converts system responses to audio. It should remain coordinated with task state and safety rather than blocking navigation control.

## Why coordinates do not belong in the speech layer

ASR and intent code should not hard-code `x`, `y`, and `yaw`. The project stores those relationships in semantic YAML so a map update changes the semantic configuration rather than recognition logic.

## How the existing code is reused

The current navigation client accepts a semantic file and anchor name. Voice integration only needs to produce those controlled values, then reuse the existing TF, planner, and controller action logic.

## References

- [Collaborative `go2-hci` module](https://github.com/PYH1107/go2-hci)
- [Project voice integration](integration.md)
- [Project `send_path_goal.py`](../../assets/source/send_path_goal.py)
- [ROS 2 Actions](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Actions/Understanding-ROS2-Actions.html)

Structured outputs such as `intent`, `place`, and `floor` are safer than generated shell commands or raw coordinates. Unknown intents and ambiguous places can be rejected before they reach navigation.

ROS 2 integration can use an intent topic, short resolver services, Nav2 actions for long-running motion, and high-priority stop interfaces. The communication pattern should match task duration and feedback needs.
