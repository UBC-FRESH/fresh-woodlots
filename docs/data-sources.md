# Data sources

All inputs are public. Every derived artifact records source, retrieval date,
query, and SHA256. Large raw inputs belong in DataLad or a shared cache, not
Git.

## Woodlot boundaries

| Field | Value |
| --- | --- |
| Name | Forest Tenure Managed Licence |
| Object | `WHSE_FOREST_TENURE.FTEN_MANAGED_LICENCE_POLY_SVW` |
| Endpoint | `https://maps.gov.bc.ca/arcgis/rest/services/whse/bcgw_pub_whse_forest_tenure/MapServer/8` |
| Filter | `LIFE_CYCLE_STATUS_CODE='ACTIVE' AND FOREST_FILE_ID LIKE 'W%'` |
| CRS | EPSG:3005 |
| Current count | 845 active W file IDs, 2,007 source polygons |
| Fetch | `scripts/fetch_woodlot_catalog.py` |

The layer carries Schedule A and Schedule B polygons. The catalog unions them
per file ID and reports the split.

## Allowable annual cut

| Field | Value |
| --- | --- |
| Name | Issued woodlot licence AAC report |
| File | `ftarpt_f000_file_status_register_mar2026rpt.xls` |
| Filter | `FILE_TYPE_CODE = A04` |
| Match | 800/845 active woodlots (47 pending) |
| Total | 1,298,031 m³/yr matched |
| Status | Parsed and merged into the catalog |

The tenure layer has geometry and status but no AAC. The AAC report supplies
`AAC_TOTAL` and `AREA_TOTAL`. `xlrd` is required for the legacy `.xls`.

## Inventory and land base

- **VRI Rank 1 2025** (`VEG_COMP_LYR_R1_POLY_2025.gdb`): inventory polygons,
  species, age, site index. Clipped per instance by `scripts/prepare_vri.py`.
- **VDYP7 input polygon/layer tables**: natural-stand yield curves.
- **TIPSY database tables**: managed-stand yield surfaces; raw tables are not
  redistributed.
- **Provincial Proxy THLB** (`provincial_pthlb`, layer `provincial_pthlb`):
  strategic managed/unmanaged split. The build prefers the
  `Woodlot - <file_id>` management unit and falls back to all overlapping THLB.
  `pthlb_fact` is a per-polygon contribution between 0 and 1, not a binary
  mask. `prepare_thlb.py` reports `sum(area × pthlb_fact)`, and
  `clip_fragments.py` computes each fragment's net managed area as
  `sum(fragment ∩ THLB polygon area × pthlb_fact)`. The fragment is split into
  managed/unmanaged records by that net area, while retaining the clipped
  geometry for the block map. The binary footprint-only split was replaced
  because it overstated managed area on partial-contribution polygons.
- **TSA boundaries and site productivity**: boundary and site-index context.

## Models and packages

| Component | Role | Licence |
| --- | --- | --- |
| FEMIC | Inventory, curves, XML, fragments | MIT |
| WS4 | Spatial estate model and web app | MIT |
| FHOPS | Harvesting operations planning | MIT |
| fresh-vdyp | VDYP7 bundle and runner | MIT |
| fresh-tipsy | TIPSY/FAN$IER tables and curves | MIT |

## Provenance rules

1. Every artifact records source name, object or file, URL, retrieval date,
   and SHA256.
2. No raw government bundle or large table is committed to Git.
3. A failed fetch or failed model run is recorded as a failure, never filled
   with a guessed value.
4. Every published number can be traced to a build manifest.
5. Every page carries a "not a statutory analysis" disclaimer.
