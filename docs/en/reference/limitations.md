# Engineering boundaries and next steps

A useful engineering archive should show what works and also make the next session easy to continue. The items below are not reasons the project cannot be used; they are the highest-value tasks to resume when the robot and site are available again.

## Priorities for the next on-site session

- rebuild and tune `amcl_foxy.yaml`, keeping a public example and a site-calibrated version;
- record validated Floor 1 lobby, elevator and presentation anchors;
- connect floor switching, destination-floor initialization and the elevator state machine into one task script;
- connect the voice-intent adapter to the semantic YAML and building graph;
- run a physical safety pass on the final operational map boundaries.

## Historical material not preserved in the export

- the exact `localization/config/amcl_foxy.yaml` used on site;
- the source provenance of the already-built `graph_pid_ws`;
- complete raw sensor rosbags for every mapping run.

None of these prevents understanding the system or reproducing the planner-only workflow. They simply mean that a new environment should be calibrated and verified like any real robot deployment.

## Historical naming note

The directory name `floor_3_recovered` refers to the more deliberate second Floor 3 mapping pass; it was not recovered from a corrupted file or rosbag. The public documentation calls it **Floor 3 second pass**.

## Public material

The maps, location names and semantic coordinates have permission for public release. Go2 hardware photographs can be added later to the home or architecture page.
