#!/usr/bin/env python3
"""Build lightweight FHOPS scheduled-block GeoJSON for the portal map.

The FHOPS solution uses block labels such as ``K1E-11``. WS4 uses integer
block IDs, so the numeric suffix is the join key. The output is intentionally
small: only blocks that appear in the solved first-period plan.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "queue" / "woodlot_build_queue.json"


def _numeric_block(label: object) -> int | None:
    text = str(label)
    suffix = text.rsplit("-", 1)[-1]
    try:
        return int(float(suffix))
    except (TypeError, ValueError):
        return None


def build_one(root: Path) -> int:
    solution_path = root / "fhops" / "out" / "heur_solution.csv"
    geometry_path = root / "ws4" / "geometry" / "blocks.geojson"
    if not solution_path.is_file() or not geometry_path.is_file():
        return 0
    solution = pd.read_csv(solution_path)
    if "block_id" not in solution.columns:
        return 0
    if "assigned" in solution.columns:
        solution = solution[solution["assigned"].astype(bool)]
    if solution.empty:
        return 0
    solution = solution.copy()
    solution["block_num"] = solution["block_id"].map(_numeric_block)
    solution = solution[solution["block_num"].notna()]
    if solution.empty:
        return 0

    grouped = (
        solution.groupby("block_num")
        .agg(
            machines=(
                "machine_id",
                lambda values: ",".join(sorted({str(v) for v in values})),
            ),
            first_day=("day", "min"),
            last_day=("day", "max"),
            assignments=("block_id", "size"),
        )
        .reset_index()
    )
    wanted = set(grouped["block_num"].astype(int))
    blocks = gpd.read_file(geometry_path)
    blocks = blocks[blocks["block_id"].astype(int).isin(wanted)].copy()
    if blocks.empty:
        return 0
    merged = blocks.merge(grouped, left_on="block_id", right_on="block_num", how="left")
    merged["label"] = merged["block_id"].map(
        dict(
            zip(
                solution["block_num"].astype(int),
                solution["block_id"],
                strict=False,
            )
        )
    )
    merged = merged[
        [
            "block_id",
            "label",
            "area_ha",
            "machines",
            "first_day",
            "last_day",
            "assignments",
            "geometry",
        ]
    ].to_crs("EPSG:4326")
    volume_path = root / "fhops" / "data" / "blocks.csv"
    volume = {}
    if volume_path.is_file():
        frame = pd.read_csv(volume_path)
        if {"id", "work_required"}.issubset(frame.columns):
            volume = {
                str(row.id): float(row.work_required)
                for row in frame.itertuples(index=False)
            }
    merged["volume_m3"] = merged["label"].map(volume)
    merged = merged.to_crs("EPSG:4326")
    centroids = merged.geometry.to_crs(3005).centroid.to_crs(4326)
    merged["centroid_lon"] = centroids.x
    merged["centroid_lat"] = centroids.y
    output = root / "fhops" / "out" / "scheduled_blocks.geojson"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    merged.to_file(output, driver="GeoJSON")

    summary_path = root / "fhops" / "summary.json"
    summary = {}
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    events = (
        solution[["day", "machine_id", "block_id"]]
        .drop_duplicates()
        .sort_values(["day", "machine_id", "block_id"])
    )
    timeline = {
        "schema_version": 1,
        "horizon_days": summary.get("horizon_days"),
        "makespan_day": summary.get("makespan_day"),
        "events": [
            {
                "day": int(row.day),
                "machine": str(row.machine_id),
                "block": str(row.block_id),
            }
            for row in events.itertuples(index=False)
        ],
    }
    timeline_path = root / "fhops" / "out" / "timeline.json"
    timeline_path.write_text(
        json.dumps(timeline, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return len(merged)


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
            print(f"{slug}: {count} scheduled blocks")
            total += count
    print(f"wrote {total} scheduled block features")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
