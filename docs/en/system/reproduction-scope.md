# Choose the reproduction path that fits your setup

You do not need an identical robot setup on day one. The project has three useful entry points, and the first two are valuable even before the physical robot is available.

## Route A: understand and inspect everything locally

**Needs:** an ordinary computer.

You can review the maps, semantic YAML, Nav2 configuration, scripts, route CSV/PNG outputs, floor-alignment results and debugging notes. This is the best place to understand why each module exists and to adapt the documentation to a new site.

## Route B: run the real Nav2 planner without robot motion

**Needs:** the archived dock environment or an equivalent ROS 2 Foxy/Nav2 setup.

This route starts `map_server`, `planner_server`, the global costmap and lifecycle management, then supplies a virtual start pose through TF. The motion bridge stays off. That makes it ideal for checking map loading, costmap activation, semantic-anchor safety and planner responses.

## Route C: reconnect the Go2 for physical navigation

**Needs:** Go2 EDU, the expansion dock, LiDAR topics, odometry/TF, a remote controller and a controlled test area.

Add AMCL, the local costmap, controller server and the Go2 motion bridge to Route B. The on-site phase already verified the low-level motion path and established the orchestration scripts; the next visit mainly requires recalibrating localization parameters, initial poses and site safety boundaries.

!!! note "How to read planner-only results"
    They are real global-planner results on the project map and costmap, and they are excellent for finding map, lifecycle and semantic-anchor problems. Physical navigation then adds localization accuracy, moving obstacles, controller response and safety distance—the normal step from “a route exists” to “the robot follows it reliably.”
