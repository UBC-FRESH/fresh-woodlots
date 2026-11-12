# Tactical validation set

Date: 2026-11-12  
Status: validation complete; W1832 remains on the v2 land-base benchmark

This page tests whether the FHOPS tactical–operational pipeline generalizes
beyond the three featured pilots. The validation set is small and uses the
woodlots with public management plans in the document library.

## Method

For the clearcut candidates, the tactical scenario is built from **all
compiled WS4 blocks**, not only the small set selected by the compressed
first-period FHOPS pilot. Each block gets its real polygon area and a share of
the ten-year published AAC; the tactical MILP selects annual block areas and
product volumes, then ten annual operational seasons are solved.

The candidate-pool change fixed a material issue found during validation: the
original compressed FHOPS selections for W1548 covered only **2.1 ha** while
carrying 40,000 m³, or about **18,900 m³/ha**. That is not a credible
operational footprint. Using all WS4 blocks gives a plausible ten-year
volume-per-area figure.

Published plan values are compared with the v1/v2 land-base calibration, not
treated as a direct check on the tactical MILP. The tactical model is a
scheduling layer, not a new AAC calculation.

## Results

| Licence | Basis | Annual AAC | Tactical blocks | Tactical area | 10-year volume | Volume/ha | Published benchmark |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| W1674 | clearcut | 2,255 m³ | 35 | 256.0 ha | 22,550 m³ | 88.1 m³/ha | THLB 303.8 ha; plan AAC 2,425 m³ |
| W0007 | clearcut | 2,600 m³ | 52 | 221.7 ha | 26,000 m³ | 117.3 m³/ha | netdown 261.4 ha; 2001 AAC 2,672 m³ |
| W0026 | clearcut | 7,311 m³ | 144 | 732.5 ha | 73,110 m³ | 99.8 m³/ha | Proxy THLB 667.4 ha; no published THLB |
| W1548 | clearcut | 4,000 m³ | 85 | 404.8 ha | 40,000 m³ | 98.8 m³/ha | no published THLB in library |
| W2023 | clearcut | 5,833 m³ | 120 | 635.3 ha | 58,330 m³ | 91.8 m³/ha | no published THLB in library |
| W1832 | partial cut | 1,043 m³ | — | — | — | — | **v2 415.7 ha vs published 398.6 ha (+4.3%)** |

The ten-year volume-per-area range for the clearcut runs is **88–117 m³/ha**,
which is plausible as a ten-year harvest footprint. It is not a yield-table
validation and does not prove the local THLB.

## Land-base checks

| Licence | Our v1 net | Our v2 net | Published THLB | Result |
| --- | ---: | ---: | ---: | --- |
| W1674 | 321.1 ha | — | 303.8 ha | v1 **+5.7%** |
| W0007 | 209.6 ha | — | 261.4 ha netdown | v1 **−19.8%** (weak benchmark) |
| W1832 | 105.3 ha | **415.7 ha** | 398.6 ha | v1 invalid; v2 **+4.3%** |
| W0026 | 660.8 ha | — | Proxy 667.4 ha | v1 **99.0% of Proxy** |

W1832 is **not** given a tactical plan: its management plan documents partial
cutting/commercial thinning, while the current tactical scenario assumes a
ground-based clearcut system. Using v2 for its land base is the correct
comparison.

## Findings

1. The tactical pipeline runs cleanly on the benchmark woodlots.
2. The original compressed FHOPS block selection is not a sufficient candidate
   pool for woodlots with sparse first-period schedules. W1548 was the clear
   failure case; using all WS4 blocks fixes it.
3. Selected tactical area is not a published THLB. W1674 (256 ha) and W0007
   (221.7 ha) are plausible harvest footprints but sit below their published
   THLBs; do not relabel them as THLB.
4. W1674 remains the strongest clearcut calibration benchmark (+5.7%);
   W1832 remains the strongest partial-cut benchmark (v2 +4.3%).
5. Product yields in the tactical model are still a transparent 70/30
   sawlog/pulp split, not WS4 product curves.

## Reproduce

```bash
python scripts/build_tactical_plan.py \
  --block-source all \
  --only wl-w0026 --only wl-w1548 --only wl-w2023 \
  --only wl-w1674 --only wl-w0007
python scripts/build_fhops_tactical_ops.py \
  --only wl-w0026 --only wl-w1548 --only wl-w2023 \
  --only wl-w1674 --only wl-w0007
python scripts/prepare_fhops_maps.py \
  --only wl-w0026 --only wl-w1548 --only wl-w2023 \
  --only wl-w1674 --only wl-w0007
python scripts/prepare_theatre.py \
  --only wl-w0026 --only wl-w1548 --only wl-w2023 \
  --only wl-w1674 --only wl-w0007
```

## Caveats

- The validation set is five clearcut/pilot instances plus one partial-cut
  land-base check, not a population-wide validation.
- The tactical model does not include roads, silviculture, landing geometry,
  or real costs.
- The first-period FHOPS pilots remain compressed demonstrations for the other
  woodlots.
- W1548/W2023 have no published THLB in the local library.
