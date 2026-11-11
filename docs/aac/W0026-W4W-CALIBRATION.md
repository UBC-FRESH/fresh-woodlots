# W0026 — reverse-engineered Woodlot for Windows inputs

## Result

The published AAC is **7,311 m³/year**.

A simple oldest-first, 250-year even-flow model, applied to the W0026 WS4
fragment/yield data, reproduces that rate with an **effective net productive
area of about 660.8 ha**:

| Input | Value |
|---|---:|
| Gross VRI fragment area used in the model | **732.48 ha** |
| Calibrated THLB factor | **0.9022** |
| Calibrated net area | **660.82 ha** |
| Max even flow at factor 1.0 | 8,103.9 m³/yr |
| Published AAC / net area | **11.06 m³/ha/yr** |
| Net area as % of AAC report area (1,110 ha) | 59.5% |
| Net area as % of AOI (1,027.92 ha) | 64.3% |
| Net area as % of Proxy THLB (667.38 ha) | **99.0%** |
| Net area as % of gross VRI (732.48 ha) | 90.2% |

The headline is not the exact factor; it is that the published AAC is
consistent with a **net THLB of roughly 590–700 ha**, with the Proxy THLB
(667.38 ha) sitting almost exactly in the middle.

## Recommended effective input set

Use the 276 W0026 fragments (144 blocks; managed and unmanaged curves), with:

- **Gross area:** 732.48 ha
- **THLB factor:** 0.9022
- **Net area:** 660.82 ha
- **Harvest rule:** oldest-first priority queue
- **Flow:** constant non-declining even flow
- **Horizon:** 250 years
- **Period width:** 5 years
- **Minimum harvest age:** 40 years
- **Regeneration:** clearcut, reset age to 0, same yield curve
- **Yields:** WS4 compiled `feature.Yield.managed.Total` and
  `feature.Yield.unmanaged.Total` curves
- **Partial cutting / private land:** not modelled separately; the single
  THLB factor absorbs them in this first calibration

At factor 1.0 the model produces 8,103.9 m³/yr. Scaling the area by
`7,311 / 8,103.9 = 0.9022` produces the published rate.

## Managed-only alternative

If only the WS4 **managed** fragments are used (449.60 ha), the result is:

| Input | Value |
|---|---:|
| Managed base area | 449.60 ha |
| Max even flow at factor 1.0 | 5,587.6 m³/yr |
| Calibrated factor | **1.3084** |
| Calibrated net area | **588.27 ha** |
| Net area as % of Proxy THLB | 88.2% |

This requires **138.7 ha more** than the managed WS4 fragments. That extra area
is plausibly unmanaged, private (Schedule A), or otherwise not present as a
WS4 managed fragment. It is not evidence of a specific ownership split.

## Sensitivity

The calibrated net area is not a single precise number. Across minimum harvest
ages and period widths:

| Model | Min age | Period | Net area (ha) | % of Proxy THLB |
|---|---:|---:|---:|---:|
| all VRI | 40 | 5 yr | 660.8 | 99.0% |
| all VRI | 40 | 10 yr | 611.2 | 91.6% |
| all VRI | 60 | 5 yr | 664.9 | 99.6% |
| all VRI | 60 | 10 yr | 611.2 | 91.6% |
| all VRI | 80 | 5 yr | 697.7 | 104.6% |
| all VRI | 80 | 10 yr | 649.5 | 97.3% |
| managed | 40 | 5 yr | 588.3 | 88.2% |
| managed | 40 | 10 yr | 534.4 | 80.1% |
| managed | 60 | 5 yr | 588.3 | 88.2% |
| managed | 60 | 10 yr | 554.7 | 83.1% |
| managed | 80 | 5 yr | 672.5 | 100.8% |
| managed | 80 | 10 yr | 570.7 | 85.5% |

The all-VRI case centers on the Proxy THLB. The managed-only case centers
somewhat below it and needs additional area to close the gap.

## What this means for the WS4 demo

The WS4 **factor-weighted managed area is 449.60 ha**. That is not the same
denominator as the published AAC. The AAC is consistent with an effective net
area near **660 ha**, not 450 ha.

Therefore:

- the WS4 **1.2× AAC baseline** is a stress scenario, not a reproduction of
  the published AAC;
- a **1.0× W4W target** is the right comparison scenario;
- the current WS4 per-hectare intensity of `7,311 / 449.60 = 16.26 m³/ha/yr`
  is not the AAC's MAI. It is the AAC divided by a smaller VRI-covered managed
  area;
- the WS4 model is still useful for spatial and operational questions, but it
  should not be presented as a statutory AAC reproduction.

I added a **“W4W published AAC (1.0×)”** saved scenario to the portal. It sets
the target floor and ceiling equal to the public AAC (no 1.2× uplift).

## Reproduce

```bash
cd /srv/shared-data/gep/ws4/fresh-woodlots
python scripts/calibrate_w4w_aac.py
```

Outputs:

- `data/aac/w0026/w4w_calibration.json`
- `data/aac/w0026/w4w_plausible_inputs.csv`
- this report and the copied input table under `docs/aac/`

## Caveats

- This is a **simplified replica** of Woodlot for Windows, not the actual W4W
  project. It does not implement W4W's exact harvest-age logic, partial-cut
  accounting, roads, private-land split, or all constraints.
- The calibration is underdetermined: several assumption sets can match 7,311.
  The robust conclusion is the **range of net area**, not the last decimal of
  the factor.
- The yield curves come from the WS4 compiled dataset, not from a recovered
  W4W project file.
- The single THLB factor is an effective area multiplier. It should not be
  interpreted as a legal THLB determination.
- Any non-public W4W project or management plan would supersede this
  calibration.
