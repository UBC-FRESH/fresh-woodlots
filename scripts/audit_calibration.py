#!/usr/bin/env python3
"""Audit the population W4W calibration and flag method-check cases."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "queue" / "woodlot_build_queue.json"
OUT_MD = REPO_ROOT / "docs" / "aac" / "CALIBRATION-AUDIT.md"
OUT_CSV = REPO_ROOT / "docs" / "aac" / "CALIBRATION-AUDIT.csv"


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return ordered[index]


def classify(factor: float) -> str:
    if factor < 0.25:
        return "extreme-low"
    if factor < 0.4:
        return "low"
    if factor > 4.0:
        return "extreme-high"
    if factor > 2.0:
        return "high"
    return "ok"


def main() -> int:
    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    rows = []
    for entry in queue.get("instances", []):
        if entry.get("status") != "built":
            continue
        slug = str(entry.get("slug"))
        path = REPO_ROOT / "instances" / slug / "config" / "w4w_calibration.json"
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        case = (payload.get("cases") or {}).get("all_vri") or {}
        factor = float(case.get("thlb_factor") or 0)
        v2_path = (
            REPO_ROOT / "instances" / slug / "config" / "w4w_calibration_v2.json"
        )
        v2 = (
            json.loads(v2_path.read_text(encoding="utf-8"))
            if v2_path.is_file()
            else None
        )
        rows.append(
            {
                "file_id": payload.get("file_id"),
                "slug": slug,
                "licensee": payload.get("display_name"),
                "aac_m3": float(payload.get("published_aac_m3_per_year") or 0),
                "factor": factor,
                "net_area_ha": float(case.get("net_area_ha") or 0),
                "proxy_thlb_ha": float(payload.get("proxy_thlb_ha") or 0),
                "pct_proxy_thlb": float(case.get("netdown_vs_proxy_thlb") or 0) * 100,
                "method_class": classify(factor),
                "v2_available": bool(v2),
                "v2_factor": float(v2.get("thlb_factor") or 0) if v2 else None,
                "v2_net_area_ha": float(v2.get("net_area_ha") or 0) if v2 else None,
            }
        )
    frame = pd.DataFrame(rows).sort_values("file_id")
    frame.to_csv(OUT_CSV, index=False)
    factors = [float(value) for value in frame["factor"] if value]
    counts = frame["method_class"].value_counts().to_dict()
    method_check = int((frame["method_class"] != "ok").sum())
    within = int(
        ((frame["pct_proxy_thlb"] >= 80) & (frame["pct_proxy_thlb"] <= 120)).sum()
    )
    outliers = frame[frame["method_class"] != "ok"].copy()
    low = outliers[outliers["factor"] < 0.4].sort_values("factor").head(15)
    high = (
        outliers[outliers["factor"] > 2.0]
        .sort_values("factor", ascending=False)
        .head(15)
    )
    v2_rows = frame[frame["v2_available"]].sort_values("file_id")
    lines = [
        "# W4W calibration audit",
        "",
        "Population audit of the simplified Woodlot-for-Windows calibration. "
        "The published AAC is the target; the all-VRI model solves for one "
        "multiplicative THLB factor.",
        "",
        f"- Built instances audited: **{len(frame)}**",
        f"- Median factor: **{statistics.median(factors):.4f}**" if factors else "",
        f"- Factor range: **{min(factors):.4f}–{max(factors):.4f}**"
        if factors
        else "",
        f"- 10th–90th percentile: "
        f"**{percentile(factors, 0.10):.4f}–{percentile(factors, 0.90):.4f}**",
        f"- Within 80–120% of Proxy THLB: **{within}**",
        f"- Method-check cases (factor <0.4 or >2.0): **{method_check}**",
        "- Extreme cases (factor <0.25 or >4.0): "
        f"**{int(frame['method_class'].str.startswith('extreme').sum())}**",
        "",
        "## Decision",
        "",
        "**v1 remains the population default.** It is a clearcut/oldest-first "
        "replica and is appropriate only while a plan's silviculture system is "
        "unknown. **v2 is selected per plan** when the plan documents partial "
        "cutting or commercial thinning. The portal flags every factor outside "
        "the 0.4–2.0 range as **method check**; the factor is a calibration "
        "device, not a statutory THLB.",
        "",
        "The unresolved cases are a data problem, not a reason to mass-switch "
        "the population to v2. A mass v2 run would require a silviculture "
        "assumption for every licence, and W0026 is a documented counter-example "
        "where v2 is implausible.",
        "",
        "## Class counts",
        "",
        "| Class | Count |",
        "|---|---:|",
    ]
    for name in ("ok", "low", "high", "extreme-low", "extreme-high"):
        lines.append(f"| {name} | {int(counts.get(name, 0))} |")
    lines += [
        "",
        "## Lowest factors",
        "",
        "| File | Licence | Factor | Net ha | % Proxy THLB | Class |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in low.itertuples(index=False):
        lines.append(
            f"| {row.file_id} | {row.licensee} | {row.factor:.4f} | "
            f"{row.net_area_ha:,.1f} | {row.pct_proxy_thlb:.1f}% | {row.method_class} |"
        )
    lines += [
        "",
        "## Highest factors",
        "",
        "| File | Licence | Factor | Net ha | % Proxy THLB | Class |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in high.itertuples(index=False):
        lines.append(
            f"| {row.file_id} | {row.licensee} | {row.factor:.4f} | "
            f"{row.net_area_ha:,.1f} | {row.pct_proxy_thlb:.1f}% | {row.method_class} |"
        )
    lines += [
        "",
        "## v2 cases",
        "",
        "| File | Licence | v1 factor | v1 net ha | v2 factor | v2 net ha |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in v2_rows.itertuples(index=False):
        lines.append(
            f"| {row.file_id} | {row.licensee} | {row.factor:.4f} | "
            f"{row.net_area_ha:,.1f} | {row.v2_factor:.4f} | "
            f"{row.v2_net_area_ha:,.1f} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- Factors below 0.4 usually mean the clearcut model overestimates "
        "sustainable yield for the published AAC, often because the plan uses "
        "partial cutting, has a high non-timber constraint, or has a small AAC.",
        "- Factors above 2.0 usually mean the public VRI fragment/yield curve "
        "underestimates the local land base or the AAC includes area not in the "
        "compiled fragments.",
        "- Do not interpret either tail as a THLB estimate without the local "
        "management plan.",
        "",
        f"Full CSV: [`{OUT_CSV.name}`]({OUT_CSV.name}).",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT_MD} ({len(frame)} rows, {method_check} method-check)")
    print(f"wrote {OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
