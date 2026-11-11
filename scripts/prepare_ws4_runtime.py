#!/usr/bin/env python3
"""Prepare the WS4 runtime inputs for one woodlot instance.

Writes:

- ``ws4/schedules/earliest_cc.csv``: harvest each block at the first offset
  when its clearcut treatment is operable.
- ``ws4/geometry/blocks.geojson``: full-detail block polygons in WGS84.
- ``ws4/geometry/blocks_overview.geojson``: simplified block polygons for
  low-zoom map tiles.

The schedule is a smoke baseline, not an AAC-balanced plan.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd


def build_schedule(compiled: Path) -> pd.DataFrame:
    """Return one clearcut entry per block at its earliest operable offset."""

    blocks = pd.read_parquet(compiled / "blocks.parquet")
    fragments = pd.read_parquet(compiled / "fragments.parquet")
    treatments = pd.read_parquet(compiled / "treatments.parquet")
    clearcuts = treatments[treatments["treatment"] == "CC"]
    if clearcuts.empty:
        raise ValueError("Compiled dataset has no CC treatment")
    managed_tracks = {int(track_id) for track_id in clearcuts["track_id"]}
    begin = {
        int(row.track_id): int(row.begin) for row in clearcuts.itertuples()
    }
    oldest_age = fragments.groupby("block_id")["age"].max()
    rows: list[dict[str, object]] = []
    for block in blocks.itertuples():
        block_id = int(block.block_id)
        track_id = int(block.track_id)
        if track_id not in managed_tracks:
            continue
        age = int(oldest_age.loc[block_id])
        offset = max(0, begin.get(track_id, 0) - age)
        rows.append({"block_id": block_id, "treatment": "CC", "offset": offset})
    return pd.DataFrame(rows).sort_values(["offset", "block_id"]).reset_index(drop=True)


def build_geometry(instance_root: Path) -> gpd.GeoDataFrame:
    """Dissolve fragments to full-detail block polygons for the WS4 map."""

    fragments = gpd.read_file(
        instance_root / "output" / "patchworks" / "fragments" / "fragments_clipped.shp"
    )
    blocks = fragments.dissolve(by="BLOCK").reset_index()
    blocks["block_id"] = blocks["BLOCK"].astype(int)
    blocks["area_ha"] = blocks.geometry.area / 10_000.0
    return blocks[["block_id", "area_ha", "geometry"]].copy()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-root", type=Path, required=True)
    parser.add_argument(
        "--simplify-m",
        type=float,
        default=0.0,
        help="Detail simplification tolerance in metres (default: 0, full detail)",
    )
    parser.add_argument(
        "--overview-m",
        type=float,
        default=10.0,
        help="Low-zoom overview simplification in metres (default: 10)",
    )
    args = parser.parse_args(argv)

    instance_root = args.instance_root.resolve()
    compiled = instance_root / "ws4" / "build" / "compiled"
    schedule = build_schedule(compiled)
    schedule_path = instance_root / "ws4" / "schedules" / "earliest_cc.csv"
    schedule_path.parent.mkdir(parents=True, exist_ok=True)
    schedule.to_csv(schedule_path, index=False)

    geometry = build_geometry(instance_root)
    geometry_dir = instance_root / "ws4" / "geometry"
    geometry_dir.mkdir(parents=True, exist_ok=True)

    detail = geometry.copy()
    if args.simplify_m > 0:
        detail["geometry"] = detail.geometry.simplify(
            args.simplify_m, preserve_topology=True
        )
    detail_path = geometry_dir / "blocks.geojson"
    if detail_path.exists():
        detail_path.unlink()
    detail.to_crs("EPSG:4326").to_file(detail_path, driver="GeoJSON")

    overview = geometry.copy()
    overview["geometry"] = overview.geometry.simplify(
        args.overview_m, preserve_topology=True
    )
    overview_path = geometry_dir / "blocks_overview.geojson"
    if overview_path.exists():
        overview_path.unlink()
    overview.to_crs("EPSG:4326").to_file(overview_path, driver="GeoJSON")

    print(f"Wrote {len(schedule)} schedule rows to {schedule_path}")
    print(f"Wrote {len(geometry)} block polygons to {detail_path}")
    print(f"Wrote {len(overview)} overview polygons to {overview_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
