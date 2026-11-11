# Land-base benchmarks from published woodlot management plans

This page compares our public-data land-base calculations with published
woodlot management plans that report gross land base, analysis/forest land
base, and timber harvesting land base.

## Benchmarks found

| Licence | Source | Published GLB | Published AFLB / net | Published THLB | Published AAC | Our AOI | Our VRI area | Our Proxy THLB | Our calibrated net |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| W1674 | Woodlot Management Plan #2 (2024) | 402.0 ha (gross 406.2) | 395.2 ha | **303.8 ha** | 2,425 m³/yr | 406.21 ha | 406.21 ha | 329.26 ha | pending build |
| W1832 | Management Plan #1 (2000) | 619.4 ha | 479.3 ha* | **398.6 ha** | 1,043 m³/yr | 593.45 ha | 593.45 ha | 460.06 ha | pending build |
| W0007 | Management Plan #4 / W4W report (2001) | 275 ha | 275.4 ha net; 261.4 ha netdown | not stated | 2,600 m³/yr (current); 2,672 (2001) | 283.56 ha | 283.56 ha | 226.44 ha | 209.58 ha |

\* W1832 AFLB is derived from the plan's Table 6: 619.4 ha total less 100%
netdowns of 30.2 + 1.8 + 91.9 + 16.2 ha = 479.3 ha. The plan calls the
remaining area the **Timber Management Landbase** (398.6 ha), after partial
netdowns.

## Comparison

### W1674 — modern W4W 4.4 plan

The plan's W4W Volume Calculation Report reports:

```text
Total Area: 402.0 ha
Net Area: 395.2 ha
THLB Area: 303.8 ha
LRSY: 3,140 m³/year
AAC: 2,425 m³/year
```

Our public-data results:

- AOI **406.21 ha** vs 402.0 ha total (+1.0%)
- VRI area **406.21 ha** vs 395.2 ha net (+2.8%)
- Proxy THLB **329.26 ha** vs 303.8 ha THLB (**+8.4%**)

The modern plan is the strongest benchmark: our land base is close, but our
Proxy THLB is less netted than the local plan by about 25 ha.

The March 2026 public AAC listing currently gives W1674 **2,255 m³/year**,
while the 2024 plan proposed **2,425 m³/year**. That difference is separate
from the land-base comparison.

### W1832 — older W4W 3-era plan

The plan's Table 6 gives:

```text
Total Area: 619.4 ha
100% netdowns: 140.1 ha
Timber Management Landbase: 398.6 ha
AAC: 1,043 m³/year (accessible portion 618 m³/year)
```

Our public-data results:

- AOI **593.45 ha** vs 619.4 ha total (-4.2%)
- VRI area **593.45 ha** vs AFLB 479.3 ha (+23.8% — VRI is gross forest area,
  not the plan's netted AFLB)
- Proxy THLB **460.06 ha** vs 398.6 ha THLB (**+15.4%**)
- Proxy THLB vs the plan's AFLB 479.3 ha: **-4.0%**

The public AOI is smaller than the plan's total; the plan includes Crown and
private land and a different boundary vintage. The Proxy THLB sits between the
plan's AFLB and THLB, which is consistent with the Proxy THLB being a strategic
midpoint rather than a local netdown.

### W0007 — older Woodlot 3 report

The 2001 report is not a W4W 4.4 report; it reports:

```text
Total Net Area: 275.4 ha
Netdown Area: 261.4 ha
Harvest Rate: 2,672 m³/year
```

Our public-data results:

- AOI **283.56 ha** vs 275 ha gross (+3.1%)
- VRI area **283.56 ha** vs 275.4 ha net (+2.9%)
- Proxy THLB **226.44 ha** vs 261.4 ha netdown (-13.4%)
- Calibrated net **209.58 ha** vs 261.4 ha netdown (-19.8%)

This is a weak benchmark because the inventory, yield model, and planning
assumptions are from 2001. It does show that the public Proxy THLB is not
always more generous than a local plan; it can be lower.

## What the benchmarks imply

1. **Our GLB/AOI is in the right range.** W1674 is within 1%, W1832 within 4%.
2. **Our Proxy THLB is not a local THLB.** It is 8–15% higher than the modern
   local THLBs in W1674 and W1832, and 13% lower than the old W0007 netdown.
3. **A local netdown factor is needed.** The ratios of published THLB to our
   Proxy THLB are:

   | Licence | Published THLB / our Proxy THLB |
   |---|---:|
   | W1674 | 303.8 / 329.26 = **0.923** |
   | W1832 | 398.6 / 460.06 = **0.866** |
   | W0026 calibration | 660.82 / 667.38 = **0.990** |

   A range of roughly **0.87–0.99** is the honest current uncertainty band.

4. **W0026's 660.8 ha calibration is consistent with the Proxy THLB**, while
   W1674/W1832 suggest local netdowns closer to 0.87–0.92. That is exactly the
   kind of local refinement a real management plan or W4W project would
   provide.

## Sources

- W1674 Management Plan #2:  
  <https://crgl.ca/wp-content/uploads/2024/08/W1674-Woodlot_Management_Plan_2_Document_Public.pdf>  
  local: `data/library/benchmarks/W1674-management-plan-2.pdf`
- W1832 Management Plan #1:  
  <http://winlawwoodlot.ca/mwp/W1832_mp.pdf>  
  local: `data/library/benchmarks/W1832-management-plan-1.pdf`
- W0007 Management Plan #4:  
  <http://www.woodlot0007.ca/documents/W0007planNov22.pdf>  
  local: `data/library/benchmarks/W0007-management-plan-4.pdf`
- W0007 W4W report:  
  <http://woodlot0007.ca/documents/W0007reportNov12.pdf>  
  local: `data/library/benchmarks/W0007-harvest-report-2012.pdf`

## Caveats

- These are different inventory vintages and local netdowns.
- VRI area is not AFLB; the W1832 VRI area is gross forest area.
- The W0007 report predates W4W 4.4 and uses Woodlot 3.
- W1674 and W1832 WS4 builds were still pending when this benchmark was
  written; their calibrations will be added to the register after build.
- Proxy THLB is a provincial strategic layer, not a substitute for a local
  management plan or statutory THLB.
