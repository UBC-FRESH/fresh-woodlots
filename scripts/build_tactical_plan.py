#!/usr/bin/env python3
"""Build and solve a formal 10-year FHOPS tactical-operational plan.

The tactical scenario uses the real WS4 block geometry/area for the selected
FHOPS blocks and distributes the ten-year AAC across those areas. Product
yields are a transparent 70/30 sawlog/pulp split until WS4 product curves are
wired into the planning-unit contract.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import date
from pathlib import Path

import geopandas as gpd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "queue" / "woodlot_build_queue.json"
YEARS = 10
SAWLOG_SHARE = 0.70
PULP_SHARE = 0.30


def _periods() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(YEARS):
        start = date(2026 + index, 1, 1)
        end = date(2026 + index, 12, 31)
        rows.append(
            {
                "period_id": f"Y{index + 1}",
                "level": "year",
                "sequence": index + 1,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "duration_days": (end - start).days + 1,
                "available_hours": 4320,
                "discount_factor": round(1 / (1.04**index), 6),
                "season_tags": ["annual"],
            }
        )
    return rows


def build_scenario(root: Path, years: int = YEARS) -> Path:
    slug = root.name
    prefix = slug.split("-")[-1].upper()
    summary = json.loads((root / "fhops" / "summary.json").read_text(encoding="utf-8"))
    aac = float(summary["aac_m3"])
    blocks = gpd.read_file(root / "fhops" / "out" / "scheduled_blocks.geojson")
    if blocks.empty:
        raise SystemExit(f"{slug}: no scheduled blocks")
    total_area = float(blocks["area_ha"].sum())
    total_volume = aac * years
    yield_per_ha = total_volume / total_area
    periods = _periods()[:years]

    planning_units: list[dict[str, object]] = []
    options: list[dict[str, object]] = []
    arcs: list[dict[str, object]] = []
    for row in blocks.itertuples(index=False):
        block_id = str(row.label)
        area = float(row.area_ha)
        total_yield = area * yield_per_ha
        planning_units.append(
            {
                "block_id": block_id,
                "gross_area_ha": area,
                "operable_area_ha": area,
                "forest_class": "woodlot",
                "initial_state": "mature",
                "product_yields_m3_per_ha": {
                    "sawlog": yield_per_ha * SAWLOG_SHARE,
                    "pulp": yield_per_ha * PULP_SHARE,
                },
            }
        )
        for period in periods:
            period_id = str(period["period_id"])
            options.append(
                {
                    "option_id": f"{block_id}__ground_fb_skid__{period_id}",
                    "block_id": block_id,
                    "system_id": "ground_fb_skid",
                    "period_id": period_id,
                    "eligible": True,
                    "min_area_ha": 0.0,
                    "max_area_ha": area,
                    "variable_cost_per_m3": 20.0,
                    "fixed_cost": 0.0,
                    "productivity_m3_per_period": total_yield,
                }
            )
            for product_id, facility_id, cost in (
                ("sawlog", "mill_saw", 6.0),
                ("pulp", "mill_pulp", 8.0),
            ):
                arcs.append(
                    {
                        "arc_id": f"{block_id}__{facility_id}__{period_id}",
                        "origin_id": block_id,
                        "destination_id": facility_id,
                        "product_id": product_id,
                        "mode": "truck",
                        "period_id": period_id,
                        "cost_per_m3": cost,
                        "capacity_m3": aac * 1.2,
                    }
                )

    fleet = [
        {
            "system_id": "ground_fb_skid",
            "period_id": str(period["period_id"]),
            "capacity_m3": aac * 1.5,
            "capacity_hours": 4320,
        }
        for period in periods
    ]
    demand: list[dict[str, object]] = []
    for period in periods:
        period_id = str(period["period_id"])
        demand.append(
            {
                "facility_id": "mill_saw",
                "product_id": "sawlog",
                "period_id": period_id,
                "minimum_m3": aac * SAWLOG_SHARE,
                "target_m3": aac * SAWLOG_SHARE,
                "maximum_m3": aac * SAWLOG_SHARE,
            }
        )
        demand.append(
            {
                "facility_id": "mill_pulp",
                "product_id": "pulp",
                "period_id": period_id,
                "minimum_m3": aac * PULP_SHARE,
                "target_m3": aac * PULP_SHARE,
                "maximum_m3": aac * PULP_SHARE,
            }
        )

    scenario = {
        "name": f"{prefix} tactical 10-year plan",
        "planning_level": "tactical_operational",
        "schema_version": "0.1.0",
        "economics": {
            "currency": "CAD",
            "base_year": 2026,
            "discount_rate_per_year": 0.04,
            "objective_profile": "min_discounted_delivered_cost",
        },
        "periods": periods,
        "products": [
            {"product_id": "sawlog", "species_group": "mixed", "grade": "sawlog"},
            {"product_id": "pulp", "species_group": "mixed", "grade": "pulp"},
        ],
        "planning_units": planning_units,
        "harvest_system_options": options,
        "fleet_capacity": fleet,
        "facilities": [
            {
                "facility_id": "mill_saw",
                "facility_type": "sawmill",
                "accepted_products": ["sawlog"],
            },
            {
                "facility_id": "mill_pulp",
                "facility_type": "pulp_mill",
                "accepted_products": ["pulp"],
            },
        ],
        "facility_demand": demand,
        "initial_inventory": [],
        "transport_arcs": arcs,
        "external_supply": [],
    }
    output = root / "fhops" / "tactical" / "scenario.yaml"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8")
    return output


def solve_scenario(
    root: Path,
    scenario_path: Path,
    time_limit: int = 180,
) -> dict[str, object]:
    out_dir = root / "fhops" / "tactical" / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "fhops",
        "plan",
        "tactical-operational",
        str(scenario_path),
        "--harvest-mode",
        "continuous",
        "--demand-basis",
        "target",
        "--time-limit",
        str(time_limit),
        "--gap",
        "0.01",
        "--out-json",
        str(out_dir / "result.json"),
        "--out-harvest-csv",
        str(out_dir / "harvest.csv"),
        "--out-production-csv",
        str(out_dir / "production.csv"),
    ]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        raise SystemExit(result.stdout[-4000:])
    payload = json.loads((out_dir / "result.json").read_text(encoding="utf-8"))
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=QUEUE_PATH)
    parser.add_argument("--only", action="append", default=None)
    parser.add_argument("--years", type=int, default=YEARS)
    parser.add_argument("--time-limit", type=int, default=180)
    args = parser.parse_args(argv)

    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    wanted = set(args.only) if args.only else None
    for entry in queue.get("instances", []):
        slug = str(entry.get("slug"))
        if wanted is not None and slug not in wanted:
            continue
        if entry.get("status") not in ("built", "pilot_built"):
            continue
        root = REPO_ROOT / "instances" / slug
        scenario_path = build_scenario(root, args.years)
        payload = solve_scenario(root, scenario_path, args.time_limit)
        harvest = payload.get("harvest_decisions") or []
        selected = [
            row
            for row in harvest
            if float(row.get("harvested_area_ha") or 0) > 0
        ]
        print(
            f"{slug}: tactical {payload.get('termination_condition')} "
            f"objective={payload.get('objective')} commitments={len(selected)} "
            f"blocks={len({row['block_id'] for row in selected})}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
