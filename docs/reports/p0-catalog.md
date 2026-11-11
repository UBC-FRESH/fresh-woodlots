# P0 report: public CFA catalog and build queue

Date: 2026-11-09
Status: P0.1-P0.7 complete; display-name curation remains open

## What landed

- `scripts/fetch_cfa_catalog.py` fetches the public BC Geographic Warehouse
  *Forest Tenure Managed Licence* layer through its ArcGIS REST endpoint.
- `src/fresh_cf/catalog.py` filters to active `K` forest file IDs, dissolves
  source polygons to one boundary per CFA, computes hectares and the
  Schedule A/B split, and writes the catalog, boundaries, manifest, and queue.
- `queue/cfa_build_queue.json` contains one pending entry per CFA with the
  six-step build pipeline.
- `tests/test_catalog.py` covers ID filtering, slugging, grouping, area sums,
  and deterministic ordering.

## Evidence

Command:

```bash
python scripts/fetch_cfa_catalog.py
```

Output:

```text
Retrieved 235 source objects at 2026-11-09T21:28:24+00:00
Catalog: 62 active CFAs, 2,032,471 ha, 235 source polygons
```

Artifacts:

| Artifact | Size | SHA256 |
| --- | --- | --- |
| `data/catalog/cfa_catalog.csv` | 15,400 B | `7ed4e3ec4dd6c0301c55d0db7c8afdf4a5cabbd0d23b06d797168ed40906626d` |
| `data/catalog/cfa_catalog.json` | 44,555 B | `580a13b362545bccdd2ac2630d8f6d8d3aba74e404cdefa36c9ebad0237a1179` |
| `data/boundaries/cfa_boundaries.gpkg` | 7,561,216 B | `60736de2f02fd422233f624a7f8e38c2d47d67f13e07356fd5cdb032a83a9eee` |
| `data/boundaries/cfa_boundaries_simplified.geojson` | 1,995,191 B | `c0d8c108c494eef22379755f12d04abb48a48e724341255e47f0b8e402968230` |

Gates:

```text
pytest: 4 passed
ruff check: All checks passed
```

## AAC addendum (2026-11-09)

The public issued-tenure AAC report was added to the catalog fetch:

- source: `ftarpt_f000_file_status_register_mar2026rpt.xls`
- filter: `FILE_TYPE_CODE = A28` (community forest agreement)
- match: **62/62 CFAs**
- total AAC: **2,187,599 m³/yr**

The catalog and queue now carry `aac_m3`, `aac_area_ha`, `aac_licensee`, and
`aac_district`. The AAC source URL, SHA256, row count, and match count are in
`data/catalog/source_manifest.json`.

## Findings

- The public layer returns **62 active CFA files**, not ~75. BCCFA and the
  province both quote 62; the extra count in the kickoff likely includes
  pending applications or expansions.
- The 62 CFAs cover **2,032,471 ha** across **235 source polygons**. This is
  consistent with the BCCFA average of about 31,119 ha per CFA.
- The smallest active CFA is Bamfield Huu-ay-aht at **355 ha**; the largest is
  FNFN/NRRM at **184,682 ha**.
- `ADMIN_DISTRICT_NAME` in this layer carries the natural resource *region*,
  not the district. The field name is misleading; the catalog keeps the value
  but the docs should call it a region until verified.
- Almost every CFA is Schedule B; Schedule A polygons are small add-ons. The
  catalog keeps the split for provenance but the model AOI is the union.
- Display names are currently the licensee names in uppercase. P0.6 needs a
  curated short name and community label.

## Open items

- P0.6: curate display names and short names against the BCCFA list.
- The biggest technical risk remains `fresh-vdyp`: version 0.1.0 still uses the
  Windows console for full yield tables. The P1 pilot records a time-boxed
  Wine exception and a fresh-tipsy bridge for the managed-curve stage.

## Next

Select the three P1 pilot CFAs and freeze their AOIs. Recommended:

- K1E Bamfield Huu-ay-aht (small, coast);
- K2E Logan Lake (medium, interior);
- K3X FNFN/NRRM (large, north).
