#!/usr/bin/env python3
"""Run the remaining woodlot builds in parallel and resumably.

Each instance is built with the standard script, with FHOPS skipped and a
short AAC search. Queue statuses are updated after every instance so a crashed
run can resume without repeating completed work.

The default concurrency is memory-aware: each job is assumed to peak at about
14 GB, and the runner keeps a 24 GB reserve. Override with ``--jobs``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "queue" / "woodlot_build_queue.json"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_instance.sh"
LOG_ROOT = REPO_ROOT / "batch" / "logs"


def _read_queue() -> dict[str, object]:
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def _write_queue(payload: dict[str, object]) -> None:
    temp = QUEUE_PATH.with_suffix(".tmp")
    temp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temp.replace(QUEUE_PATH)


def _update_status(
    payload: dict[str, object],
    slug: str,
    status: str,
    notes: str,
) -> None:
    for entry in payload.get("instances", []):
        if entry.get("slug") == slug:
            entry["status"] = status
            entry["notes"] = notes
            entry["updated_at"] = datetime.now(UTC).isoformat(timespec="seconds")
            return
    raise KeyError(slug)


def _parse_time(path: Path) -> tuple[str | None, str | None]:
    if not path.exists():
        return None, None
    text = path.read_text(encoding="utf-8", errors="replace")
    elapsed = re.search(r"Elapsed \(wall clock\) time.*?:\s*([0-9:.]+)", text)
    rss = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", text)
    rss_gb = f"{int(rss.group(1)) / 1024 / 1024:.1f} GB" if rss else None
    return (elapsed.group(1) if elapsed else None), rss_gb


def _available_gb() -> float:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1024 / 1024
    except OSError:
        pass
    return 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--start-at", default=None)
    parser.add_argument("--only", action="append", default=None)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--salvage", action="store_true")
    parser.add_argument("--reset-building", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=7200)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--per-job-gb", type=float, default=14.0)
    parser.add_argument("--reserve-gb", type=float, default=24.0)
    parser.add_argument(
        "--aac-search-time",
        default="00:02:00",
        help="Passed to the build script as AAC_SEARCH_TIME",
    )
    args = parser.parse_args(argv)

    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    payload = _read_queue()
    if args.reset_building:
        for entry in payload.get("instances", []):
            if entry.get("status") == "building":
                entry["status"] = "pending"
                entry["notes"] = "reset after interrupted batch"
        _write_queue(payload)
    instances = list(payload.get("instances", []))
    if args.only:
        wanted = set(args.only)
        instances = [entry for entry in instances if entry.get("slug") in wanted]
    if args.start_at:
        slugs = [entry.get("slug") for entry in instances]
        if args.start_at in slugs:
            instances = instances[slugs.index(args.start_at) :]

    if args.salvage:
        queue = [
            entry for entry in instances if entry.get("status") == "failed"
        ]
    else:
        queue = [
            entry
            for entry in instances
            if entry.get("status") == "pending"
            or (args.retry_failed and entry.get("status") == "failed")
        ]
    if args.limit:
        queue = queue[: args.limit]
    if not queue:
        print("No instances to build.")
        return 0

    available = _available_gb()
    memory_jobs = max(1, int((available - args.reserve_gb) // args.per_job_gb))
    jobs = max(1, min(args.jobs, memory_jobs))
    print(
        f"Batch queue: {len(queue)} instances; jobs={jobs} "
        f"(available {available:.0f} GB, reserve {args.reserve_gb:.0f} GB)"
    )
    for entry in queue:
        print(f"  {entry.get('file_id')} {entry.get('slug')}")
    if args.dry_run:
        return 0

    env = dict(os.environ)
    env["SKIP_FHOPS"] = "1"
    env["AAC_SEARCH_TIME"] = args.aac_search_time
    env.setdefault("FEMIC_DISABLE_IPP", "1")
    env.setdefault("FEMIC_ALLOW_PARTIAL_BUNDLE", "1")

    lock = threading.Lock()
    completed = 0

    def run_one(entry: dict[str, object]) -> None:
        nonlocal completed
        slug = str(entry["slug"])
        instance_root = REPO_ROOT / "instances" / slug
        if not instance_root.exists():
            with lock:
                _update_status(
                    payload, slug, "failed", "instance workspace missing"
                )
                _write_queue(payload)
                print(f"{slug}: missing workspace")
            return

        with lock:
            _update_status(payload, slug, "building", f"batch job {jobs} running")
            _write_queue(payload)
            print(f"{slug}: building")

        log_path = LOG_ROOT / f"{slug}.log"
        time_path = LOG_ROOT / f"{slug}.time.log"
        started = time.monotonic()
        try:
            with log_path.open("w", encoding="utf-8") as log, time_path.open(
                "w", encoding="utf-8"
            ) as time_log:
                process = subprocess.run(
                    ["/usr/bin/time", "-v", str(BUILD_SCRIPT), slug],
                    cwd=REPO_ROOT,
                    env=env,
                    stdout=log,
                    stderr=time_log,
                    timeout=args.timeout,
                    check=False,
                )
        except subprocess.TimeoutExpired:
            with lock:
                _update_status(
                    payload, slug, "failed", f"timeout after {args.timeout}s"
                )
                _write_queue(payload)
                print(f"{slug}: timeout")
            return

        elapsed = time.monotonic() - started
        elapsed_text, rss_text = _parse_time(time_path)
        with lock:
            if process.returncode == 0:
                prefix = "partial salvage" if args.salvage else "batch built"
                notes = (
                    f"{prefix} in {elapsed_text or f'{elapsed:.0f}s'}"
                    f", peak RSS {rss_text or 'unknown'}"
                )
                _update_status(payload, slug, "built", notes)
                status = "built"
            else:
                tail = log_path.read_text(
                    encoding="utf-8", errors="replace"
                )[-800:]
                _update_status(
                    payload,
                    slug,
                    "failed",
                    f"exit {process.returncode}; see {log_path.name}; {tail[-300:]}",
                )
                status = f"failed ({process.returncode})"
            _write_queue(payload)
            completed += 1
            print(
                f"{slug}: {status} in {elapsed_text or f'{elapsed:.0f}s'}, "
                f"RSS {rss_text or 'unknown'} "
                f"[{completed}/{len(queue)}]"
            )

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = [pool.submit(run_one, entry) for entry in queue]
        for future in as_completed(futures):
            future.result()

    statuses = [entry.get("status") for entry in payload.get("instances", [])]
    built = statuses.count("built")
    failed = statuses.count("failed")
    pending = statuses.count("pending")
    print(f"Queue state: built={built} failed={failed} pending={pending}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
