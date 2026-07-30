# Elevator workflow: continuous navigation plus discrete state transitions

Nav2 plans continuous motion in one 2D frame. An elevator transfers the robot between independent floor frames, so the project uses a human-assisted transition: the robot reaches a safe waiting pose, a person manages the physical ride, and the system handles prompts, map switching, and relocalization.

A useful state sequence is:

```text
NAVIGATE_TO_ELEVATOR
→ WAIT_FOR_HUMAN
→ IN_ELEVATOR
→ SWITCH_FLOOR
→ LOCALIZE_ON_NEW_FLOOR
→ NAVIGATE_TO_DESTINATION
```

A state machine defines entry conditions, completion, timeout, and failure instead of allowing voice, navigation, and manual actions to change state independently.

Map switching is more than changing a filename: stop the current action, change map server and AMCL state, load the target floor, provide an initial pose, wait for TF convergence, switch semantic anchors, and then send the next goal.

Human assistance is an explicit safety boundary. Fully autonomous elevators require door perception, button interaction, cabin localization, dynamic-obstacle handling, and additional safety validation beyond this prototype's focus.
