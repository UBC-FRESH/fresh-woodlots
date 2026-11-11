# P1 pilot report: K3X FNFN/NRRM

Date: 2026-11-10
Status: built end to end with a THLB land base and an AAC-balanced baseline

## Scale

| Field | Value |
| --- | --- |
| CFA | K3X FNFN/NRRM Community Forest |
| AOI | 184,681.61 ha |
| AAC | 185,000 m³/yr |
| Build wall clock | 26:37 |
| Peak resident memory | 13.1 GB |
| VRI clip | 24,872 polygons, 184,681.61 ha |
| FEMIC fragments | 16,469 |
| Clipped fragments | 24,435 rows, 133,387 ha |
| WS4 blocks | 24,435 |
| WS4 treatments | 18 |

## THLB land base

The Provincial Proxy THLB intersects **46,058.64 ha** of the 184,681.61 ha AOI
(**24.9%**). The VRI is clipped to the AOI (24,872 polygons, 184,681.61 ha).
After clipping and splitting by THLB:

- managed: **43,555.40 ha**
- unmanaged: **89,831.82 ha**
- total forested: **133,387.22 ha**

## AAC result

Targets: 1,850,000-2,220,000 m³ per 10-year period (185,000-222,000 m³/yr).
A 10-minute greedy search met **all ten periods** at the upper band:

| Period | Harvest m³ | Status |
| --- | --- | --- |
| 1 | 2,220,000 | met |
| 2 | 2,220,000 | met |
| 3 | 2,220,000 | met |
| 4 | 2,220,000 | met |
| 5 | 2,220,000 | met |
| 6 | 2,220,000 | met |
| 7 | 2,220,000 | met |
| 8 | 2,220,000 | met |
| 9 | 2,220,000 | met |
| 10 | 2,220,000 | met |

Total harvest is 22,200,000 m³ over 100 years (222,000 m³/yr, 1.2x AAC).
The schedule sits exactly on the ceiling, so the next iteration should tighten
the ceiling or add a non-declining constraint.

## FHOPS pilot

The first AAC period has 44 blocks and 1,850,000 m³. The generated scenario
uses a four-machine ground-based chain at 10,000 m³/day over 500 days:

```text
completed_blocks: 44.000
total_production: 1850000.000
remaining_work_total: 0.000
makespan_day: 412
sequencing_violation_count: 0
```

## Issues

1. **SB has no TIPSY table.** The bridge maps black spruce (`SB`) to white
   spruce (`SW`) and records the mapping in the sidecar manifest.
2. **The first build failed at the TIPSY bridge.** The K3X species mix includes
   `Sb`, which the initial override file did not map. Adding `SB: SW` fixed it.
3. **The upstream stage was re-run once.** Editing the build script while bash
   was executing it caused a second inventory/VDYP pass. No data was lost, but
   build time doubled.
4. **FHOPS scales to K3X.** The first period has 44 blocks; the pilot
   completes all of them in 412 days at 10,000 m³/day.

## Next

1. Add a non-declining or even-flow shape to the AAC targets instead of a flat
   band.
2. Compare the three pilots' peak memory and add a batch scheduler.
3. Wire the K3X FHOPS plan into the portal.
4. Start the 59-CFA batch with a memory-aware queue.
