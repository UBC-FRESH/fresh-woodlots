# FHOPS operational pilots

Every built woodlot with a solved FHOPS pilot has a portal page:

```text
/fhops/<slug>
/fhops/<slug>/studio
/fhops/<slug>/theatre
```

## FHOPS summary page

Shows:

- annual AAC;
- **10-year period volume**;
- completed blocks / blocks treated;
- makespan;
- average scheduled rate or annual harvested/processed/staged;
- configured rate;
- horizon;
- sequencing violations;
- solved-block map;
- model file downloads.

Non-featured woodlots remain first-period, rate-fixed pilots. The three
featured pilots now use the tactical–operational MILP and annual operational
seasons described below.

## 3D harvest studio

`/fhops/<slug>/studio` is a full-screen MapLibre view with:

- extruded scheduled blocks;
- day-by-day harvest states;
- machine markers and planned tracks;
- follow-camera, height exaggeration, speed, play/pause, and orbit controls.

## Tree-scale theatre

`/fhops/<slug>/theatre` is a Three.js scene with:

- three real block polygons per instance;
- a deterministic synthetic tree layout inside each block;
- felling, skidding, and processing animation;
- block selector and playback controls.

The tree layout is illustrative, not an inventory, and the machine choreography
is not a FHOPS solve.

## Selected-area audit

The first-period pilots compress ten years of AAC into a short horizon. A
population audit compares the period volume with the selected scheduled block
area:

- **71** instances are above 1,000 m³ per selected hectare;
- **5** are above 5,000 m³/ha;
- no instance has a missing selected area.

Those cases are labeled **⚠ area check** in the portal. The label is a
screening prompt, not a yield result. The featured tactical plans now use all
compiled WS4 blocks and generally sit near 90–120 m³/ha for the ten-year
volume.

See [`FHOPS-AREA-AUDIT.md`](FHOPS-AREA-AUDIT.md) for the full table.

## Tree Lab

`/treelab/` mounts the experimental FHOPS Tree Lab sandbox. The three featured
pilots have precomputed cases:

- `w0026-61` — W0026 Chinook Woodlots
- `w1548-24` — W1548 Fibre Farms
- `w2023-94` — W2023 Boomer Enterprises

The FHOPS page links directly to the matching run. See
[TREELAB.md](TREELAB.md) for the case layout, rebuild commands, and caveats.

## Generated data

`scripts/prepare_fhops_maps.py` writes:

```text
fhops/out/scheduled_blocks.geojson
fhops/out/timeline.json
```

`scripts/prepare_theatre.py` writes:

```text
fhops/out/theatre.json
```

`scripts/batch_fhops.py` runs both builders after a FHOPS batch solve.

## Ten-year tactical–operational plans

The three featured pilots now use the formal FHOPS tactical–operational MILP:

| Woodlot | Annual AAC | 10-year volume | Blocks treated | Horizon |
| --- | ---: | ---: | ---: | ---: |
| W0026 | 7,311 m³ | 73,110 m³ | 4 | 10 years |
| W1548 | 4,000 m³ | 40,000 m³ | 2 | 10 years |
| W2023 | 5,833 m³ | 58,330 m³ | 10 | 10 years |

The tactical layer selects block areas and annual product volumes from the
real selected WS4 blocks. Each year is then compiled into an independent
180-day operational FHOPS season, which supplies the machine-day schedule,
block map, and 3D replay. Product yields use a transparent 70/30
sawlog/pulp split.

Rebuild:

```bash
python scripts/build_tactical_plan.py \
  --only wl-w0026 --only wl-w1548 --only wl-w2023
python scripts/build_fhops_tactical_ops.py \
  --only wl-w0026 --only wl-w1548 --only wl-w2023
python scripts/prepare_fhops_maps.py \
  --only wl-w0026 --only wl-w1548 --only wl-w2023
python scripts/prepare_theatre.py \
  --only wl-w0026 --only wl-w1548 --only wl-w2023
```

## Pareto sweeps

The featured pilots also have small AAC-band Pareto portfolios:

```text
instances/<slug>/ws4/runs/pareto_sweep/portfolio.json
```

The sweeps use 0.85×, 1.0×, and 1.15× AAC. Current fronts:

| Woodlot | Front members |
| --- | ---: |
| W0026 | 3 |
| W1548 | 2 |
| W2023 | 1 |

The WS4 **Pareto** tab loads the portfolio and shows the front.

```bash
python scripts/build_pareto_sweep.py --only wl-w0026 \
  --factors 0.85,1.00,1.15 --seeds 1 --iterations 30
```

## Coverage

All **798** built instances have FHOPS summaries, maps, and theatre data. The
three featured pilots also have ten-year tactical–operational plans, Pareto
sweeps, and Tree Lab cases. W1674 and W0007 have additional tactical
validation plans using all compiled WS4 blocks; see
[TACTICAL-VALIDATION.md](TACTICAL-VALIDATION.md).

## Caveats

- The non-featured studio pilots compress AAC volume into a short horizon.
- The featured studios show the tactical MILP plus ten annual operational
  seasons; the operational layer is not a production schedule.
- Machine movement is a straight-line marker between block centroids, not a road
  route.
- The theatre trees and choreography are explicitly illustrative.
- The 2D FHOPS and WS4 data remain authoritative.
