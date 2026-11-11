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

## Ten-year seasonal plan

W0026 has a ten-year seasonal plan:

- horizon: 3,650 days;
- operating season: 180 days/year;
- solved volume: 73,110 m³ (ten years of AAC);
- completed blocks: 4;
- makespan: 9.87 years;
- the original compressed 450-day plan is backed up as
  `fhops_compressed_450d`.

Rebuild:

```bash
python scripts/build_fhops_tenyear.py --only wl-w0026 --iterations 800
```

## Pareto sweep

W0026 also has a small AAC-band Pareto portfolio:

```text
ws4/runs/pareto_sweep/portfolio.json
```

Three target levels (0.85×, 1.0×, 1.15× AAC) produce three front members. The
WS4 **Pareto** tab loads the portfolio and shows the front.

```bash
python scripts/build_pareto_sweep.py --only wl-w0026 \
  --factors 0.85,1.00,1.15 --seeds 1 --iterations 30
```

## Coverage

At the time this page was written, **323 built instances** had FHOPS pages and
studios/theatre data. The remaining built/in-flight instances get theirs in the
post-batch FHOPS pass. W0026 has the ten-year and Pareto demo surfaces; W1548
and W2023 can be added the same way after their FHOPS summaries exist.

## Caveats

- The studio compresses ten years of AAC volume into a short horizon.
- Machine movement is a straight-line marker between block centroids, not a road
  route.
- The theatre trees and choreography are explicitly illustrative.
- The 2D FHOPS and WS4 data remain authoritative.
