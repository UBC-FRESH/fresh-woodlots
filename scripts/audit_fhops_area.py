#!/usr/bin/env python3
"""Audit FHOPS volume against the selected scheduled-block area.

The first-period FHOPS pilots compress ten years of AAC into a short
horizon. That makes volume per selected hectare a useful screening check:
a very high value usually means too little block area was selected.
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "queue" / "woodlot_build_queue.json"
OUT_MD = REPO_ROOT / "docs" / "FHOPS-AREA-AUDIT.md"
OUT_CSV = REPO_ROOT / "docs" / "FHOPS-AREA-AUDIT.csv"
CHECK_THRESHOLD = 1000.0
EXTREME_THRESHOLD = 5000.0


def area_check(value: float | None) -> tuple[str, str]:
    if value is None:
        return "missing", "selected block area is missing or zero"
    if value > EXTREME_THRESHOLD:
        return "extreme", "volume per selected hectare is extreme"
    if value > CHECK_THRESHOLD:
        return "check", "volume per selected hectare is high"
    return "ok", ""


def main() -> int:
    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    rows = []
    for entry in queue.get("instances", []):
        if entry.get("status") != "built":
            continue
        slug = str(entry.get("slug"))
        root = REPO_ROOT / "instances" / slug
        summary_path = root / "fhops" / "summary.json"
        geometry_path = root / "fhops" / "out" / "scheduled_blocks.geojson"
        if not summary_path.is_file():
            continue
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        volume = float(summary.get("total_production_m3") or 0)
        area = 0.0
        feature_count = 0
        if geometry_path.is_file():
            try:
                geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
                features = geometry.get("features", [])
                feature_count = len(features)
                area = sum(
                    float(feature.get("properties", {}).get("area_ha") or 0)
                    for feature in features
                )
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                area = 0.0
        value = volume / area if area > 0 else None
        status, note = area_check(value)
        summary["selected_area_ha"] = round(area, 2)
        summary["period_volume_per_ha"] = round(value, 1) if value else None
        summary["area_check"] = status
        summary["area_check_note"] = note
        summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        rows.append(
            {
                "file_id": entry.get("file_id") or summary.get("file_id") or "",
                "slug": slug,
                "plan_kind": summary.get("plan_kind") or "first_period",
                "blocks": feature_count,
                "selected_area_ha": round(area, 2),
                "total_production_m3": round(volume, 1),
                "period_volume_per_ha": round(value, 1) if value else "",
                "area_check": status,
                "note": note,
            }
        )

    rows.sort(key=lambda item: str(item["file_id"]))
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    values = [
        float(item["period_volume_per_ha"])
        for item in rows
        if item["period_volume_per_ha"] != ""
    ]
    counts = {
        status: sum(1 for item in rows if item["area_check"] == status)
        for status in ("ok", "check", "extreme", "missing")
    }
    lines = [
        "# FHOPS selected-area audit",
        "",
        "The first-period FHOPS pilots compress ten years of AAC into a short "
        "horizon. Volume per selected scheduled hectare is a screening check, "
        "not a yield-table validation.",
        "",
        f"- Instances audited: **{len(rows)}**",
        f"- Median volume / selected ha: **{statistics.median(values):.1f} m³/ha**"
        if values
        else "",
        f"- 90th percentile: **{percentile(values, 0.90):.1f} m³/ha**"
        if values
        else "",
        f"- Check (> {CHECK_THRESHOLD:,.0f} m³/ha): **{counts['check']}**",
        f"- Extreme (> {EXTREME_THRESHOLD:,.0f} m³/ha): **{counts['extreme']}**",
        f"- Missing/zero selected area: **{counts['missing']}**",
        "",
        "## Interpretation",
        "",
        "A high value normally means the compressed pilot selected too little "
        "block area for the volume assigned to it. It is not evidence that the "
        "woodlot has that yield. Featured tactical plans now draw from all "
        "compiled WS4 blocks and generally sit near 90–120 m³/ha for the "
        "ten-year volume.",
        "",
        "The portal labels `check`, `extreme`, and `missing` cases as "
        "**⚠ area check**. The label is a prompt to inspect the block "
        "selection, not a conclusion about the woodlot.",
        "",
        "## Highest values",
        "",
        "| File | Plan | Blocks | Selected ha | 10-yr volume | m³/ha | Check |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in sorted(
        rows, key=lambda item: float(item["period_volume_per_ha"] or 0), reverse=True
    )[:25]:
        lines.append(
            f"| {row['file_id']} | {row['plan_kind']} | {row['blocks']} | "
            f"{row['selected_area_ha']:,.2f} | "
            f"{row['total_production_m3']:,.0f} | "
            f"{row['period_volume_per_ha'] or '—'} | {row['area_check']} |"
        )
    lines += [
        "",
        "## Class counts",
        "",
        "| Class | Count |",
        "|---|---:|",
        f"| ok | {counts['ok']} |",
        f"| check | {counts['check']} |",
        f"| extreme | {counts['extreme']} |",
        f"| missing | {counts['missing']} |",
        "",
        f"Full CSV: [`{OUT_CSV.name}`]({OUT_CSV.name}).",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT_MD} ({len(rows)} rows)")
    print(f"wrote {OUT_CSV}")
    print(
        f"check={counts['check']} extreme={counts['extreme']} "
        f"missing={counts['missing']}"
    )
    return 0


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return ordered[index]


if __name__ == "__main__":
    raise SystemExit(main())
