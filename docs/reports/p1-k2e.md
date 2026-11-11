# P1 pilot report: K2E Logan Lake

Date: 2026-11-10
Status: built end to end with a THLB land base, an AAC-balanced baseline, and a
FHOPS operational pilot

## Scale

| Field | Value |
| --- | --- |
| CFA | K2E Logan Lake Community Forest |
| AOI | 16,722.44 ha |
| AAC | 18,300 m³/yr |
| Upstream build wall clock | 13:26 |
| Peak resident memory | 12.3 GB |

## THLB land base

The Provincial Proxy THLB intersects **10,831.91 ha** of the 16,722.44 ha AOI
(**64.8%**). The VRI is clipped to the AOI (2,194 polygons, 16,722.44 ha).
After clipping and splitting by THLB:

- managed: **7,343.05 ha**
- unmanaged: **1,461.63 ha**
- total forested: **8,804.68 ha**
- WS4 blocks: **1,595**
- WS4 treatments: **58**

## AAC result

Targets: 183,000-219,600 m³ per 10-year period (18,300-21,960 m³/yr).
A 5-minute greedy search met **all ten periods** at the ceiling:

| Period | Harvest m³ | Status |
| --- | --- | --- |
| 1 | 219,596 | met |
| 2 | 219,599 | met |
| 3 | 219,600 | met |
| 4 | 219,599 | met |
| 5 | 219,600 | met |
| 6 | 219,600 | met |
| 7 | 219,600 | met |
| 8 | 219,598 | met |
| 9 | 219,597 | met |
| 10 | 219,597 | met |

Total harvest is 2,195,965 m³ over 100 years (21,960 m³/yr), inside the
1.2x AAC band.

## FHOPS pilot

The first AAC period has 14 blocks and 183,000 m³. The generated scenario uses
a four-machine ground-based chain over 300 days:

```text
completed_blocks: 14.000
total_production: 183000.000
remaining_work_total: 0.000
makespan_day: 261
sequencing_violation_count: 0
```

## Lessons

1. **Use `--seed-greedy` for every CFA.** The unseeded 2-minute search missed
   every period; the greedy seed met all ten.
2. **THLB changes the answer.** The pre-THLB K2E search hit ~1.9x AAC. With the
   Proxy THLB and a 1.2x band, the same AAC is met cleanly.
3. **The VRI clip changes the curves.** The clipped VRI (2,194 polygons) is
   now the source for curves and species proportions; the WS4 block count moved
   from 1,593 to 1,595.
4. **Peak memory is material.** 12.3 GB for a 16.7k ha CFA means the batch
   build needs a memory-aware scheduler.
5. **FHOPS horizons must scale with the volume.** 14 blocks at 183,000 m³ need
   a ~250-day horizon with one four-machine chain.

## Next

1. Run K3X FHOPS on its first AAC period.
2. Add a non-declining flow shape instead of a flat band.
