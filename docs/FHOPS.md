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
- completed blocks;
- makespan;
- average scheduled rate;
- configured rate;
- horizon;
- sequencing violations;
- solved-block map;
- model file downloads.

The period volume is `annual AAC × 10`, compressed into the FHOPS operating
horizon. It is not annual production and not a production operating plan.

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

## Ten-year seasonal plans

The three featured pilots have ten-year seasonal plans:

| Woodlot | Volume | Blocks | Makespan |
| --- | ---: | ---: | ---: |
| W0026 | 73,110 m³ | 4 | 9.87 years |
| W1548 | 40,000 m³ | 2 | 9.87 years |
| W2023 | 58,330 m³ | 10 | 9.90 years |

Each plan uses a 3,650-day horizon with a 180-day operating season per year.
It is a compressed tactical pilot, not a global ten-year MILP or a production
schedule.

Rebuild:

```bash
python scripts/build_fhops_tenyear.py --only wl-w0026 --iterations 800
python scripts/build_fhops_tenyear.py --only wl-w1548 --iterations 800
python scripts/build_fhops_tenyear.py --only wl-w2023 --iterations 800
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
three featured pilots also have ten-year seasonal plans, Pareto sweeps, and
Tree Lab cases.

## Caveats

- The studio compresses ten years of AAC volume into a short horizon.
- Machine movement is a straight-line marker between block centroids, not a road
  route.
- The theatre trees and choreography are explicitly illustrative.
- The 2D FHOPS and WS4 data remain authoritative.
