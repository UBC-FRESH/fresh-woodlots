# Provenance register

Date: 2026-11-10
Status: current for the 62-CFA batch

## Source register

| Source | Object / file | Use | Licence |
| --- | --- | --- | --- |
| Forest Tenure Managed Licence | `WHSE_FOREST_TENURE.FTEN_MANAGED_LICENCE_POLY_SVW` | CFA boundaries, file IDs, status | Open Government Licence – BC |
| Issued Community Forest Listings | `ftarpt_f000_file_status_register_mar2026rpt.xls` | AAC and AAC area | Open Government Licence – BC |
| VRI Rank 1 (2025) | `VEG_COMP_LYR_R1_POLY_2025.gdb` | inventory polygons, species, age, SI | Open Government Licence – BC |
| VDYP7 input polygon/layer | `VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2025.gdb` | natural curves | Open Government Licence – BC |
| Provincial Proxy THLB | `provincial_pthlb.gdb` | managed/unmanaged split | Open Government Licence – BC |
| TSA boundaries | `FADM_TSA.gdb` | boundary context | Open Government Licence – BC |
| Site productivity | `Site_Prod_BC.gdb`, `siteprod.tif` | site index | Open Government Licence – BC |
| TIPSY database | local `Database/` tables | managed curves | BC government; raw tables not redistributed |

## Artifact provenance

| Artifact | Location | Provenance |
| --- | --- | --- |
| Catalog + AAC | `data/catalog/cfa_catalog.csv`, `cfa_catalog.json` | source URL, query, retrieved_at, SHA256 in `source_manifest.json` |
| CFA boundaries | `data/boundaries/cfa_boundaries.gpkg` | source layer and SHA256 |
| Build queue | `queue/cfa_build_queue.json` | status, build time, peak RSS, bundle status, FHOPS summary |
| Per-instance VRI | `instances/<slug>/data/external/` | clipped VRI + `vri.summary.json` |
| Per-instance THLB | `instances/<slug>/data/source/thlb/` | `thlb.summary.json` |
| Per-instance curves | `data/model_input_bundle/` | FEMIC run manifest |
| Per-instance WS4 | `ws4/build/compiled/manifest.json` | source hashes |
| Per-instance AAC | `ws4/runs/aac_baseline/` | schedule, targets, report |
| Per-instance FHOPS | `fhops/scenario.yaml`, `fhops/summary.json` | rate, horizon, production, makespan |

## Batch result

- 62 active CFAs
- 62 built
- 62 full bundles
- 62 AAC baselines
- 62 FHOPS pilots
- 0 failed

## Redistribution rules

- Raw TIPSY tables and BC government model bundles are not committed or
  redistributed.
- Large public inputs live in the DataLad mirror or local downloads, not Git.
- Derived model outputs are published with source citations and the
  not-a-statutory-analysis disclaimer.

## Reproduce

```bash
python scripts/fetch_cfa_catalog.py
python scripts/fetch_thlb.py
python scripts/prepare_pilot.py --pilots config/pilots_batch.yaml
python scripts/batch_build.py --jobs 8
python scripts/batch_fhops.py --jobs 8
./run_portal.sh
```
