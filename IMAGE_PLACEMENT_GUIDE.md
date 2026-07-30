# Documentation image placement guide

All website images live under:

```text
docs/assets/images/
├── network/
├── mapping/
├── planner/
└── alignment/
```

The documentation already references these files. To replace an image later, overwrite the file while keeping the same filename; no Markdown edit is required.

## Current placement

| Image | Page |
|---|---|
| `network/vmware_bridged_adapter.png` | VMware dual-NIC tutorial |
| `network/vmware_nat_adapter.png` | VMware dual-NIC tutorial |
| `network/ubuntu_dual_nic_status.png` | Home page and network verification |
| `mapping/map_contact_sheet.png` | Home-page project overview |
| `mapping/floor_1_raw.png` / `floor_1_clean.png` | Operational map boundary page |
| `mapping/floor_3_second_pass_raw.png` / `floor_3_clean.png` | Operational map boundary page |
| `mapping/floor_1_trajectory_stops.png` / `floor_3_trajectory_stops.png` | Acquisition trajectory page |
| `planner/01_...png` / `02_...png` / `03_...png` | Planner debugging story |
| `alignment/*.png` | Floor-alignment page and home page |

## Images still worth adding later

- a clean Go2 EDU + expansion-dock hero photograph;
- a close-up showing the dock installation;
- an optional terminal screenshot of the voice module running;
- a polished replacement for the trajectory/stop overlays.

Recommended future paths:

```text
docs/assets/images/hardware/go2_with_dock.jpg
docs/assets/images/hardware/expansion_dock_closeup.jpg
docs/assets/images/voice/voice_runtime.png
```

Keep screenshots wide, crop unrelated desktop areas, and avoid serial numbers, account names and other unnecessary private details.
