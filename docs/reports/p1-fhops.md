# P1 FHOPS pilot: K1E first AAC period

Date: 2026-11-09
Status: scenario validates and solves; all blocks completed

## Scenario

The FHOPS scenario is generated from the first 10-year period of the K1E AAC
baseline:

| Field | Value |
| --- | --- |
| Blocks | 3 (first K1E clipped-VRI AAC period) |
| Volume | 8,600 m³ (AAC 860 m³/yr x 10 years) |
| Harvest system | `ground_fb_skid` |
| Machines | 4 (feller-buncher, grapple skidder, roadside processor, loader) |
| Landings | 1 |
| Horizon | 120 days |
| Production rate | 250 m³ per machine-day |

Block volumes are allocated in proportion to block area. The scenario is a
contract and integration pilot, not a production operating plan: rates are
fixed, access is not modelled, and costs are placeholders.

## Commands

```bash
python scripts/build_fhops_pilot.py \
  --instance-root instances/cfa-k1e --aac 860 --days 120
cd instances/cfa-k1e/fhops
fhops validate scenario.yaml
fhops solve-heur scenario.yaml --out out/heur_solution.csv
fhops evaluate scenario.yaml --assignments out/heur_solution.csv
```

## Result

```text
fhops validate: 120 days, 3 blocks, 4 machines, 1 landing
fhops solve-heur:
  total_production: 8600.000
  remaining_work_total: 0.000
  completed_blocks: 3.000
  makespan_day: 73
  sequencing_violation_count: 0
```

The heuristic completes every block in 73 days with no sequencing violations.

## K2E scale pilot

The same generator was run on the K2E first AAC period:

- 14 blocks, 183,000 m³
- four-machine ground-based chain
- 300-day horizon, 1,500 m³ per machine-day

```text
total_production: 183000.000
remaining_work_total: 0.000
completed_blocks: 14.000
makespan_day: 257
sequencing_violation_count: 0
```

The K2E pilot shows the generator and solver scale to a realistic period
volume; the K1E pilot shows the small-community case.

## Limits

- No road, landing, or terrain geometry is attached yet.
- Production rates are fixed instead of stand- and machine-specific.
- Costs are placeholders, not FPInnovations or contractor rates.
- The scenario is one period, not a rolling operational plan.
- The WS4-to-FHOPS handoff is by block ID and volume only.

## Next

1. Attach block centroids and a road network from public data.
2. Replace fixed rates with the FHOPS productivity presets and stand metrics.
3. Add harvest-system choice per block (ground, cable, helicopter).
4. Build a rolling 3-period plan from the AAC baseline.
5. Expose the FHOPS plan beside the WS4 run in the portal.
