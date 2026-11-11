#!/usr/bin/env python3
"""Build and solve a ten-year seasonal FHOPS plan for selected demo CFAs.

The plan uses the first WS4 10-year period blocks, the annual AAC, a 3,650-day
horizon, and a 180-day operating season each year. It is a multi-year
tactical/operational schedule, not the formal TOPM tactical MILP and not a
production operating plan.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "queue" / "woodlot_build_queue.json"
BUILD_SCENARIO = REPO_ROOT / "scripts" / "build_fhops_pilot.py"


def _kpi(text: str, name: str) -> float | None:
    match = re.search(rf"{name}:\s*([0-9.]+)", text)
    return float(match.group(1)) if match else None


def _run(command: list[str], *, cwd: Path, log, timeout: int = 1800) -> int:
    result = subprocess.run(
        command,
        cwd=cwd,
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=QUEUE_PATH)
    parser.add_argument("--only", action="append", default=None)
    parser.add_argument("--iterations", type=int, default=800)
    parser.add_argument("--season-days", type=int, default=180)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    payload = json.loads(args.queue.read_text(encoding="utf-8"))
    wanted = set(args.only) if args.only else {"cfa-k1e", "cfa-k2e", "cfa-k3x"}
    for entry in payload.get("instances", []):
        slug = str(entry.get("slug"))
        if slug not in wanted:
            continue
        if entry.get("status") not in ("built", "pilot_built"):
            continue
        aac = entry.get("aac_m3")
        if not aac:
            print(f"{slug}: no AAC")
            continue
        root = REPO_ROOT / "instances" / slug
        fhops = root / "fhops"
        if not fhops.is_dir():
            print(f"{slug}: no FHOPS directory")
            continue
        backup = root / "fhops_compressed_450d"
        if not backup.exists() and (fhops / "summary.json").is_file():
            shutil.copytree(fhops, backup)
            print(f"{slug}: backed up compressed plan to {backup.name}")
        if (fhops / "summary.json").is_file() and not args.force:
            current = json.loads((fhops / "summary.json").read_text(encoding="utf-8"))
            if current.get("plan_kind") == "tenyear":
                print(f"{slug}: ten-year plan already present")
                continue

        rate = max(0.05, float(aac) / (args.season_days * 4.0))
        log_path = REPO_ROOT / "batch" / "tenyear" / f"{slug}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        with log_path.open("w", encoding="utf-8") as log:
            build = _run(
                [
                    "python3",
                    str(BUILD_SCENARIO),
                    "--instance-root",
                    str(root),
                    "--period",
                    "10",
                    "--aac",
                    str(aac),
                    "--daily-rate",
                    f"{rate:.6f}",
                    "--days",
                    "3650",
                    "--season-days",
                    str(args.season_days),
                    "--name",
                    f"{slug.split('-')[-1].upper()} 10-year seasonal plan",
                    "--out",
                    str(fhops),
                ],
                cwd=REPO_ROOT,
                log=log,
            )
            if build != 0:
                print(f"{slug}: scenario build failed")
                continue
            validate = _run(
                ["fhops", "validate", "scenario.yaml"], cwd=fhops, log=log
            )
            if validate != 0:
                print(f"{slug}: validate failed")
                continue
            (fhops / "out").mkdir(exist_ok=True)
            solve = _run(
                [
                    "fhops",
                    "solve-heur",
                    "scenario.yaml",
                    "--out",
                    "out/heur_solution.csv",
                    "--iters",
                    str(args.iterations),
                ],
                cwd=fhops,
                log=log,
                timeout=3600,
            )
            if solve != 0:
                print(f"{slug}: solve failed")
                continue
            evaluate = subprocess.run(
                [
                    "fhops",
                    "evaluate",
                    "scenario.yaml",
                    "--assignments",
                    "out/heur_solution.csv",
                ],
                cwd=fhops,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=3600,
            )
            log.write(evaluate.stdout)
            if evaluate.returncode != 0:
                print(f"{slug}: evaluate failed")
                continue
            makespan = _kpi(evaluate.stdout, "makespan_day")
            summary = {
                "schema_version": 1,
                "plan_kind": "tenyear",
                "aac_m3": float(aac),
                "rate_m3_per_day": round(rate, 6),
                "horizon_days": 3650,
                "season_days": args.season_days,
                "years": 10,
                "total_production_m3": _kpi(
                    evaluate.stdout, "total_production"
                ),
                "completed_blocks": _kpi(evaluate.stdout, "completed_blocks"),
                "makespan_day": makespan,
                "makespan_years": (
                    round(makespan / 365.0, 2) if makespan is not None else None
                ),
                "sequencing_violation_count": _kpi(
                    evaluate.stdout, "sequencing_violation_count"
                ),
                "elapsed_sec": round(time.monotonic() - started, 1),
            }
            (fhops / "summary.json").write_text(
                json.dumps(summary, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        entry["fhops"] = {"status": "built", "summary": summary}
        print(
            f"{slug}: 10-year plan blocks={summary['completed_blocks']} "
            f"volume={summary['total_production_m3']} "
            f"makespan={summary['makespan_years']} years"
        )

    # Let the portal map/timeline and theatre builders consume the new plan.
    for script in ("prepare_fhops_maps.py", "prepare_theatre.py"):
        subprocess.run(
            ["python3", str(REPO_ROOT / "scripts" / script)],
            cwd=REPO_ROOT,
            check=False,
        )
    args.queue.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
