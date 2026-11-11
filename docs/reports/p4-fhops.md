# P4 FHOPS batch

Date: 2026-11-10
Status: complete for the first operational period

## Result

| State | Count |
|---|---:|
| Built CFAs | 62 |
| FHOPS scenarios | **62** |
| FHOPS solved | **62** |
| Failed | **0** |
| Batch wall clock | 23:07 |
| Concurrency | 8 jobs |

Every instance has:

```text
fhops/scenario.yaml
fhops/out/heur_solution.csv
fhops/summary.json
```

## Method

For each CFA the batch uses the first 10-year period of the WS4 AAC baseline:

- volume target = AAC × 10
- four-machine ground-based chain:
  feller-buncher → grapple skidder → roadside processor → loader
- daily rate sized from the volume, horizon at least 450 days
- FHOPS `validate`, `solve-heur`, `evaluate`

This is a contract and integration pilot. Rates are fixed, access is not
modelled, and costs are placeholders.

## Examples

| CFA | Blocks completed | Production m³ | Makespan days |
|---|---:|---:|---:|
| K1E Bamfield | 3 | 8,600 | 73 |
| K2E Logan Lake | 14 | 183,000 | 261 |
| K3X FNFN/NRRM | 44 | 1,850,000 | 405 |
| K4R Chinook | 73 | 657,200 | 436 |
| K3W Three Rivers | 65 | 532,500 | 425 |

All 62 finished with zero sequencing violations.

## Limits

- one period, not a rolling plan
- fixed production rates, not stand- or machine-specific
- no road network, landing geometry, or terrain
- placeholder costs
- no harvest-system choice per block

## Next

1. Attach public road and terrain data.
2. Replace fixed rates with the FHOPS productivity presets.
3. Add harvest-system choice per block.
4. Expose the FHOPS plan beside the WS4 run in the portal.
5. Build rolling 3-period plans.
