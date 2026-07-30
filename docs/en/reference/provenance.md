# From lower-level components to the guide system

The project is best understood as a layered system rather than as a wrapper around one repository.

ROS 2 Foxy provides topics, services, actions, lifecycle nodes, parameters, and TF. CycloneDDS and Unitree ROS 2 messages connect the dock and Go2. PointCloud2/TF processing produces LaserScan; `slam_toolbox` and `map_saver_cli` produce occupancy maps. AMCL and Nav2 provide localization, costmaps, planning, and control. The motion bridge translates `/cmd_vel` into Unitree Sport requests.

The project-specific work adds real floor maps, operational task boundaries, Foxy orchestration, semantic and safe anchors, building graph and elevator handoff, floor alignment, planner-only visualization, CSV/PNG outputs, and diagnostic tools.

Selected Go2-specific packages are traceable to:

```text
rbgyhjn/go2-nav2-amcl
commit 8a022d5ca389af2a9b793849e28956992f6a52a5
```

It is recorded as a source and engineering reference for selected driver, perception, and motion-bridge packages—not as the complete guide-robot solution. The local compatibility patch is preserved under `patches/`.

Voice collaboration is traceable to:

```text
PYH1107/go2-hci
commit 77520f4d3fda1f46ddc71355a76bf66ac56fc6b9
```

Official references:

- [ROS 2 Foxy Tutorials](https://docs.ros.org/en/foxy/Tutorials.html)
- [Nav2 Concepts](https://docs.nav2.org/concepts/)
- [Nav2 Configuration Guide](https://docs.nav2.org/configuration/)
- [slam_toolbox](https://docs.ros.org/en/ros2_packages/humble/api/slam_toolbox/)
- [Unitree ROS 2](https://github.com/unitreerobotics/unitree_ros2)
- [Unitree Go2 developer documentation](https://support.unitree.com/home/en/developer/)
