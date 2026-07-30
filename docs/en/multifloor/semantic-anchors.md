# Semantic anchors: translate names into poses

## Task and learning goals

Nav2 accepts coordinates while visitors use place names. The semantic layer provides a stable contract between them and separates human viewing locations from robot-safe stopping poses.

Nav2 accepts poses, while a visitor asks for a named destination. Semantic YAML bridges that gap.

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

The real client reads the selected anchor:

```python
pose = data["anchors"][anchor_name]["pose"]
goal_pose = self.make_pose(pose["x"], pose["y"], pose["yaw"])
```

A human-facing point and a robot-safe point should not always be the same. The original HCI view point was close to inflated cost; moving the virtual start into corridor free space produced a valid path. A clearer model is therefore `hci_lab_view` for presentation and `hci_lab_nav` for the actual robot stop.

`building_graph.yaml` connects floor-specific elevator anchors through a human-assisted transition. Floor 1 coordinates remain placeholders and are not presented as field-validated poses.

A 2D navigation pose contains position, arrival orientation, and a frame. Orientation affects presentation, sensing, and departure. YAML stores scene data outside algorithm code, so map recalibration does not require recompiling ASR, planning, or bridge logic.

A floor map solves continuous obstacle-aware motion within one floor. A building graph solves discrete relations between floors and transition points.
