#!/usr/bin/env python3
"""Rebuild the WS4 side of already-built instances with the factor-weighted THLB split.

This reuses the existing VRI, VDYP, and bundled inputs (SKIP_UPSTREAM=1), then
re-runs TIPSY, the Patchworks export, the net THLB split, the WS4 compile, the
runtime geometry, the smoke run, the AAC search, and the baseline. FHOPS is
left for the separate FHOPS batch because its volumes also change.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "queue" / "woodlot_build_queue.json"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_instance.sh"
LOG_ROOT = REPO_ROOT / "batch" / "repair"


def _read_queue() -> dict[str, object]:
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def _write_queue(payload: dict[str, object]) -> None:
    temp = QUEUE_PATH.with_suffix(".tmp")
    temp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temp.replace(QUEUE_PATH)


def _mark(payload: dict[str, object], slug: str, notes: str) -> None:
    for entry in payload.get("instances", []):
        if entry.get("slug") == slug:
            entry["notes"] = notes
            entry["updated_at"] = datetime.now(UTC).isoformat(timespec="seconds")
            return


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=10)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only", action="append", default=None)
    parser.add_argument("--skip", action="append", default=None)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--aac-search-time", default="00:00:30")
    args = parser.parse_args(argv)

    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    payload = _read_queue()
    skip = set(args.skip or [])
    instances = [
        entry
        for entry in payload.get("instances", [])
        if entry.get("status") == "built" and entry.get("slug") not in skip
    ]
    if args.only:
        wanted = set(args.only)
        instances = [entry for entry in instances if entry.get("slug") in wanted]
    if args.limit:
        instances = instances[: args.limit]
    if not instances:
        print("No built instances to repair.")
        return 0

    print(f"Repair queue: {len(instances)} instances; jobs={args.jobs}")
    env = dict(os.environ)
    env.update(
        {
            "SKIP_UPSTREAM": "1",
            "SKIP_FHOPS": "1",
            "AAC_SEARCH_TIME": args.aac_search_time,
            "OPT_THREADS": "4",
            "FEMIC_DISABLE_IPP": "1",
        }
    )
    lock = threading.Lock()
    completed = 0
    failed = 0

    def run_one(entry: dict[str, object]) -> None:
        nonlocal completed, failed
        slug = str(entry["slug"])
        log_path = LOG_ROOT / f"{slug}.log"
        started = time.monotonic()
        try:
            with log_path.open("w", encoding="utf-8") as log:
                result = subprocess.run(
                    ["/usr/bin/time", "-v", str(BUILD_SCRIPT), slug],
                    cwd=REPO_ROOT,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=args.timeout,
                    check=False,
                )
        except subprocess.TimeoutExpired:
            with lock:
                _mark(payload, slug, f"repair timeout after {args.timeout}s")
                _write_queue(payload)
                failed += 1
            print(f"{slug}: repair timeout")
            return
        elapsed = time.monotonic() - started
        with lock:
            if result.returncode == 0:
                _mark(payload, slug, "rebuilt with factor-weighted THLB split")
                completed += 1
                print(f"{slug}: repaired in {elapsed:.0f}s")
            else:
                _mark(payload, slug, f"repair exit {result.returncode}")
                failed += 1
                print(f"{slug}: repair failed ({result.returncode})")
            _write_queue(payload)

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_one, entry) for entry in instances]
        for future in as_completed(futures):
            future.result()

    print(f"Repair state: completed={completed} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
