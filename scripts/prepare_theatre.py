#!/usr/bin/env python3
"""Build synthetic tree-scale theatre scenes from FHOPS scheduled blocks.

The tree positions are a deterministic visual sample inside each real block
polygon. They are not a forest inventory and the machine choreography is
illustrative, not a FHOPS solve.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "queue" / "woodlot_build_queue.json"
SPECIES = ("Fd", "Cw", "Hw", "Pl")


def _local_ring(polygon, centroid) -> list[list[float]]:
    ring = list(polygon.exterior.coords)
    return [
        [round(float(x - centroid.x), 2), round(float(y - centroid.y), 2)]
        for x, y in ring
    ]


def _choose_blocks(frame: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    eligible = frame[(frame["area_ha"] >= 1.0) & (frame["area_ha"] <= 30.0)].copy()
    if eligible.empty:
        eligible = frame.copy()
    return eligible.sort_values("area_ha").head(3)


def _trees(polygon, seed: int) -> list[dict[str, object]]:
    area_ha = polygon.area / 10_000.0
    target = max(120, min(700, int(area_ha * 55)))
    minx, miny, maxx, maxy = polygon.bounds
    spacing = max(2.0, math.sqrt(polygon.area / target) * 0.92)
    rng = random.Random(seed)
    trees: list[dict[str, object]] = []
    steps = int(math.ceil(max(maxx - minx, maxy - miny) / spacing)) + 1
    centers: list[tuple[float, float]] = []
    for ix in range(steps):
        for iy in range(steps):
            x = minx + (ix + 0.5) * spacing + rng.uniform(-0.35, 0.35) * spacing
            y = miny + (iy + 0.5) * spacing + rng.uniform(-0.35, 0.35) * spacing
            if polygon.contains(Point(x, y)):
                centers.append((x, y))
    rng.shuffle(centers)
    for x, y in centers[:target]:
        height = round(rng.uniform(16.0, 28.0), 1)
        crown = round(rng.uniform(1.8, 3.2), 2)
        trees.append(
            {
                "x": round(x, 2),
                "y": round(y, 2),
                "h": height,
                "c": crown,
                "sp": rng.choice(SPECIES),
            }
        )
    return trees


def build_one(root: Path) -> int:
    source = root / "fhops" / "out" / "scheduled_blocks.geojson"
    if not source.is_file():
        return 0
    frame = gpd.read_file(source).to_crs(3005)
    chosen = _choose_blocks(frame)
    if chosen.empty:
        return 0
    blocks: list[dict[str, object]] = []
    for index, row in enumerate(chosen.itertuples(index=False)):
        geometry = row.geometry
        if geometry.geom_type == "MultiPolygon":
            geometry = max(geometry.geoms, key=lambda part: part.area)
        if geometry.geom_type != "Polygon" or geometry.is_empty:
            continue
        centroid = geometry.centroid
        trees = _trees(geometry, seed=1000 + index)
        landing = [round(centroid.x, 2), round(centroid.y, 2)]
        blocks.append(
            {
                "label": str(row.label),
                "area_ha": round(float(row.area_ha), 2),
                "volume_m3": round(float(row.volume_m3 or 0), 1),
                "rings": [_local_ring(geometry, centroid)],
                "trees": [
                    {
                        "x": round(float(tree["x"]) - centroid.x, 2),
                        "z": round(float(tree["y"]) - centroid.y, 2),
                        "h": tree["h"],
                        "c": tree["c"],
                        "sp": tree["sp"],
                    }
                    for tree in trees
                ],
                "landing": [
                    round(landing[0] - centroid.x, 2),
                    round(landing[1] - centroid.y, 2),
                ],
            }
        )
    if not blocks:
        return 0
    output = root / "fhops" / "out" / "theatre.json"
    output.write_text(
        json.dumps(
            {"schema_version": 1, "slug": root.name, "blocks": blocks},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return len(blocks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=QUEUE_PATH)
    parser.add_argument("--only", action="append", default=None)
    args = parser.parse_args(argv)
    payload = json.loads(args.queue.read_text(encoding="utf-8"))
    wanted = set(args.only) if args.only else None
    total = 0
    for entry in payload.get("instances", []):
        if entry.get("status") not in ("built", "pilot_built"):
            continue
        slug = str(entry["slug"])
        if wanted is not None and slug not in wanted:
            continue
        count = build_one(REPO_ROOT / "instances" / slug)
        if count:
            print(f"{slug}: {count} theatre blocks")
            total += count
    print(f"wrote {total} theatre blocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
