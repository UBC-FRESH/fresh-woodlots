#!/usr/bin/env python3
"""Generate a FHOPS pilot scenario from a WS4 AAC baseline.

The scenario covers the first 10-year period of the WS4 AAC baseline. Block
volumes are allocated in proportion to block area, and a four-role ground-based
chain is staffed at a fixed daily rate. It is a contract and integration
pilot, not a production operating plan.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import pandas as pd
import yaml

MACHINES = (
    ("H1", "feller_buncher", 875.0),
    ("H2", "grapple_skidder", 925.0),
    ("H3", "roadside_processor", 1050.0),
    ("H4", "loader", 900.0),
)
DAILY_RATE = 250.0
LANDING = "L1"


def _write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-root", type=Path, required=True)
    parser.add_argument("--period", type=int, default=10)
    parser.add_argument("--aac", type=float, required=True, help="AAC m3/yr")
    parser.add_argument("--daily-rate", type=float, default=DAILY_RATE)
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Override the computed horizon",
    )
    parser.add_argument(
        "--season-days",
        type=int,
        default=0,
        help="Working days per year; 0 means every day is available",
    )
    parser.add_argument("--name", default=None, help="Scenario name override")
    parser.add_argument(
        "--block-ids",
        default=None,
        help="Comma-separated WS4 block IDs to include",
    )
    parser.add_argument(
        "--target-volume",
        type=float,
        default=None,
        help="Override the target volume; default AAC x period",
    )
    parser.add_argument(
        "--volume-map",
        type=Path,
        default=None,
        help="Optional JSON mapping numeric WS4 block ID to exact work volume (m3)",
    )
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    instance_root = args.instance_root.resolve()
    slug = instance_root.name
    prefix = slug.split("-")[-1].upper()
    out_root = args.out or (instance_root / "fhops")
    data_root = out_root / "data"
    data_root.mkdir(parents=True, exist_ok=True)

    schedule = pd.read_csv(
        instance_root / "ws4" / "runs" / "aac_baseline" / "schedule.csv"
    )
    blocks = pd.read_parquet(
        instance_root / "ws4" / "build" / "compiled" / "blocks.parquet"
    )
    areas = blocks.groupby("block_id")["area_ha"].sum()
    if args.block_ids:
        wanted = {
            int(item)
            for item in args.block_ids.split(",")
            if item.strip()
        }
        selected = [
            (block_id, float(areas.loc[block_id]))
            for block_id in sorted(wanted)
            if block_id in areas.index
        ]
        if not selected:
            raise SystemExit("No requested blocks in the compiled dataset")
    else:
        first = schedule[schedule["offset"] < args.period].copy()
        first = first.drop_duplicates(subset=["block_id"], keep="first")
        if first.empty:
            # Some woodlots have no harvest scheduled in the first 10 years.
            # Use the first 10-year window that contains blocks instead.
            start = int(schedule["offset"].min()) if not schedule.empty else 0
            first = schedule[
                (schedule["offset"] >= start)
                & (schedule["offset"] < start + args.period)
            ].copy()
            first = first.drop_duplicates(subset=["block_id"], keep="first")
        if first.empty:
            raise SystemExit("No blocks in the first WS4 period")
        selected = [
            (int(block_id), float(areas.loc[int(block_id)]))
            for block_id in first["block_id"]
            if int(block_id) in areas.index
        ]
    total_area = sum(area for _block, area in selected)
    target_volume = args.target_volume or args.aac * args.period
    volume_map: dict[str, float] = {}
    if args.volume_map:
        payload = json.loads(args.volume_map.read_text(encoding="utf-8"))
        volume_map = {str(key): float(value) for key, value in payload.items()}
    block_rows: list[dict[str, object]] = []
    for block_id, area in selected:
        if str(block_id) in volume_map:
            volume = round(volume_map[str(block_id)], 3)
        else:
            volume = round(target_volume * area / total_area, 3)
        block_rows.append(
            {
                "id": f"{prefix}-{block_id}",
                "landing_id": LANDING,
                "harvest_system_id": "ground_fb_skid",
                "work_required": volume,
                "earliest_start": 1,
                "latest_finish": 0,
            }
        )

    target_volume = sum(float(row["work_required"]) for row in block_rows)
    num_days = args.days or max(
        30,
        math.ceil(target_volume / args.daily_rate) + 10,
    )
    for row in block_rows:
        row["latest_finish"] = num_days

    machine_rows = [
        {
            "id": machine_id,
            "crew": f"C{machine_id}",
            "daily_hours": 10.0,
            "operating_cost": cost,
            "role": role,
        }
        for machine_id, role, cost in MACHINES
    ]
    landing_rows = [{"id": LANDING, "daily_capacity": 2}]
    calendar_rows: list[dict[str, object]] = []
    for machine_id, _role, _cost in MACHINES:
        if args.season_days > 0:
            for year in range(math.ceil(num_days / 365)):
                start = year * 365 + 1
                end = min(num_days, start + args.season_days - 1)
                for day in range(start, end + 1):
                    calendar_rows.append(
                        {"machine_id": machine_id, "day": day, "available": 1}
                    )
        else:
            for day in range(1, num_days + 1):
                calendar_rows.append(
                    {"machine_id": machine_id, "day": day, "available": 1}
                )
    rate_rows = [
        {
            "machine_id": machine_id,
            "block_id": f"{prefix}-{block_id}",
            "rate": args.daily_rate,
        }
        for machine_id, _role, _cost in MACHINES
        for block_id, _area in selected
    ]

    _write_csv(
        data_root / "blocks.csv",
        block_rows,
        [
            "id",
            "landing_id",
            "harvest_system_id",
            "work_required",
            "earliest_start",
            "latest_finish",
        ],
    )
    _write_csv(
        data_root / "machines.csv",
        machine_rows,
        ["id", "crew", "daily_hours", "operating_cost", "role"],
    )
    _write_csv(data_root / "landings.csv", landing_rows, ["id", "daily_capacity"])
    _write_csv(
        data_root / "calendar.csv",
        calendar_rows,
        ["machine_id", "day", "available"],
    )
    _write_csv(
        data_root / "prod_rates.csv",
        rate_rows,
        ["machine_id", "block_id", "rate"],
    )
    scenario = {
        "name": args.name or f"{prefix} first AAC period",
        "num_days": num_days,
        "start_date": "2026-01-01",
        "data": {
            "blocks": "data/blocks.csv",
            "machines": "data/machines.csv",
            "landings": "data/landings.csv",
            "calendar": "data/calendar.csv",
            "prod_rates": "data/prod_rates.csv",
        },
        "objective_weights": {"production": 1.0, "mobilisation": 0.0},
    }
    (out_root / "scenario.yaml").write_text(
        yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8"
    )
    print(
        f"Wrote FHOPS scenario: {len(block_rows)} blocks, {num_days} days, "
        f"{target_volume:,.0f} m3 target"
    )
    print(f"Scenario: {out_root / 'scenario.yaml'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
