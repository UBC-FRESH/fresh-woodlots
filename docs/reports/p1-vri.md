# VRI pre-clip

Date: 2026-11-10
Status: implemented and applied to K1E; K2E and K3X rebuilds running

## Problem

FEMIC's custom-boundary mode selects VRI polygons that intersect the AOI but
does not clip them. For a small community forest the overhang can dominate the
model:

- K1E AOI: 354.91 ha
- K1E source VRI selection: 43 polygons
- K1E fragments before clipping: 781.24 ha

The fragment clip fixed the WS4 area, but the yield curves and species
proportions were still derived from polygons outside the AOI.

## Fix

`scripts/prepare_vri.py` now:

1. reads the VRI Rank 1 polygon layer for the AOI bounding box;
2. clips it to the AOI;
3. writes `<instance>/data/external/bc/vri/2025/VEG_COMP_LYR_R1_POLY_2025.gpkg`;
4. symlinks the shared TSA, site-productivity, VDYP input, and THLB raster
   sources into `<instance>/data/external`.

The run profile points at the clipped VRI:

```yaml
source_paths:
  vri_rel_candidates:
    - bc/vri/2025/VEG_COMP_LYR_R1_POLY_2025.gpkg
```

and the build sets:

```bash
export FEMIC_EXTERNAL_DATA_ROOT=<instance>/data/external
```

The VDYP input polygon/layer tables are aspatial and remain in the shared GDB.
They are joined to the clipped VRI by feature ID, so the curves and species
proportions inherit the clip.

## K1E result

- clipped VRI: 43 polygons, 354.91 ha
- THLB: 133.35 ha (37.6%)
- WS4: 57 blocks, 6 treatments
- 1.2x AAC search: **60,769 m³** over 100 years
- periods met: 1, 7, 10 of 10
- FHOPS: 3 blocks, 8,600 m³, 73-day makespan

Before the VRI clip the same K1E setup produced 76,864 m³. The clipped VRI
removes the overhanging volume and makes the AAC gap visible: the small
coastal instance cannot hold the 1.2x band in every period.

## K2E result

- clipped VRI: 2,194 polygons, 16,722.44 ha
- THLB: 10,831.91 ha (64.8%)
- WS4: 1,595 blocks, 58 treatments
- 1.2x AAC search: **2,195,965 m³** over 100 years (21,960 m³/yr)
- all ten periods met at the 219,600 m³ ceiling
- FHOPS: 14 blocks, 183,000 m³, 261-day makespan

K2E is insensitive to the VRI clip at the whole-AOI scale because the AOI is
large enough that the overhang is a small share. The clipped source still
matters for species proportions and curve selection.

## K3X result

- clipped VRI: 24,872 polygons, 184,681.61 ha
- THLB: 46,058.64 ha (24.9%)
- WS4: 24,435 blocks, 18 treatments
- 1.2x AAC search: **22,200,000 m³** over 100 years (222,000 m³/yr)
- all ten periods met at the ceiling
- FHOPS: 44 blocks, 1,850,000 m³, 412-day makespan
- build wall clock 26:37, peak RSS 13.1 GB

The clipped VRI and THLB together give a much smaller operable land base than
the raw AOI. The AAC search still meets the 1.2x band, but only at the ceiling;
a non-declining or tighter shape is the next test.

## Next

1. Finish the K2E and K3X clipped-VRI rebuilds.
2. Re-run the portal after the rebuilds finish.
3. Decide whether K1E needs a lower AAC or a longer search horizon.
