# Woodlots BC Planning Portal

A free, public-data planning portal for BC woodlot licences, built for
Woodlots BC (the BC Woodlot Owners Association). It follows the same model as
the BCCFA community forest portal:

- one WS4 strategic planning instance per woodlot licence;
- one first-period FHOPS operational pilot per built woodlot;
- a read-only public catalogue and map of every active licence;
- a demo-ready scenario editor for the featured pilots.

The source of truth is the public BC data:

| Dataset | Use |
| --- | --- |
| Forest Tenure Managed Licence (`FTEN_MANAGED_LICENCE_POLY_SVW`) | Woodlot boundaries, file IDs, Schedule A/B |
| Issued woodlot AAC report (`A04`) | Public AAC and AAC area |
| Vegetation Resources Inventory Rank 1 (2025) | Inventory polygons, species, age, site index |
| Provincial Proxy THLB | Managed / unmanaged land-base split |
| VDYP7 input tables | Natural-stand yield curves |
| TIPSY database tables | Managed-stand yield surfaces |
| TSA boundaries / site productivity | Boundary and site-index context |

## Current state

- **845** active woodlot licences catalogued.
- **798** have a public AAC value and are buildable.
- **798 / 798** built, with FHOPS summaries, maps, timelines, theatre data, and
  W4W v1 calibrations.
- **47** are catalogued with **AAC pending** (not in the March 2026 public
  report yet).
- Release-candidate QA: **0 failures** across six portal routes and five
  required artifacts per built instance.
- Calibration audit: **157 / 798** v1 factors flagged as **method check**
  (outside 0.4–2.0); v1 remains the population default, with v2 selected per
  documented partial-cut plan.
- The three featured pilots are:
  - W0026 Chinook Woodlots (Campbell River)
  - W2023 Boomer Enterprises (Okanagan)
  - W1548 Fibre Farms (Prince George)
- The portal runs on **port 8795**; the BCCFA portal remains on 8796 and
  Nemora remains on 8799.

## Tech docs

Sphinx documentation is published at:

<https://ubc-fresh.github.io/fresh-woodlots/>

Source is in `docs/`; the GitHub Actions workflow at
`.github/workflows/docs.yml` builds and deploys it with GitHub Pages.

## FHOPS pages

Every built woodlot with a solved FHOPS pilot has a `/fhops/<slug>` page,
a 3D harvest studio at `/fhops/<slug>/studio`, and a tree-scale theatre at
`/fhops/<slug>/theatre`.

The three featured pilots also have Tree Lab cases at `/treelab/`:

| Woodlot | Case | Direct link |
| --- | --- | --- |
| W0026 Chinook Woodlots | `w0026-61` | `/treelab/?case=w0026-61&run=demo-1` |
| W1548 Fibre Farms | `w1548-24` | `/treelab/?case=w1548-24&run=demo-1` |
| W2023 Boomer Enterprises | `w2023-94` | `/treelab/?case=w2023-94&run=demo-1` |

The tree lists are synthetic samples inside real FHOPS block polygons; the
machine choreography is illustrative. See `docs/TREELAB.md`.

## Document library

A local, searchable library of the BC woodlot documents is in
`data/library/woodlot/` (59 records, extracted text, SHA256 manifest):

```bash
python scripts/search_doc_library.py --query "allowable annual cut"
```

## Woodlot for Windows under Wine

Woodlot for Windows 4.4 is installed in `data/wine/woodlot` and runs under
Wine 11 + Wine Mono 11.3.0:

```bash
DISPLAY=:99 scripts/run_woodlot_wine.sh
```

See `docs/W4W-WINE.md` for install and caveats.

## Quick start

```bash
python scripts/fetch_woodlot_catalog.py
python scripts/prepare_pilot.py --pilots config/pilots.yaml
bash scripts/build_instance.sh wl-w0026
python scripts/prepare_demo.py --only wl-w0026
PORT=8795 ./run_portal.sh
```

For the full batch:

```bash
python scripts/prepare_pilot.py --pilots config/all_woodlots.yaml
python scripts/batch_build.py --jobs 12 --per-job-gb 8 --reserve-gb 32 \
  --aac-search-time 00:00:30
python scripts/batch_fhops.py --jobs 8
python scripts/prepare_demo.py
```

## Portal

- Landing page: all 845 licences, featured pilots first, search, province map.
- Model page: WS4 map, AAC baseline, Plan tab scenarios
  (baseline / high / conservative), target matrix, and solve controls.
- Sources & methods: `/about`; Terms: `/terms`; Privacy: `/privacy`.
- Health: `/health` reports `instances`, `ready`, `buildable`, and
  `pending_aac`.

## Deployment

The systemd unit is `deploy/freshwl-portal.container.service`, installed as
`freshwl-portal.service` on port 8795. It uses the newer WS4 UI from
`/srv/shared-data/gep/ws4/ws4-public-demo` and runs in demo mode:

```text
PUBLIC_READ_ONLY=0
DEMO_MODE=1
```

For a public read-only deployment, set `PUBLIC_READ_ONLY=1` and
`DEMO_MODE=0`, and re-enable a read-only bind for the instance tree.

## Caveats

- The Proxy THLB is a strategic estimate, not the statutory TSR THLB.
- The THLB netdown uses `pthlb_fact` partial contributions: the WS4 managed
  area is factor-weighted, not a binary footprint mask. This can reduce the
  managed area substantially on partial-contribution polygons.
- Where TIPSY lacks a BC species code, the build records a surrogate
  (for example MB→AT, BL→AT, SE→SW, PY→PLI, H→HWI).
- VDYP7 still runs the Windows console under Wine; the managed-curve stage
  uses `fresh-tipsy` without Wine.
- FHOPS plans are first-period, ground-based, rate-fixed pilots. They do not
  model roads, terrain, landing geometry, or real costs.
- This is not a statutory timber supply analysis. Use professional judgment
  and the cited public sources.
