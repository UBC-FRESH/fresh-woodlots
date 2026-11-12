# Calibration v2 — partial-cut method

## Why v2

The v1 calibration is a **clearcut/oldest-first** replica. It is appropriate for
plans that use clearcut or even-aged management, but not for partial-cut or
commercial-thinning plans.

The W1832 benchmark demonstrates the problem:

| Model | Effective net area | Published THLB | Result |
|---|---:|---:|---|
| v1 clearcut | 105.32 ha | 398.6 ha | **not comparable** |
| v2 partial cut | **415.67 ha** | 398.6 ha | **+4.3%** |

## v2 method

- oldest-first priority queue;
- partial volume removal: **30%/entry**;
- re-entry: **20 years**;
- minimum harvest age: **80 years** for the W1832 benchmark;
- minimum residual volume: 50 m³/ha;
- residual stand continues to grow on the same yield curve;
- effective PCAF/yield factor: **0.65**, absorbing the W4W 0.80 PC adjustment,
  full-cycle-tree netdown, and road netdown;
- 250-year horizon, 5-year periods.

The factor is solved so the simplified model reproduces the published AAC.

## Results

| Licence | Method | Calibrated net | Published THLB | Difference |
|---|---|---:|---:|---:|
| W1674 | v1 clearcut | **321.05 ha** | 303.8 ha | +5.7% |
| W1832 | v2 partial cut | **415.67 ha** | 398.6 ha | +4.3% |
| W0026 | v1 clearcut | **660.82 ha** | n/a | 99.0% of Proxy THLB |
| W0026 | v2 partial cut | 2,879.59 ha | n/a | not plausible |

W0026 is deliberately a counter-example: applying the partial-cut v2 model to it
requires about 4.3× the Proxy THLB. The v1 clearcut calibration is the credible
one for W0026.

## What this means

- The calibration method must be chosen per plan, not globally.
- v1 remains the default for the population until a plan's silviculture system is
  known.
- v2 is the right tool for partial-cut/thinning woodlots and should be selected
  from the management plan or WLP.
- The portal flags v1 factors outside a plausible range as **method check** so a
  low-factor result is not presented as a land-base fact.

## Reproduce

```bash
python scripts/calibrate_w4w_aac_v2.py \\
  --slug wl-w1832 --min-age 80 --removal 0.30 --reentry 20 --pcaf 0.65
```

Outputs per instance:

```text
config/w4w_calibration_v2.json
config/w4w_plausible_inputs_v2.csv
config/W4W-CALIBRATION-V2.md
```
