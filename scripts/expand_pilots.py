#!/usr/bin/env python3
"""Generate the batch pilot selection for the remaining community forests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
COAST_TOKENS = ("Coast", "West Coast", "South Coast")
SPRUCE = {"S", "SB", "SE", "SN", "SS", "SW", "SX", "SXE", "SXL", "SXW"}
PINE = {"P", "PA", "PJ", "PL", "PLC", "PLI", "PM", "PW", "PY"}
FIR = {"B", "BA", "BB", "BG", "BL", "BM", "BP"}
LARCH = {"L", "LA", "LS", "LT", "LW"}
CEDAR = {"C", "CW", "YC"}
HEMLOCK = {"H", "HM", "HWI", "HW"}
DOUGLAS = {"F", "FD", "FDC", "FDI"}
BROADLEAF = {
    "AC", "ACB", "ACT", "AD", "AT", "AX",
    "E", "EA", "EB", "EE", "EP", "EW", "EXP",
    "W", "WA", "WB", "WD", "WP", "WS",
    "D", "V", "GP", "Q", "M", "MB", "MV",
}


def _overrides(district: str) -> dict[str, str]:
    coast = any(token.lower() in district.lower() for token in COAST_TOKENS)
    mapping: dict[str, str] = {}
    for code in SPRUCE:
        mapping[code] = "SS" if code == "SS" else "SW"
    for code in PINE:
        mapping[code] = "PLI"
    for code in DOUGLAS:
        mapping[code] = "FDC" if coast else "FDI"
    for code in FIR:
        mapping[code] = "FDC" if coast else "FDI"
    for code in LARCH:
        mapping[code] = "FDC" if coast else "FDI"
    for code in CEDAR:
        mapping[code] = "CW"
    for code in HEMLOCK:
        mapping[code] = "HWC" if coast else "HWI"
    for code in BROADLEAF:
        mapping[code] = "AT"
    mapping["DR"] = "FDC" if coast else "FDI"
    mapping["NC"] = "NC"
    return mapping


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=REPO_ROOT / "data" / "catalog" / "cfa_catalog.json",
    )
    parser.add_argument(
        "--queue",
        type=Path,
        default=REPO_ROOT / "queue" / "woodlot_build_queue.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "config" / "pilots_batch.yaml",
    )
    parser.add_argument(
        "--status",
        action="append",
        default=None,
        help="Queue status to include (default: pending, failed)",
    )
    args = parser.parse_args(argv)

    statuses = set(args.status or ["pending", "failed"])
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    wanted = {
        str(entry.get("slug"))
        for entry in queue.get("instances", [])
        if entry.get("status") in statuses
    }
    rows = [
        row
        for row in catalog.get("community_forests", [])
        if str(row.get("slug")) in wanted
    ]
    if not rows:
        raise SystemExit(f"No catalog rows match statuses {sorted(statuses)}")

    pilots = []
    for row in sorted(rows, key=lambda item: str(item.get("file_id", ""))):
        pilots.append(
            {
                "slug": row["slug"],
                "file_id": row["file_id"],
                "label": str(row.get("display_name", row["file_id"])).title(),
                "rationale": "Batch build",
                "species_code_overrides": _overrides(str(row.get("district", ""))),
            }
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        yaml.safe_dump({"pilots": pilots}, sort_keys=False), encoding="utf-8"
    )
    print(f"Wrote {len(pilots)} batch pilots to {args.out}")
    print("  " + ", ".join(pilot["file_id"] for pilot in pilots))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
