#!/usr/bin/env python3
"""Generate and solve a FHOPS operational pilot for every built woodlot.

The scenario uses the first 10-year period of the WS4 AAC baseline and a
four-machine ground-based chain. It is a contract/integration pilot, not a
production operating plan.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "queue" / "woodlot_build_queue.json"
LOG_ROOT = REPO_ROOT / "batch" / "fhops"
BUILD_SCENARIO = REPO_ROOT / "scripts" / "build_fhops_pilot.py"


def _read_queue() -> dict[str, object]:
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def _write_queue(payload: dict[str, object]) -> None:
    temp = QUEUE_PATH.with_suffix(".tmp")
    temp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temp.replace(QUEUE_PATH)


def _parse_kpi(text: str, name: str) -> float | None:
    match = re.search(rf"{name}:\s*([0-9.]+)", text)
    return float(match.group(1)) if match else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only", action="append", default=None)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--timeout", type=int, default=3600)
    args = parser.parse_args(argv)

    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    payload = _read_queue()
    instances = list(payload.get("instances", []))
    if args.only:
        wanted = set(args.only)
        instances = [entry for entry in instances if entry.get("slug") in wanted]

    queue = []
    for entry in instances:
        if entry.get("status") not in ("built", "pilot_built"):
            continue
        prior = entry.get("fhops") or {}
        if prior.get("status") == "built" and not args.retry_failed:
            continue
        if not entry.get("aac_m3"):
            continue
        queue.append(entry)
    if args.limit:
        queue = queue[: args.limit]
    if not queue:
        print("No FHOPS pilots to build.")
        return 0

    print(f"FHOPS queue: {len(queue)} instances; jobs={args.jobs}")

    lock = threading.Lock()
    completed = 0

    def run_one(entry: dict[str, object]) -> None:
        nonlocal completed
        slug = str(entry["slug"])
        instance_root = REPO_ROOT / "instances" / slug
        fhops_root = instance_root / "fhops"
        log_path = LOG_ROOT / f"{slug}.log"
        schedule_path = (
            instance_root / "ws4" / "runs" / "aac_baseline" / "schedule.csv"
        )
        if not schedule_path.exists():
            with lock:
                entry["fhops"] = {"status": "failed", "reason": "no AAC baseline"}
                _write_queue(payload)
                print(f"{slug}: no AAC baseline")
            return

        aac = float(entry["aac_m3"])
        volume = aac * 10.0
        rate = max(250.0, math.ceil(volume / 180.0))
        days = max(450, math.ceil(volume / rate) * 2 + 60)
        with log_path.open("w", encoding="utf-8") as log:
            started = time.monotonic()
            build = subprocess.run(
                [
                    "python3",
                    str(BUILD_SCENARIO),
                    "--instance-root",
                    str(instance_root),
                    "--aac",
                    str(aac),
                    "--daily-rate",
                    str(rate),
                    "--days",
                    str(days),
                ],
                cwd=REPO_ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=args.timeout,
            )
            if build.returncode != 0:
                with lock:
                    entry["fhops"] = {
                        "status": "failed",
                        "reason": f"scenario generation exit {build.returncode}",
                    }
                    _write_queue(payload)
                    print(f"{slug}: scenario generation failed")
                return
            validate = subprocess.run(
                ["fhops", "validate", "scenario.yaml"],
                cwd=fhops_root,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=args.timeout,
            )
            if validate.returncode != 0:
                with lock:
                    entry["fhops"] = {
                        "status": "failed",
                        "reason": f"fhops validate exit {validate.returncode}",
                    }
                    _write_queue(payload)
                    print(f"{slug}: validate failed")
                return
            (fhops_root / "out").mkdir(exist_ok=True)
            solve = subprocess.run(
                [
                    "fhops",
                    "solve-heur",
                    "scenario.yaml",
                    "--out",
                    "out/heur_solution.csv",
                ],
                cwd=fhops_root,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=args.timeout,
            )
            if solve.returncode != 0:
                with lock:
                    entry["fhops"] = {
                        "status": "failed",
                        "reason": f"fhops solve exit {solve.returncode}",
                    }
                    _write_queue(payload)
                    print(f"{slug}: solve failed")
                return
            evaluate = subprocess.run(
                [
                    "fhops",
                    "evaluate",
                    "scenario.yaml",
                    "--assignments",
                    "out/heur_solution.csv",
                ],
                cwd=fhops_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=args.timeout,
            )
            log.write(evaluate.stdout)
            total = _parse_kpi(evaluate.stdout, "total_production")
            blocks = _parse_kpi(evaluate.stdout, "completed_blocks")
            makespan = _parse_kpi(evaluate.stdout, "makespan_day")
            violations = _parse_kpi(evaluate.stdout, "sequencing_violation_count")
            summary = {
                "schema_version": 1,
                "aac_m3": aac,
                "rate_m3_per_day": rate,
                "horizon_days": days,
                "total_production_m3": total,
                "completed_blocks": blocks,
                "makespan_day": makespan,
                "sequencing_violation_count": violations,
                "elapsed_sec": round(time.monotonic() - started, 1),
            }
            (fhops_root / "summary.json").write_text(
                json.dumps(summary, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        with lock:
            entry["fhops"] = {
                "status": "built" if evaluate.returncode == 0 else "failed",
                "summary": summary,
            }
            _write_queue(payload)
            completed += 1
            print(
                f"{slug}: FHOPS {entry['fhops']['status']} "
                f"blocks={blocks} production={total} makespan={makespan} "
                f"[{completed}/{len(queue)}]"
            )

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_one, entry) for entry in queue]
        for future in as_completed(futures):
            future.result()

    built = sum(
        1
        for entry in payload.get("instances", [])
        if (entry.get("fhops") or {}).get("status") == "built"
    )
    failed = sum(
        1
        for entry in payload.get("instances", [])
        if (entry.get("fhops") or {}).get("status") == "failed"
    )
    print(f"FHOPS state: built={built} failed={failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
