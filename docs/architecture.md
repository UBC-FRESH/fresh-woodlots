# Architecture

## Repository layout

```text
fresh-woodlots/
  instances/              per-licence workspaces (large, gitignored)
  queue/                  build queue and statuses
  scripts/                catalog, prep, build, repair, FHOPS, library
  portal/                 multi-instance FastAPI portal
  src/fresh_wl/           catalog transform
  data/library/woodlot/   local searchable document library
  docs/                   Sphinx source and operational notes
```

## Data flow

```text
FTEN managed licence  ──> catalog + dissolved boundaries
issued AAC report A04 ──> AAC and AAC area
VRI 2025              ──> per-instance clip
Proxy THLB            ──> pthlb_fact-weighted managed area
VDYP / TIPSY via FEMIC ─> yield curves and Patchworks bundle
WS4                    ─> compiled dataset, schedule, AAC runs
FHOPS                  ─> first-period operational pilot
portal                 ─> read-only or demo UI
```

## THLB netdown

`prepare_thlb.py` computes the reported THLB as:

```text
thlb_ha = Σ(polygon_area_ha × pthlb_fact)
```

`clip_fragments.py` computes each fragment's net managed area as:

```text
managed_ha = Σ(area(fragment ∩ THLB polygon) × pthlb_fact)
unmanaged_ha = fragment_area_ha − managed_ha
```

The fragment geometry is retained for the block map, while `AREA_HA` is the
factor-weighted area used by WS4. This replaced an earlier binary footprint
mask that overstated managed area on partial-contribution polygons.

## Portal

The portal mounts WS4 sub-applications under `/instance/<slug>/` lazily. A
single uvicorn worker serves the landing page, `/about`, `/terms`, `/privacy`,
the GeoJSON boundaries, and the WS4 apps. The BCCFA portal remains on **8796**;
the woodlot portal uses **8795**.

## Batch processing

- `scripts/batch_build.py` builds pending queue entries with a memory-aware
  process pool.
- `scripts/repair_built.py` rebuilds the WS4 side of built entries after a
  pipeline change.
- `scripts/batch_fhops.py` generates and solves operational pilots.
- `scripts/sync_queue.py` reconciles queue statuses with artefacts on disk.
