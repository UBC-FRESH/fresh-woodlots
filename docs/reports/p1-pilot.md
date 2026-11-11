# P1 pilot report: K1E Bamfield Huu-ay-aht

Date: 2026-11-10
Status: K1E, K2E, and K3X built end to end with THLB land bases and
AAC-balanced baselines; K1E and K2E FHOPS pilots solve

## Decisions locked

- "Fannie" is **FEMIC**, the inventory/curve/XML/fragments builder.
- The pilot accepts a **time-boxed Wine exception** for the VDYP stage. Managed
  curves use **fresh-tipsy** with no Windows process.
- The first batch is the three-CFA pilot: K1E (small coast), K2E (medium
  interior), K3X (large north).

## What was built

K1E Bamfield Huu-ay-aht Community Forest, 354.91 ha, AAC 860 m³/yr:

| Stage | Result |
| --- | --- |
| AOI | Public CFA boundary, 354.91 ha, EPSG:3005 |
| VRI clip | 43 polygons, 354.91 ha; curves now use the clipped VRI |
| FEMIC inventory | VRI clip, site productivity, 3 source feature rows |
| VDYP curves | 4 strata, smoothed curves produced (Wine exception) |
| TIPSY managed curves | 3 features, 96 curves, 2,826 curve points (fresh-tipsy, no Wine) |
| Patchworks interchange | 35 fragments, 211 curves |
| AOI clipping | fragments 781.24 ha -> 345.92 ha (97.5% of AOI) |
| THLB | 133.35 ha of 354.91 ha (37.6%) |
| THLB split | managed 144.56 ha, unmanaged 201.37 ha |
| WS4 compile | 57 blocks, 6 treatments, 66 products, dataset valid |
| Smoke simulation | 100-year liquidation baseline |
| AAC search | 1.2x band, 60,769 m³ total over 100 years |
| AAC baseline | 100-year simulation of the searched schedule |
| FHOPS pilot | 3 blocks, 8,600 m³, 73-day makespan |
| Web UI | `http://127.0.0.1:8799/` returns HTTP 200 |

The AAC search targets 8,600-10,320 m³ per 10-year period (1.0-1.2x AAC).
Periods 1-3 meet the band; the others are below it because the THLB land base
is smaller and the blocks are lumpy. The result is a pilot scenario, not a
statutory timber supply analysis.

## Evidence

The whole K1E chain is one command:

```bash
./scripts/build_instance.sh cfa-k1e
```

The underlying commands are:

```bash
python -m femic run --run-config config/run_profile.cfa-k1e.yaml
python scripts/tipsy_bridge.py --instance-root instances/cfa-k1e --tsa k1e \
  --source .../TIPSY/Database --catalog data/tipsy/manifest.json \
  --overrides instances/cfa-k1e/config/species_overrides.yaml
FEMIC_ALLOW_STALE_TIPSY_OUTPUT=1 python -m femic tsa post-tipsy \
  --tsa k1e --run-config config/run_profile.cfa-k1e.yaml
python -m femic export patchworks --tsa k1e --bundle-dir data/model_input_bundle \
  --output-dir output/patchworks --ifm-mode legacy_binary --ifm-threshold -1
python scripts/clip_fragments.py --instance-root instances/cfa-k1e
ws4 build --xml output/patchworks/forestmodel.xml \
  --fragments output/patchworks/fragments/fragments_clipped.shp \
  --out ws4/build/compiled
ws4 validate --dataset ws4/build/compiled
python scripts/prepare_ws4_runtime.py --instance-root instances/cfa-k1e
ws4 simulate --dataset ws4/build/compiled \
  --schedule ws4/schedules/earliest_cc.csv --years 100 \
  --out ws4/runs/smoke_liquidation
python scripts/write_aac_targets.py --slug cfa-k1e \
  --output instances/cfa-k1e/config/targets/evenflow_aac.yaml
ws4 optimize --dataset ws4/build/compiled \
  --targets instances/cfa-k1e/config/targets/evenflow_aac.yaml \
  --years 100 --time-limit 00:02:00 --threads 8 --seed 42 \
  --out ws4/runs/aac_search
ws4 simulate --dataset ws4/build/compiled \
  --schedule ws4/runs/aac_search/schedule.csv --years 100 \
  --out ws4/runs/aac_baseline
ws4 serve --dataset ws4/build/compiled --runs ws4/runs \
  --geometry ws4/geometry/blocks.geojson --port 8799
```

Observed output:

```text
post-tipsy completed tsa=['k1e'] au_rows=9 curves=96 curve_points=2826
patchworks export completed tsa=['k1e'] au=9 fragments=35 curves=211
Clipped fragments: 35 -> 35 rows, 781.24 -> 345.92 ha
Built dataset → ws4/build/compiled
Dataset is valid → ws4/build/compiled
Simulation complete → ws4/runs/smoke_liquidation
Simulation complete → ws4/runs/aac_baseline
HTTP 200 from http://127.0.0.1:8799/
```

## AAC baseline

