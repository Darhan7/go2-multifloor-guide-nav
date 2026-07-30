# Troubleshooting

## VM can reach the Internet but not Go2

- confirm the bridged adapter is connected to the correct physical interface;
- confirm an address in `192.168.123.0/24` exists;
- confirm the route uses the bridged interface;
- ping the dock at `192.168.123.18`.

## VM can reach Go2 but DNS fails

- ensure the default route is on the NAT interface;
- inspect `resolvectl status`;
- bring the NAT profile up again.

## `Package 'go2_core' not found`

The workspace was not built or `install/setup.bash` was not sourced.

## `/scan` missing

Check the point-cloud input, `cloud_accumulation`, TF to `base_link`, and the conversion node.

## Planner node has the wrong name

Start with `-r __node:=planner_server` so lifecycle and parameter commands target `/planner_server`.

## Straight line crosses walls

Do not interpret it as valid planning. Verify map server, planner lifecycle, static layer, global costmap dimensions and occupancy statistics.

## Planner returns an empty path

Check whether the start/goal lies in an occupied cell, unknown space or the inflation zone. Create a separate robot-safe anchor.

## Script works only under `/home/unitree`

The archived scripts use absolute paths. Refactor them to accept project root, map YAML, semantic YAML and output directory as arguments.
