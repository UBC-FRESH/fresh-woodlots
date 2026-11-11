#!/usr/bin/env python3
"""Synchronise the build queue with the instance artefacts on disk.

Useful after a single-instance build, or after a batch that was interrupted
before it could record the final status.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "queue" / "woodlot_build_queue.json"


def _read_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=QUEUE_PATH)
    args = parser.parse_args(argv)

    payload = json.loads(args.queue.read_text(encoding="utf-8"))
    changed = 0
    for entry in payload.get("instances", []):
        slug = str(entry.get("slug"))
        root = REPO_ROOT / "instances" / slug
        if entry.get("status") == "pending_aac":
            continue
        compiled = root / "ws4" / "build" / "compiled" / "manifest.json"
        baseline = root / "ws4" / "runs" / "aac_baseline"
        if not compiled.is_file() or not baseline.is_dir():
            continue
        if entry.get("status") != "built":
            entry["status"] = "built"
            entry["notes"] = "built and synced from disk"
            entry["updated_at"] = datetime.now(UTC).isoformat(timespec="seconds")
            changed += 1
        fhops = root / "fhops" / "summary.json"
        if fhops.is_file():
            entry["fhops"] = {
                "status": "built",
                "summary": _read_json(fhops),
            }
    args.queue.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"queue synced: {changed} status changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
