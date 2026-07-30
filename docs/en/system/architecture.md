# System architecture: follow the data flow

This system is not one large program. It is a collection of ROS 2 nodes connected by well-defined interfaces.

```text
Go2 LiDAR PointCloud2
→ accumulated and transformed cloud
→ LaserScan /scan
→ slam_toolbox for mapping or AMCL for localization
→ Nav2 costmaps
→ planner Path
→ controller Twist on /cmd_vel
→ go2_twist_bridge
→ /api/sport/request
→ Go2 Sport Move
```

Continuous sensor data, maps, and velocity commands use topics. Short management requests use services. Navigation uses actions because planning and motion can take time, return feedback, and be cancelled.

The project contains real examples of both planning actions:

```python
ActionClient(self, ComputePathToPose, "compute_path_to_pose")
ActionClient(self, FollowPath, "follow_path")
```

The lower layers provide communication, mapping, localization, and navigation. The project-specific layer adds real floor maps, operational boundaries, semantic anchors, multi-floor structure, elevator handoff, planner previews, and repeatable orchestration scripts.


New readers can continue with [ROS 2 building blocks](ros2-primer.md), [TF and coordinate frames](tf-primer.md), and then [How to read the code](code-guide.md).

## Using the architecture for debugging

Every arrow should correspond to an inspectable ROS interface or TF: point-cloud topic, `/scan`, `/map`, `map → base`, planner action, `/cmd_vel`, and the Unitree request topic. Debugging follows the arrows until the first contract is not satisfied.
