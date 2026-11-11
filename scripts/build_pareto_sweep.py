#!/usr/bin/env python3
"""Pre-compute an AAC-band Pareto sweep for selected community forests.

The WS4 portfolio tool varies target *weights*. For a public demo we need
different target *levels* so the cloud has real trade-offs. This script runs
the optimizer over a small grid of AAC multipliers and seeds, then writes a
``portfolio.json`` that the existing Pareto tab already knows how to load.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "queue" / "woodlot_build_queue.json"
WS4_ROOT = Path("/srv/shared-data/gep/ws4/ws4-public-demo")
FACTORS = (0.70, 0.85, 1.00, 1.15, 1.30)
SEEDS = (1, 2)
METRIC_ACCOUNTS = (
    "product.HarvestedVolume.managed.Total.CC@sum",
    "feature.Area.og1.total@end",
    "product.HarvestedVolume.managed.CW.CC@sum",
    "product.HarvestedVolume.managed.HW.CC@sum",
)


def _available_metrics(root: Path) -> list[str]:
    path = root / "ws4" / "runs" / "aac_baseline" / "account_values.csv"
    frame = pd.read_csv(path)
    accounts = set(frame["account"].astype(str))
    metrics = []
    for metric in METRIC_ACCOUNTS:
        account = metric.split("@", 1)[0]
        if account in accounts:
            metrics.append(metric)
    return metrics


def _scaled_targets(source: Path, destination: Path, factor: float) -> None:
    document = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    for target in document.get("targets", []):
        for key in ("minimum", "maximum"):
            value = target.get(key)
            if isinstance(value, (int, float)):
                target[key] = round(float(value) * factor, 3)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )


def _run_member(
    root: Path,
    portfolio: Path,
    label: str,
    target_path: Path,
    seed: int,
    iterations: int,
) -> dict[str, object]:
    run_dir = portfolio / "members" / label
    run_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "ws4.cli",
        "optimize",
        "--dataset",
        str(root / "ws4" / "build" / "compiled"),
        "--targets",
        str(target_path),
        "--out",
        str(run_dir),
        "--initial-schedule",
        str(root / "ws4" / "runs" / "aac_baseline" / "schedule.csv"),
        "--iterations",
        str(iterations),
        "--years",
        "100",
        "--seed",
        str(seed),
        "--threads",
        "2",
        "--time-limit",
        "00:05:00",
    ]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(WS4_ROOT) + os.pathsep + environment.get(
        "PYTHONPATH", ""
    )
    result = subprocess.run(
        command,
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=900,
    )
    summary_path = run_dir / "summary.json"
    summary = {}
    if summary_path.is_file():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            summary = {}
    return {
        "run_dir": run_dir,
        "returncode": result.returncode,
        "summary": summary,
        "log": (result.stdout + result.stderr)[-4000:],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=QUEUE_PATH)
    parser.add_argument("--only", action="append", default=None)
    parser.add_argument("--factors", default="0.70,0.85,1.00,1.15,1.30")
    parser.add_argument("--seeds", default="1,2")
    parser.add_argument("--iterations", type=int, default=60)
    args = parser.parse_args(argv)

    factors = tuple(float(item) for item in args.factors.split(",") if item.strip())
    seeds = tuple(int(item) for item in args.seeds.split(",") if item.strip())
    payload = json.loads(args.queue.read_text(encoding="utf-8"))
    wanted = set(args.only) if args.only else None
    selected = []
    for entry in payload.get("instances", []):
        if entry.get("status") not in ("built", "pilot_built"):
            continue
        slug = str(entry["slug"])
        if wanted is not None and slug not in wanted:
            continue
        selected.append(slug)

    sys.path.insert(0, str(WS4_ROOT))
    from ws4.opt.portfolio import metrics_from_run
    from ws4.opt.solution_space import build_solution_space

    for slug in selected:
        root = REPO_ROOT / "instances" / slug
        base_targets = root / "config" / "targets" / "evenflow_aac.yaml"
        if not base_targets.is_file():
            print(f"{slug}: no base targets")
            continue
        metrics = _available_metrics(root)
        if not metrics:
            print(f"{slug}: no metrics")
            continue
        portfolio = root / "ws4" / "runs" / "pareto_sweep"
        if portfolio.exists():
            shutil.rmtree(portfolio)
        portfolio.mkdir(parents=True, exist_ok=True)
        members: list[dict[str, object]] = []
        for factor in factors:
            for seed in seeds:
                label = f"aac-{int(round(factor * 100)):03d}-s{seed}"
                member_dir = portfolio / "members" / label
                target_path = member_dir / "targets.yaml"
                _scaled_targets(base_targets, target_path, factor)
                print(f"{slug}: {label} f={factor:.2f} seed={seed}")
                result = _run_member(
                    root, portfolio, label, target_path, seed, args.iterations
                )
                summary = result["summary"]
                status = "ok" if result["returncode"] == 0 and summary else "failed"
                member: dict[str, object] = {
                    "label": label,
                    "seed": seed,
                    "factors": {"aac_factor": factor},
                    "targets": str(target_path.relative_to(portfolio)),
                    "run_dir": str(result["run_dir"].relative_to(portfolio)),
                    "schedule": str(
                        (result["run_dir"] / "schedule.csv").relative_to(portfolio)
                    ),
                    "objective": summary.get("incumbent_objective"),
                    "metrics": {},
                    "status": status,
                    "error": "" if status == "ok" else result["log"][-800:],
                }
                if status == "ok":
                    try:
                        member["metrics"] = metrics_from_run(
                            result["run_dir"], metrics
                        )
                    except Exception as error:  # pragma: no cover - defensive
                        member["status"] = "failed"
                        member["error"] = str(error)
                members.append(member)
                if member["status"] != "ok":
                    print(f"{slug}: {label} failed: {str(member['error'])[-200:]}")

        document: dict[str, object] = {
            "schema_version": 1,
            "kind": "portfolio",
            "name": "AAC-band Pareto sweep",
            "notes": (
                "Pre-computed AAC target-level sweep for the public demo. "
                "Each member scales the published AAC band by a factor and "
                "uses a fixed seed. Finite sample, not a certified optimum."
            ),
            "metrics": metrics,
            "directions": {metric: "max" for metric in metrics}
            | {"objective": "min"},
            "members": members,
            "failures": sum(
                1 for member in members if member["status"] != "ok"
            ),
        }
        space = build_solution_space(document)
        document["front"] = space["front"]
        document["outcome_front"] = space["front"]
        document["outcome_front_size"] = space["front_size"]
        (portfolio / "portfolio.json").write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        point_count = len(space["points"])
        print(
            f"{slug}: portfolio {point_count} points, "
            f"front {space['front_size']}, failures {document['failures']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
