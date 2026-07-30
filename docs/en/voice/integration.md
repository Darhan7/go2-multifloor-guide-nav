# Connecting voice to semantic navigation through clear module contracts

The voice module should recognize requests such as “go to the HCI lab” without depending directly on map pixels, Nav2 plugins, or Unitree APIs.

A minimal interface is:

```yaml
intent: navigate
place: hci_lab
```

The semantic resolver selects a floor and safe anchor; the task coordinator decides whether navigation is same-floor or requires an elevator transition.

Coordinates belong in semantic YAML, not speech rules. This separates ASR vocabulary, place meaning, robot-safe poses, and map versions.

The existing client can be reused:

```bash
python3 scripts/send_path_goal.py \
  anchor semantic/floor_3_semantic.yaml \
  elevator_3f_safe
```

A voice adapter validates intent, resolves the anchor, selects the semantic file, calls a controlled API or subprocess, and converts the result into a response. A later ROS node/service wrapper could avoid starting a process for every request.

Same-floor flow:

```text
ASR text
→ intent parser
→ semantic resolver
→ PoseStamped
→ ComputePathToPose
→ FollowPath
→ result
→ TTS
```

Cross-floor flow adds elevator navigation, human handoff, map switching, relocalization, and the final goal. Errors should distinguish unknown places, unloaded maps, planning failure, control failure, cancellation, and handoff timeout.

Speech recognition and command dispatch connect with the collaborator's [go2-hci](https://github.com/PYH1107/go2-hci); this project focuses on semantic anchors, Nav2 clients, multi-floor task structure, and integration.
