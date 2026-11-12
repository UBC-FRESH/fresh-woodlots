#!/usr/bin/env python3
"""Create a Tree Lab case from a woodlot FHOPS block and run the tree system.

The tree list is a synthetic visual sample placed inside the real FHOPS block
polygon. The machine choreography is illustrative; this is a demo, not an
operational plan.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_ROOT = REPO_ROOT / "treelab_cases"
RUN_ROOT = REPO_ROOT / "treelab_runs"
DEFAULT_SLUG = "wl-w0026"
DEFAULT_BLOCK = "W0026-61"
FHops_SUPPORT = Path(
    os.environ.get(
        "FHOPS_GROUND_SUPPORT",
        "/srv/shared-data/gep/ws4/fhops-ground-support",
    )
)
_support_paths = [FHops_SUPPORT, FHops_SUPPORT / "src"]
for _path in _support_paths:
    if _path.is_dir() and str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
# The Tree Lab runner shells out to ``python -m fhops.cli.main``; make sure the
# child process sees the same FHOPS support checkout.
_existing_pythonpath = os.environ.get("PYTHONPATH")
os.environ["PYTHONPATH"] = os.pathsep.join(
    [str(path) for path in _support_paths]
    + ([_existing_pythonpath] if _existing_pythonpath else [])
)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", default=DEFAULT_SLUG)
    parser.add_argument("--block", default=DEFAULT_BLOCK)
    parser.add_argument("--case-id", default=None)
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Create the case but do not run the tree system.",
    )
    args = parser.parse_args()
    slug = args.slug
    block_label = args.block
    instance = REPO_ROOT / "instances" / slug
    theatre_path = instance / "fhops" / "out" / "theatre.json"
    theatre = json.loads(theatre_path.read_text(encoding="utf-8"))
    block = next(
        item for item in theatre["blocks"] if item["label"] == block_label
    )
    geometry = gpd.read_file(
        instance / "fhops" / "out" / "scheduled_blocks.geojson"
    ).to_crs(3005)
    row = geometry[geometry["label"] == block_label].iloc[0]
    centroid = row.geometry.centroid
    centre = gpd.GeoSeries([centroid], crs=3005).to_crs(4326).iloc[0]
    centre_wgs84 = [round(float(centre.y), 6), round(float(centre.x), 6)]
    case_id = args.case_id or block_label.lower().replace("_", "-")
    case_root = CASE_ROOT / case_id
    if case_root.exists():
        shutil.rmtree(case_root)
    case_root.mkdir(parents=True)

    inventory_dir = case_root / "tree_inventory"
    inventory_dir.mkdir()
    rows = []
    for index, tree in enumerate(block["trees"], start=1):
        height = float(tree["h"])
        rows.append(
            {
                "tree_id": f"T{index:05d}",
                "block_id": block_label,
                "x_m": round(float(tree["x"]) + centroid.x, 3),
                "y_m": round(float(tree["z"]) + centroid.y, 3),
                "elevation_m": 0.0,
                "species_code": str(tree["sp"]),
                "dbh_cm": round(max(12.0, height * 1.55), 1),
                "height_m": height,
                "crown_radius_m": float(tree["c"]),
                "status": "live",
                "confidence": 0.85,
                "source_id": f"synthetic-{case_id}",
                "source_tile_id": "T01",
                "merchantable_height_m": round(height * 0.72, 2),
                "defect": "",
                "grade_hint": "",
            }
        )
    inventory = inventory_dir / "tree_inventory.csv"
    pd.DataFrame(rows).to_csv(inventory, index=False)
    metadata = inventory_dir / "tree_inventory.meta.json"
    metadata.write_text(
        json.dumps(
            {
                "schema_version": "fhops.tree.inventory.v1",
                "inventory_id": f"{case_id}-synthetic",
                "generated_utc": datetime.now(UTC).isoformat(),
                "source_id": f"synthetic-{case_id}",
                "producer": "Woodlots BC demo tree-scale sample",
                "method": "Synthetic visual tree layout from the FHOPS block geometry.",
                "crs": "EPSG:3005",
                "units": {
                    "x_y": "m",
                    "elevation": "m",
                    "dbh": "cm",
                    "height": "m",
                    "crown_radius": "m",
                },
                "review_status": "not_reviewed",
                "block_ids": [block_label],
                "tree_count": len(rows),
                "caveats": [
                    "Synthetic tree list; not a surveyed stand or ITD/ITC product.",
                    "Machine choreography is illustrative, not a production plan.",
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    scenario_dir = case_root / "scenario"
    source_scenario = instance / "fhops_rolling_year"
    if not source_scenario.is_dir():
        source_scenario = instance / "fhops"
    shutil.copytree(source_scenario / "data", scenario_dir / "data")
    shutil.copy2(source_scenario / "scenario.yaml", scenario_dir / "scenario.yaml")
    blocks_path = scenario_dir / "data" / "blocks.csv"
    blocks = pd.read_csv(blocks_path)
    for column in ("avg_stem_size_m3", "volume_per_ha_m3", "stem_density_per_ha"):
        if column not in blocks.columns:
            blocks[column] = 0.0
    blocks.to_csv(blocks_path, index=False)
    shutil.copy2(
        FHops_SUPPORT
        / "sandbox"
        / "cases"
        / "afrf-gavin"
        / "scenario"
        / "data"
        / "harvest_systems.yaml",
        scenario_dir / "data" / "harvest_systems.yaml",
    )

    manifest = {
        "schema_version": "fhops.tree_lab.case.v1",
        "case_id": case_id,
        "label": f"{block_label} — tree-scale machine theatre",
        "block_id": block_label,
        "landing_id": "L1",
        "scenario": "scenario/scenario.yaml",
        "inventory": "tree_inventory/tree_inventory.csv",
        "metadata": "tree_inventory/tree_inventory.meta.json",
        "system_args": {
            "feller": "H1",
            "skidders": ["H2"],
            "processors": ["H3"],
            "loader": "H4",
            "bunch_volume_m3": 8.0,
            "rate_model": "calibrated",
            "shift_days": 5,
            "shifts_per_day": 1,
            "hours_per_shift": 10,
            "truck_capacity_m3": 30.0,
            "truck_count": 2,
            "truck_cycle_s": 3600.0,
            "landing_capacity_m3": 160.0,
            "skidder_capacity_m3": 40.0,
        },
        "terrain": {"dem": None, "road": None},
        "stand": {
            "area_ha": float(block["area_ha"]),
            "tree_count": len(rows),
            "centre_wgs84": centre_wgs84,
            "crs": "EPSG:3005",
        },
        "provenance": {
            "tree_list": "synthetic visual sample",
            "stand_footprint": "real FHOPS block polygon",
            "machine_choreography": "illustrative",
            "review_status": "not_reviewed",
        },
        "caveats": [
            "Synthetic tree list inside a real FHOPS block polygon.",
            "Tree-scale machine choreography is illustrative.",
            "Not an operational, financial, or regulatory plan.",
            "No ALS/LiDAR terrain or step map is included.",
        ],
        "harvest": {
            "type": "clear_cut",
            "marking_rule": "all",
            "target_basal_area_fraction": 1.0,
        },
    }
    (case_root / "case.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote case {case_root}")

    if args.skip_run:
        print("skipped tree-system run")
        return 0

    from sandbox.tree_lab.cases import load_case
    from sandbox.tree_lab.runner import run_case

    case = load_case(case_root)
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    run_dir = RUN_ROOT / case_id / "demo-1"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    record = run_case(case, RUN_ROOT / case_id, run_id="demo-1", timeout_s=1800)
    outline_geometry = row.geometry
    if outline_geometry.geom_type == "MultiPolygon":
        outline_geometry = max(
            outline_geometry.geoms, key=lambda part: part.area
        )
    outline = [
        [round(float(x), 3), round(float(y), 3)]
        for x, y in outline_geometry.exterior.coords
    ]
    events_path = (
        RUN_ROOT / case_id / "demo-1" / "system" / "system_events.json"
    )
    events = json.loads(events_path.read_text(encoding="utf-8"))
    events["block_outline"] = outline
    events_path.write_text(json.dumps(events, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record.get("kpis", {}), indent=2))
    print(f"run {RUN_ROOT / case_id / 'demo-1'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