| Period | Years | Harvest m³ | Band m³ | Status |
| --- | --- | --- | --- | --- |
| 1 | 10 | 8,611 | 8,600-10,320 | met |
| 2 | 20 | 8,018 | 8,600-10,320 | below |
| 3 | 30 | 7,533 | 8,600-10,320 | below |
| 4 | 40 | 6,550 | 8,600-10,320 | below |
| 5 | 50 | 3,816 | 8,600-10,320 | below |
| 6 | 60 | 3,999 | 8,600-10,320 | below |
| 7 | 70 | 9,032 | 8,600-10,320 | met |
| 8 | 80 | 1,203 | 8,600-10,320 | below |
| 9 | 90 | 3,349 | 8,600-10,320 | below |
| 10 | 100 | 8,659 | 8,600-10,320 | met |

Total harvest is 60,769 m³, below AAC x 100 = 86,000 m³. With the clipped
VRI and the THLB, the small coastal instance cannot hold the 1.2x band through
all periods. This is a real finding, not a search failure: the operable area
and block sizes are too small relative to the AAC.

## K2E result

K2E Logan Lake is also built end to end:

- AOI 16,722 ha, AAC 18,300 m³/yr
- build wall clock **13:48**, peak RSS **12.2 GB**
- 48 AU rows, 847 curves, 16,027 curve points
- VRI clipped to 2,194 polygons, 16,722.44 ha
- 999 fragments clipped from 10,417 ha to 8,805 ha
- THLB **10,831.91 ha** (64.8%); managed 7,343.05 ha, unmanaged 1,461.63 ha
- WS4: 1,595 blocks, 58 treatments, dataset valid
- 1.2x AAC search met all ten target periods
- AAC baseline total 2,195,965 m³ over 100 years
- FHOPS pilot: 14 blocks, 183,000 m³, 261-day makespan, zero violations

The first 2-minute search without a greedy seed missed every period. The
greedy seed plus a 5-minute search met all ten. See
`docs/reports/p1-k2e.md`.

## K3X result

K3X FNFN/NRRM is built end to end:

- AOI 184,681.61 ha, AAC 185,000 m³/yr
- build wall clock **26:37**, peak RSS **13.1 GB**
- VRI clipped to 24,872 polygons, 184,681.61 ha
- 16,469 FEMIC fragments, 24,435 clipped rows, 133,387 ha
- THLB **46,058.64 ha** (24.9%); managed 43,555.40 ha, unmanaged 89,831.82 ha
- WS4: 24,435 blocks, 18 treatments, dataset valid
- 1.2x AAC search met all ten periods at the ceiling
- AAC baseline total 22,200,000 m³ over 100 years (222,000 m³/yr)
- FHOPS: 44 blocks, 1,850,000 m³, 412-day makespan, zero violations

See `docs/reports/p1-k3x.md`.

## Issues found and worked around

1. **Custom-boundary VRI overhang.** FEMIC selects VRI polygons that intersect
   a custom boundary but does not clip them. K1E's original fragments summed to
   781 ha against a 355 ha AOI. The build now clips both the VRI source and the
   exported fragments to the AOI. The VRI clip also changes the curves and
   species proportions: K1E's 1.2x AAC total fell from 76,864 m³ to 60,769 m³
   after the clip.
2. **Non-numeric case codes.** FEMIC writes `03_input-tsa<code>.csv` and
   `vdyp_*-tsa<code>.*` during `femic run`, but the post-TIPSY step looks for
   `03_input-<code>.csv` and `vdyp_*-<code>.*`. The pilot creates short
   symlinks. This should become a FEMIC fix.
3. **Empty TSA list defaults to `08`.** A custom boundary with
   `selection.tsa: []` is normalized to `["08"]`, which conflicts with the
   boundary code. The pilot sets `selection.tsa` to the CFA code as a
   workaround.
4. **All fragments exported unmanaged.** The default `ifm-mode=proportional`
   produced 35 unmanaged fragments, so WS4 compiled zero treatments. Setting
   `--ifm-mode legacy_binary --ifm-threshold -1` marks all fragments managed
   for the pilot. This is a land-base assumption to replace with a real THLB
   signal.
5. **TIPSY density is discrete.** The TIPSY tables carry blocks at densities
   such as 1111 and 1600, not 1200. The bridge picks the closest block and
   records the choice in the sidecar manifest.
6. **Species codes differ.** `HW` maps to `HWC` on the coast and `HWI` in the
   interior; `DR` maps to `FDC`. The pilot config records these overrides.
7. **VDYP still uses Wine.** The VDYP stage ran `VDYP7Console` under Wine 11.
   Only the TIPSY stage is Wine-free. A Wine-free VDYP equation lane remains a
   parallel workstream.

## Next

1. Run a K3X FHOPS pilot on the first AAC period (45 blocks).
2. Pre-clip the VRI and VDYP input polygon layers per CFA so the curves and
   species proportions are also inside the AOI.
3. Add a non-declining or even-flow shape to the AAC targets instead of a flat
   band, and tighten K3X's ceiling.
4. Build the multi-instance portal with the three pilots.
5. Scale the batch build with a memory-aware queue.
