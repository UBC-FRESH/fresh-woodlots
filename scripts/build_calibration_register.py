#!/usr/bin/env python3
"""Build the master W4W calibration register from per-instance JSON files."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "queue" / "woodlot_build_queue.json"
OUT_MD = REPO_ROOT / "docs" / "aac" / "CALIBRATION-REGISTER.md"
OUT_CSV = REPO_ROOT / "docs" / "aac" / "CALIBRATION-REGISTER.csv"


def main() -> int:
    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    rows = []
    for entry in queue.get("instances", []):
        slug = str(entry.get("slug"))
        path = REPO_ROOT / "instances" / slug / "config" / "w4w_calibration.json"
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        case = (payload.get("cases") or {}).get("all_vri")
        if not case:
            continue
        rows.append(
            {
                "file_id": payload.get("file_id"),
                "slug": slug,
                "licensee": payload.get("display_name"),
                "aac_m3": round(float(payload.get("published_aac_m3_per_year") or 0), 1),
                "gross_vri_ha": round(float(payload.get("gross_vri_fragment_ha") or 0), 1),
                "vmax_m3": round(float(case.get("max_even_flow_m3_per_year") or 0), 1),
                "thlb_factor": round(float(case.get("thlb_factor") or 0), 4),
                "net_area_ha": round(float(case.get("net_area_ha") or 0), 1),
                "pct_aac_area": round(float(case.get("netdown_vs_aac_area") or 0) * 100, 1),
                "pct_aoi": round(float(case.get("netdown_vs_aoi") or 0) * 100, 1),
                "pct_proxy_thlb": round(float(case.get("netdown_vs_proxy_thlb") or 0) * 100, 1),
                "pct_gross_vri": round(float(case.get("netdown_vs_gross_vri") or 0) * 100, 1),
            }
        )
    frame = pd.DataFrame(rows).sort_values("file_id")
    frame.to_csv(OUT_CSV, index=False)
    factors = [float(value) for value in frame["thlb_factor"] if value]
    ratios = [float(value) for value in frame["pct_proxy_thlb"] if value]
    lines = [
        "# W4W calibration register",
        "",
        "Per-woodlot calibration of the simplified Woodlot-for-Windows replica. "
        "The published AAC is the target; the all-VRI model solves for a single "
        "multiplicative THLB factor.",
        "",
        f"- Instances calibrated: **{len(frame)}**",
        f"- Median THLB factor: **{statistics.median(factors):.4f}**" if factors else "",
        f"- Median net area / Proxy THLB: **{statistics.median(ratios):.1f}%**" if ratios else "",
        f"- Within 80–120% of Proxy THLB: **{sum(80 <= value <= 120 for value in ratios)}**",
        "",
        "## Method",
        "",
        "Oldest-first priority queue; 250-year constant non-declining even flow; "
        "5-year periods; minimum harvest age 40; clearcut/regrowth; WS4 compiled "
        "managed/unmanaged yield curves. The factor absorbs partial cutting, "
        "private land, and other W4W differences. This is a calibration, not a "
        "statutory AAC calculation.",
        "",
        "The full CSV is in [`CALIBRATION-REGISTER.csv`](CALIBRATION-REGISTER.csv).",
        "",
        "| File | Licence | AAC m³/yr | Gross VRI ha | Vmax m³/yr | Factor | Net ha | % AAC area | % AOI | % Proxy THLB | % Gross VRI |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in frame.itertuples(index=False):
        lines.append(
            f"| {row.file_id} | {row.licensee} | {row.aac_m3:,.0f} | "
            f"{row.gross_vri_ha:,.1f} | {row.vmax_m3:,.1f} | "
            f"{row.thlb_factor:.4f} | {row.net_area_ha:,.1f} | "
            f"{row.pct_aac_area:.1f}% | {row.pct_aoi:.1f}% | "
            f"{row.pct_proxy_thlb:.1f}% | {row.pct_gross_vri:.1f}% |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT_MD} ({len(frame)} rows)")
    print(f"wrote {OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
