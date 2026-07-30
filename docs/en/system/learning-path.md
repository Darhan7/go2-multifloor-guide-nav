# How to use this tutorial: learn the system while building it

This site does not separate theory and practice into two unrelated manuals. The intended route is to **learn each concept at the moment it becomes necessary in the project**. Commands are therefore not presented as magic strings, and code is not reduced to “run this file.”

## Every practical page follows the same pattern

1. **Current task** — what the stage should produce;
2. **Concepts first** — what the terms, data structures, and mechanisms actually are;
3. **Real operation** — commands, scripts, and configuration used by the project;
4. **How the code works** — who creates each object, what enters and leaves it, and what triggers callbacks or actions;
5. **Why this design** — engineering trade-offs rather than one supposedly universal answer;
6. **How to verify it** — processes, topics, TF, files, images, and robot behavior;
7. **Where to look first when it fails** — follow the data path and find the first broken stage;
8. **Official references and alternative routes** — connect the project back to ROS 2, Nav2, Unitree, and other Go2 tutorials.

## Choose an entry point

### New to ROS 2

A useful reading order is:

```text
Architecture
→ ROS 2 building blocks
→ TF and coordinate frames
→ Reading the code
→ VMware dual NIC
→ Point clouds and map data
→ Mapping
→ AMCL and Nav2
```

You do not need prior SLAM knowledge, but basic terminal use, simple Python reading, IP addresses, and filesystem paths will help.

### Comfortable with code but new to robotics

Start with networking and the sensor pipeline. When concepts such as topics, actions, TF, QoS, and lifecycle nodes appear, the corresponding page explains them in context and links to a deeper primer.

### Already familiar with ROS 2

Skip the introductory paragraphs and go directly to the archived scripts, YAML parameters, debugging cases, and multi-floor application layer.

## Separate project values from transferable principles

For example:

```text
192.168.123.222/24      project-specific VM address
no default gateway       transferable device-LAN design

min_height: 0.1          scene-specific point-cloud parameter
height filtering         general 3D-to-2D scan method

inflation_radius: 0.65   project tuning value
inflated obstacle costs  general Nav2 costmap mechanism
```

The documentation makes this distinction explicit so that a recorded value is not mistaken for a universal robot setting.

## Cloning is not installing the runtime

`git clone` downloads code, maps, configuration, images, and documentation. It does not install ROS 2, Nav2, CycloneDDS, or Unitree interfaces. The repository includes documentation setup, VM network configuration, preflight checks, example dock environment files, and dependency notes. The robot-side runtime is still assembled and verified layer by layer, which is more transparent and debuggable than a single opaque installer.
