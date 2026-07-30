# Environment setup: first decide what runs on which computer

This project involves Windows, an Ubuntu VM, and the Go2 expansion dock. A common beginner mistake is to run a correct command in the wrong terminal, or to assume that being able to edit the repository means the robot runtime is installed.

## Responsibilities of the three environments

| Location | Confirmed environment | Main responsibility |
|---|---|---|
| Windows host | Windows 11 | VMware, physical-network selection, downloads |
| Ubuntu VM | Ubuntu 24.04.4, Python 3.12.3, Git 2.43.0, ROS 2 Jazzy installed | Dual-NIC access, SSH, editing, archival work, and documentation; not the primary Foxy/Nav2 runtime |
| Go2 expansion dock | Ubuntu 20.04.5, ARM64 Jetson, Python 3.8.10, ROS 2 Foxy | Go2 DDS data, point-cloud processing, SLAM, AMCL, Nav2, and motion bridging |

!!! important
    Commands under `/home/unitree/...` belong to the dock. Paths under `/home/<vm-user>/...` belong to the VM. The OS version, ROS distribution, and CPU architecture differ.

## What a ROS 2 distribution means

ROS 2 is not one Python library. A distribution such as Foxy, Humble, or Jazzy is a coordinated set of packages, message definitions, CLI tools, middleware interfaces, and APIs. Dock packages therefore commonly use names such as `ros-foxy-*`.

Do not assume that Humble or Jazzy launch files, parameter names, and APIs are identical to Foxy. Newer Nav2 documentation remains valuable for concepts, while execution follows the archived Foxy files.

## DDS, RMW, and CycloneDDS

ROS 2 communication is normally carried by DDS middleware rather than a central message server.

- **DDS** defines discovery and data exchange behavior;
- **RMW** is the ROS 2 abstraction over middleware implementations;
- **CycloneDDS** is the implementation used here;
- `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` selects its ROS adapter;
- `CYCLONEDDS_URI` points to the XML configuration, including network interfaces.

The archived dock environment uses:

```bash
source ~/cyclonedds_ws/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=~/cyclonedds_ws/cyclonedds.xml
```

No custom `ROS_DOMAIN_ID` was explicitly preserved.

## Workspaces, packages, and `colcon build`

A typical ROS 2 workspace contains:

```text
workspace/
├── src/       source packages
├── build/     build intermediates
├── install/   installed executables, libraries, shares, and setup scripts
└── log/       build logs
```

A package is the unit registered in the ROS package index. `colcon build` resolves package dependencies and installs the results. Runtime lookup uses the install space, not an arbitrary source folder.

## What `source setup.bash` actually does

The project loads:

```bash
source /opt/ros/foxy/setup.bash
source /home/unitree/graph_pid_ws/install/setup.bash
source /home/unitree/go2_nav_official_ws/install/setup.bash
```

`source` executes the setup script in the current shell and extends package indexes, executable paths, Python paths, and library paths. It is not an installer and does not automatically affect every new terminal.

The later workspaces form overlays over earlier ones. Check the selected package with:

```bash
ros2 pkg prefix nav2_planner
ros2 pkg prefix go2_perception
ros2 pkg prefix go2_twist_bridge
```

## Cloning is not installing

```bash
git clone <repository-url>
cd go2-multifloor-guide-nav
```

This downloads project files; it does not create `/opt/ros/foxy`, Unitree messages, or CycloneDDS. The repository includes documentation setup, VM network configuration, preflight checks, dependency notes, and dock environment examples.

Because the historical `graph_pid_ws` source was not fully archived, the repository does not claim to reconstruct a blank dock with one command. The safer method is to install and verify one layer at a time.

## Example environment entry point

```bash
cp config/examples/dock_environment.sh.example \
   ~/go2_dock_environment.sh
source ~/go2_dock_environment.sh
./tools/preflight_check.sh dock
```

The preflight tool does not install missing software. It identifies which layer—OS, ROS, RMW, package lookup, maps, or interfaces—is not ready.

## Why the VM's Jazzy installation is not the Foxy runtime

“Both use ROS 2” does not guarantee binary or API compatibility. Message packages, ABI, launch APIs, dependencies, and plugins may differ. The VM is useful for editing and modern ROS learning; the archived robot runtime remains Foxy on the dock.

## Further reading

- [Official Unitree ROS 2 repository](https://github.com/unitreerobotics/unitree_ros2)
- [ROS 2 Foxy documentation](https://docs.ros.org/en/foxy/)
- [Alternative Go2 laboratory guide](https://ztl3106742440-hub.github.io/go2-tutorial/)
- [Further learning routes](../reference/further-learning.md)
