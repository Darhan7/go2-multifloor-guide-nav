# Runtime dependency notes

`apt-foxy.txt` is a readable reference list, not a claim that one apt command reconstructs the original dock. Unitree message packages and CycloneDDS are built from the official `unitree_ros2` workspace, while the historical `graph_pid_ws` source was not fully archived.

Install and verify in layers:

1. Ubuntu 20.04 and ROS 2 Foxy;
2. CycloneDDS RMW and Unitree messages/API;
3. common SLAM, localization, and Nav2 packages;
4. Go2 perception and bridge workspace;
5. project maps, scripts, and configuration;
6. `tools/preflight_check.sh dock`.

Do not blindly install this list on a newer ROS distribution by replacing every occurrence of `foxy`; APIs and package availability may differ.
