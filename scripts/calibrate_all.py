#!/usr/bin/env python3
"""Run the W4W base-scenario calibration for every built woodlot."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "queue" / "woodlot_build_queue.json"
CALIBRATOR = REPO_ROOT / "scripts" / "calibrate_w4w_aac.py"
LOG_ROOT = REPO_ROOT / "batch" / "calibration"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only", action="append", default=None)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args(argv)

    payload = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    entries = [
        entry
        for entry in payload.get("instances", [])
        if entry.get("status") in ("built", "pilot_built")
        and (REPO_ROOT / "instances" / entry["slug"] / "ws4" / "build" / "compiled").is_dir()
    ]
    if args.only:
        wanted = set(args.only)
        entries = [entry for entry in entries if entry.get("slug") in wanted]
    if args.limit:
        entries = entries[: args.limit]
    if not entries:
        print("No built instances to calibrate.")
        return 0

    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"Calibration queue: {len(entries)} instances; jobs={args.jobs}")
    completed = 0
    failed: list[str] = []

    def run_one(entry: dict[str, object]) -> tuple[str, bool, str]:
        slug = str(entry["slug"])
        log_path = LOG_ROOT / f"{slug}.log"
        started = time.monotonic()
        with log_path.open("w", encoding="utf-8") as log:
            result = subprocess.run(
                [
                    sys.executable,
                    str(CALIBRATOR),
                    "--slug",
                    slug,
                    "--quick",
                    "--write-docs",
                ],
                cwd=REPO_ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=args.timeout,
                check=False,
            )
        elapsed = time.monotonic() - started
        return slug, result.returncode == 0, f"{elapsed:.1f}s"

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_one, entry) for entry in entries]
        for future in as_completed(futures):
            slug, ok, elapsed = future.result()
            if ok:
                completed += 1
                print(f"{slug}: calibrated in {elapsed}")
            else:
                failed.append(slug)
                print(f"{slug}: calibration failed")

    print(f"Calibration state: completed={completed} failed={len(failed)}")
    if failed:
        print("Failed:", " ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
