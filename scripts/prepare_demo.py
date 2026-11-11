#!/usr/bin/env python3
"""Prepare the demo surfaces for every built woodlot instance.

- archives the old ``pre_*`` runs so the WS4 UI opens the current AAC baseline
- writes three saved target scenarios: baseline, high, and conservative
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "queue" / "woodlot_build_queue.json"


def _scenario_payload(targets: list[dict[str, object]]) -> dict[str, object]:
    return {"targets": targets}


def _write_scenario(
    *,
    root: Path,
    slug: str,
    name: str,
    description: str,
    targets: list[dict[str, object]],
    now: str,
) -> None:
    directory = root / slug
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "targets.yaml").write_text(
        yaml.safe_dump(_scenario_payload(targets), sort_keys=False),
        encoding="utf-8",
    )
    (directory / "scenario.json").write_text(
        json.dumps(
            {
                "name": name,
                "description": description,
                "created_utc": now,
                "target_count": len(targets),
                "source": "public AAC band",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _scale(
    targets: list[dict[str, object]], low: float, high: float
) -> list[dict[str, object]]:
    scaled: list[dict[str, object]] = []
    for row in targets:
        item = dict(row)
        for key in ("minimum", "maximum"):
            value = item.get(key)
            if isinstance(value, (int, float)):
                factor = low if key == "minimum" else high
                item[key] = round(float(value) * factor, 1)
        scaled.append(item)
    return scaled


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=QUEUE_PATH)
    parser.add_argument("--only", action="append", default=None)
    args = parser.parse_args(argv)

    payload = json.loads(args.queue.read_text(encoding="utf-8"))
    wanted = set(args.only) if args.only else None
    now = datetime.now(UTC).isoformat(timespec="seconds")
    processed = 0
    archived = 0

    for entry in payload.get("instances", []):
        root = REPO_ROOT / "instances" / str(entry["slug"])
        if entry.get("status") not in ("built", "pilot_built") and not (
            root / "ws4" / "runs" / "aac_baseline"
        ).is_dir():
            continue
        slug = str(entry["slug"])
        if wanted is not None and slug not in wanted:
            continue
        runs = root / "ws4" / "runs"
        baseline = root / "config" / "targets" / "evenflow_aac.yaml"
        if not runs.is_dir() or not baseline.is_file():
            print(f"skip {slug}: missing runs or baseline targets")
            continue

        archive = runs / "archive"
        for path in sorted(runs.iterdir()):
            if path.is_dir() and path.name.startswith("pre_"):
                archive.mkdir(parents=True, exist_ok=True)
                destination = archive / path.name
                if destination.exists():
                    shutil.rmtree(destination)
                path.rename(destination)
                archived += 1

        document = yaml.safe_load(baseline.read_text(encoding="utf-8")) or {}
        targets = document.get("targets") or []
        if not isinstance(targets, list) or not targets:
            print(f"skip {slug}: baseline targets are empty")
            continue

        scenarios = runs / "scenarios"
        _write_scenario(
            root=scenarios,
            slug="baseline",
            name="AAC baseline (1.2x)",
            description="The public AAC band used for the 100-year baseline.",
            targets=targets,
            now=now,
        )
        _write_scenario(
            root=scenarios,
            slug="high",
            name="Higher harvest (1.5-2x)",
            description="A stress test with a higher floor and ceiling.",
            targets=_scale(targets, 1.5, 2.0),
            now=now,
        )
        _write_scenario(
            root=scenarios,
            slug="conservative",
            name="Conservative harvest (0.5-0.8x)",
            description="A lower-pressure scenario for comparison.",
            targets=_scale(targets, 0.5, 0.8),
            now=now,
        )
        processed += 1
        print(f"prepared {slug}")

    print(f"prepared {processed} instances; archived {archived} old runs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
