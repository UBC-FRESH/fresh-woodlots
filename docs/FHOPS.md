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

## Coverage

At the time this page was written, **323 built instances** had FHOPS pages and
studios/theatre data. The remaining built/in-flight instances get theirs in the
post-batch FHOPS pass.

## Caveats

- The studio compresses ten years of AAC volume into a short horizon.
- Machine movement is a straight-line marker between block centroids, not a road
  route.
- The theatre trees and choreography are explicitly illustrative.
- The 2D FHOPS and WS4 data remain authoritative.
