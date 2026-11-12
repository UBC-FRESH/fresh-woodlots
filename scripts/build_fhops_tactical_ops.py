#!/usr/bin/env python3
"""Compile a solved tactical plan into ten annual operational FHOPS seasons."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "queue" / "woodlot_build_queue.json"
BUILD_SCENARIO = REPO_ROOT / "scripts" / "build_fhops_pilot.py"
YEARS = 10
YEAR_DAYS = 365
SEASON_DAYS = 180


def _kpi(text: str, name: str) -> float:
    match = re.search(rf"{name}:\s*([0-9.]+)", text)
    return float(match.group(1)) if match else 0.0


def _numeric(label: object) -> str:
    return str(int(str(label).rsplit("-", 1)[-1]))


def _run(command: list[str], cwd: Path, log, timeout: int = 3600) -> int:
    result = subprocess.run(
        command,
        cwd=cwd,
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )
    return result.returncode


def build_one(
    root: Path,
    aac: float,
    *,
    iterations: int,
    target_days: float,
) -> dict[str, object] | None:
    slug = root.name
    prefix = slug.split("-")[-1].upper()
    tactical_dir = root / "fhops" / "tactical"
    harvest_path = tactical_dir / "out" / "harvest.csv"
    if not harvest_path.is_file():
        print(f"{slug}: no tactical harvest decisions")
        return None
    harvest = pd.read_csv(harvest_path)
    harvest = harvest[harvest["harvested_area_ha"] > 0].copy()
    if harvest.empty:
        print(f"{slug}: tactical plan has no commitments")
        return None

    work = root / "fhops_tactical_ops"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    combined_solution: list[pd.DataFrame] = []
    combined_blocks: list[pd.DataFrame] = []
    year_summaries: list[dict[str, object]] = []
    rate = max(250.0, aac / max(1.0, target_days))
    started = time.monotonic()

    for year in range(1, YEARS + 1):
        rows = harvest[harvest["period_id"] == f"Y{year}"]
        if rows.empty:
            print(f"{slug}: no tactical commitment in year {year}")
            return None
        block_ids = [_numeric(label) for label in rows["block_id"]]
        volumes = {
            _numeric(label): float(volume)
            for label, volume in zip(
                rows["block_id"],
                rows["total_volume_m3"],
                strict=False,
            )
        }
        target = sum(volumes.values())
        year_root = work / f"year-{year:02d}"
        year_root.mkdir()
        volume_path = year_root / "volumes.json"
        volume_path.write_text(json.dumps(volumes), encoding="utf-8")
        log_path = REPO_ROOT / "batch" / "tactical" / f"{slug}-{year:02d}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", encoding="utf-8") as log:
            build = _run(
                [
                    sys.executable,
                    str(BUILD_SCENARIO),
                    "--instance-root",
                    str(root),
                    "--period",
                    str(YEARS),
                    "--block-ids",
                    ",".join(block_ids),
                    "--target-volume",
                    str(target),
                    "--volume-map",
                    str(volume_path),
                    "--aac",
                    str(aac),
                    "--daily-rate",
                    f"{rate:.6f}",
                    "--days",
                    str(SEASON_DAYS),
                    "--season-days",
                    str(SEASON_DAYS),
                    "--name",
                    f"{prefix} tactical year {year}",
                    "--out",
                    str(year_root),
                ],
                cwd=REPO_ROOT,
                log=log,
            )
            if build != 0:
                print(f"{slug}: year {year} build failed")
                return None
            if _run(["fhops", "validate", "scenario.yaml"], year_root, log):
                print(f"{slug}: year {year} validate failed")
                return None
            (year_root / "out").mkdir(exist_ok=True)
            if _run(
                [
                    "fhops",
                    "solve-heur",
                    "scenario.yaml",
                    "--out",
                    "out/heur_solution.csv",
                    "--iters",
                    str(iterations),
                ],
                year_root,
                log,
            ):
                print(f"{slug}: year {year} solve failed")
                return None
            evaluate = subprocess.run(
                [
                    "fhops",
                    "evaluate",
                    "scenario.yaml",
                    "--assignments",
                    "out/heur_solution.csv",
                ],
                cwd=year_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=3600,
            )
            log.write(evaluate.stdout)
            if evaluate.returncode != 0:
                print(f"{slug}: year {year} evaluate failed")
                return None
            processed = _kpi(evaluate.stdout, "total_production")
            staged = _kpi(evaluate.stdout, "staged_production")
            year_summaries.append(
                {
                    "year": year,
                    "blocks": [str(label) for label in rows["block_id"]],
                    "planned_m3": round(target, 3),
                    "processed_m3": round(processed, 3),
                    "staged_m3": round(staged, 3),
                    "harvested_m3": round(processed + staged, 3),
                }
            )

        solution = pd.read_csv(year_root / "out" / "heur_solution.csv")
        solution["day"] = solution["day"].astype(int) + (year - 1) * YEAR_DAYS
        combined_solution.append(solution)
        blocks = pd.read_csv(year_root / "data" / "blocks.csv")
        blocks["year"] = year
        combined_blocks.append(blocks)

    fhops = root / "fhops"
    (fhops / "data").mkdir(parents=True, exist_ok=True)
    (fhops / "out").mkdir(parents=True, exist_ok=True)
    pd.concat(combined_solution, ignore_index=True).to_csv(
        fhops / "out" / "heur_solution.csv",
        index=False,
    )
    combined = pd.concat(combined_blocks, ignore_index=True)
    combined["work_required"] = combined["work_required"].astype(float)
    combined.to_csv(fhops / "data" / "blocks.csv", index=False)
    for name in ("machines.csv", "landings.csv"):
        shutil.copy2(work / "year-01" / "data" / name, fhops / "data" / name)
    rate_frames = [
        pd.read_csv(work / f"year-{year:02d}" / "data" / "prod_rates.csv")
        for year in range(1, YEARS + 1)
    ]
    pd.concat(rate_frames, ignore_index=True).drop_duplicates().to_csv(
        fhops / "data" / "prod_rates.csv",
        index=False,
    )
    calendar_rows = []
    for year in year_summaries:
        frame = pd.read_csv(
            work / f"year-{year['year']:02d}" / "data" / "calendar.csv"
        )
        frame["day"] = frame["day"].astype(int) + (year["year"] - 1) * YEAR_DAYS
        calendar_rows.append(frame)
    pd.concat(calendar_rows, ignore_index=True).to_csv(
        fhops / "data" / "calendar.csv",
        index=False,
    )
    scenario = {
        "name": f"{prefix} tactical 10-year plan",
        "num_days": YEAR_DAYS * YEARS,
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
    (fhops / "scenario.yaml").write_text(
        yaml.safe_dump(scenario, sort_keys=False),
        encoding="utf-8",
    )
    total_harvest = sum(float(item["harvested_m3"]) for item in year_summaries)
    total_processed = sum(float(item["processed_m3"]) for item in year_summaries)
    total_staged = sum(float(item["staged_m3"]) for item in year_summaries)
    summary = {
        "schema_version": 1,
        "plan_kind": "tactical_operational",
        "tactical_result": "fhops/tactical/out/result.json",
        "aac_m3": float(aac),
        "rate_m3_per_day": round(rate, 6),
        "horizon_days": YEAR_DAYS * YEARS,
        "season_days": SEASON_DAYS,
        "years": YEARS,
        "annual_total_production_m3": round(total_harvest / YEARS, 3),
        "annual_processed_m3": round(total_processed / YEARS, 3),
        "annual_staged_m3": round(total_staged / YEARS, 3),
        "total_production_m3": round(total_harvest, 3),
        "blocks_treated": len(
            {block for item in year_summaries for block in item["blocks"]}
        ),
        "completed_blocks": 0.0,
        "makespan_day": YEAR_DAYS * YEARS,
        "makespan_years": YEARS,
        "sequencing_violation_count": 0.0,
        "elapsed_sec": round(time.monotonic() - started, 1),
        "year_allocations": year_summaries,
    }
    (fhops / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=QUEUE_PATH)
    parser.add_argument("--only", action="append", default=None)
    parser.add_argument("--iterations", type=int, default=400)
    parser.add_argument("--target-days", type=float, default=20.0)
    args = parser.parse_args(argv)
    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    wanted = set(args.only) if args.only else {"wl-w0026", "wl-w1548", "wl-w2023"}
    for entry in queue.get("instances", []):
        slug = str(entry.get("slug"))
        if slug not in wanted:
            continue
        aac = entry.get("aac_m3")
        if not aac:
            print(f"{slug}: no AAC")
            continue
        summary = build_one(
            REPO_ROOT / "instances" / slug,
            float(aac),
            iterations=args.iterations,
            target_days=args.target_days,
        )
        if summary:
            print(
                f"{slug}: {summary['annual_total_production_m3']} m3/yr, "
                f"{summary['blocks_treated']} blocks, "
                f"{summary['elapsed_sec']} s"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
