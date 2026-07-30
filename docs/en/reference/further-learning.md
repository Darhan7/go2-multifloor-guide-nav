# Further learning and alternative Go2 routes

This project documents a Foxy engineering path developed around a concrete multi-floor guide requirement. It is not the only approach; another OS, ROS distribution, hardware interface, or learning goal may favor another route.

## Alternative Chinese route: Go2 laboratory guide

The [Go2 robot laboratory guide](https://ztl3106742440-hub.github.io/go2-tutorial/) provides a broader Chinese learning sequence covering environment setup, ROS 2 communication, keyboard control, Twist bridging, visualization, drivers, topics, services, actions, perception, SLAM, and Nav2.

It complements this project: the guide is closer to a full course and mainly uses Ubuntu 22.04/Humble, while this repository follows a real guide-robot prototype on an Ubuntu 20.04/Foxy dock with dual networking, operational map boundaries, semantic anchors, multi-floor design, and archived debugging cases.

## Official foundations

- [Unitree ROS 2](https://github.com/unitreerobotics/unitree_ros2)
- [Unitree SDK2](https://github.com/unitreerobotics/unitree_sdk2)
- [ROS 2 Foxy documentation](https://docs.ros.org/en/foxy/)
- [ROS 2 services](https://docs.ros.org/en/foxy/Tutorials/Services/Understanding-ROS2-Services.html)
- [ROS 2 actions](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Actions/Understanding-ROS2-Actions.html)
- [TF2 tutorials](https://docs.ros.org/en/foxy/Tutorials/Intermediate/Tf2/Tf2-Main.html)
- [Nav2 concepts](https://docs.nav2.org/concepts/)
- [Planner Server](https://docs.nav2.org/configuration/packages/configuring-planner-server.html)
- [Controller Server](https://docs.nav2.org/configuration/packages/configuring-controller-server.html)
- [Costmap configuration](https://docs.nav2.org/configuration/packages/configuring-costmaps.html)
- [slam_toolbox](https://github.com/SteveMacenski/slam_toolbox)

Foxy is end-of-life. Its concepts remain useful, but installation and security support are historical. Current Nav2 documentation may describe newer releases, so verify exact parameters against the installed Foxy packages.

## Reading official source without drowning in it

Follow the call used by the project:

```text
public action/service/topic
→ server constructor and lifecycle callback
→ parameter declarations
→ plugin loader
→ core algorithm call
→ result or publisher
```

For `ComputePathToPose`, start with the action definition and Planner Server callback, then follow the selected planner plugin instead of reading the entire Nav2 repository linearly.
