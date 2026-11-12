#!/usr/bin/env python3
"""Rebuild selected FHOPS first-period pilots with all WS4 blocks.

This is the remediation path for pilots whose compressed block selection has
an implausible period-volume / selected-area ratio. The scenario still uses
the original fixed daily rate and compressed horizon; only the candidate block
pool changes.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import geopandas as gpd

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "queue" / "woodlot_build_queue.json"
LOG_ROOT = REPO_ROOT / "batch" / "fhops_allblocks"
SUPPORT_PATHS = [
    Path("/srv/shared-data/gep/ws4/fhops-ground-support"),
    Path("/srv/shared-data/gep/ws4/fhops-ground-support/src"),
]
BUILD_SCENARIO = REPO_ROOT / "scripts" / "build_fhops_pilot.py"


def _env() -> dict[str, str]:
    env = dict(os.environ)
    paths = [str(path) for path in SUPPORT_PATHS if path.is_dir()]
    current = env.get("PYTHONPATH")
    if current:
        paths.append(current)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env


def _kpi(text: str, name: str) -> float | None:
    match = re.search(rf"{name}:\s*([0-9.]+)", text)
    return float(match.group(1)) if match else None


def _run(
    command: list[str],
    *,
    cwd: Path,
    log,
    timeout: int,
) -> int:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=_env(),
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )
    return result.returncode


def rebuild(root: Path, entry: dict[str, object], timeout: int) -> bool:
    slug = root.name
    fhops = root / "fhops"
    backup = root / "fhops_before_allblocks"
    if fhops.is_dir() and not backup.exists():
        shutil.copytree(fhops, backup)
    geometry_path = root / "ws4" / "geometry" / "blocks.geojson"
    if not geometry_path.is_file():
        print(f"{slug}: no WS4 block geometry")
        return False
    geometry = gpd.read_file(geometry_path)
    block_ids = sorted(
        int(value)
        for value in geometry.loc[
            geometry["area_ha"].astype(float) > 0, "block_id"
        ].unique()
    )
    if not block_ids:
        print(f"{slug}: no positive-area blocks")
        return False
    aac = float(entry.get("aac_m3") or 0)
    if aac <= 0:
        print(f"{slug}: no AAC")
        return False
    volume = aac * 10.0
    rate = max(250.0, math.ceil(volume / 180.0))
    days = max(450, math.ceil(volume / rate) * 2 + 60)
    log_path = LOG_ROOT / f"{slug}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with log_path.open("w", encoding="utf-8") as log:
        build = _run(
            [
                sys.executable,
                str(BUILD_SCENARIO),
                "--instance-root",
                str(root),
                "--aac",
                str(aac),
                "--daily-rate",
                str(rate),
                "--days",
                str(days),
                "--block-ids",
                ",".join(str(value) for value in block_ids),
            ],
            cwd=REPO_ROOT,
            log=log,
            timeout=timeout,
        )
        if build != 0:
            print(f"{slug}: scenario build failed; see {log_path}")
            return False
        if _run(
            [sys.executable, "-m", "fhops.cli.main", "validate", "scenario.yaml"],
            cwd=fhops,
            log=log,
            timeout=timeout,
        ):
            print(f"{slug}: validate failed; see {log_path}")
            return False
        (fhops / "out").mkdir(exist_ok=True)
        if _run(
            [
                sys.executable,
                "-m",
                "fhops.cli.main",
                "solve-heur",
                "scenario.yaml",
                "--out",
                "out/heur_solution.csv",
            ],
            cwd=fhops,
            log=log,
            timeout=timeout,
        ):
            print(f"{slug}: solve failed; see {log_path}")
            return False
        evaluate = subprocess.run(
            [
                sys.executable,
                "-m",
                "fhops.cli.main",
                "evaluate",
                "scenario.yaml",
                "--assignments",
                "out/heur_solution.csv",
            ],
            cwd=fhops,
            env=_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
        log.write(evaluate.stdout)
        if evaluate.returncode != 0:
            print(f"{slug}: evaluate failed; see {log_path}")
            return False
        summary = {
            "schema_version": 1,
            "aac_m3": aac,
            "rate_m3_per_day": rate,
            "horizon_days": days,
            "total_production_m3": _kpi(evaluate.stdout, "total_production"),
            "completed_blocks": _kpi(evaluate.stdout, "completed_blocks"),
            "makespan_day": _kpi(evaluate.stdout, "makespan_day"),
            "sequencing_violation_count": _kpi(
                evaluate.stdout, "sequencing_violation_count"
            ),
            "elapsed_sec": round(time.monotonic() - started, 1),
            "block_pool": "all_ws4_blocks",
            "candidate_block_count": len(block_ids),
        }
        (fhops / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(
        f"{slug}: rebuilt {len(block_ids)} candidate blocks, "
        f"{summary['completed_blocks']} completed, "
        f"{summary['total_production_m3']} m³, "
        f"{summary['elapsed_sec']} s"
    )
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=QUEUE_PATH)
    parser.add_argument("--only", action="append", default=None)
    parser.add_argument("--timeout", type=int, default=3600)
    args = parser.parse_args(argv)
    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    wanted = set(args.only) if args.only else None
    entries = [
        entry
        for entry in queue.get("instances", [])
        if entry.get("status") == "built"
        and entry.get("aac_m3")
        and (wanted is None or entry.get("slug") in wanted)
    ]
    if wanted:
        missing = wanted - {str(entry.get("slug")) for entry in entries}
        if missing:
            raise SystemExit(f"unknown or unbuilt slugs: {sorted(missing)}")
    ok = 0
    failed = 0
    for entry in entries:
        slug = str(entry["slug"])
        if rebuild(REPO_ROOT / "instances" / slug, entry, args.timeout):
            ok += 1
        else:
            failed += 1
    print(f"all-block FHOPS rebuild: ok={ok} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
