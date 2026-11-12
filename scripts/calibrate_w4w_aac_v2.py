#!/usr/bin/env python3
"""Calibrate a partial-cut W4W-style AAC for one woodlot (v2)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from calibrate_w4w_aac import QUEUE_PATH, REPO_ROOT, load_blocks

AAC_AREA = 1110.0
AOI = 1027.92
PROXY_THLB = 667.38


def simulate_partial(
    blocks,
    target_m3_per_year: float,
    *,
    horizon: int = 250,
    width: int = 5,
    min_age: int = 80,
    removal: float = 0.30,
    reentry: int = 20,
    pcaf: float = 0.65,
    min_volume: float = 50.0,
) -> bool:
    if target_m3_per_year <= 0:
        return True
    ages = np.array([block.age for block in blocks], dtype=float)
    areas = np.array([block.area_ha for block in blocks], dtype=float)
    residual = np.ones(len(blocks), dtype=float)
    last_entry = np.full(len(blocks), -1e9, dtype=float)
    target = target_m3_per_year * width
    for period in range(horizon // width):
        year = period * width
        available = np.where(
            (ages >= min_age) & ((year - last_entry) >= reentry)
        )[0]
        if available.size == 0:
            return False
        volumes = {
            int(index): areas[index]
            * residual[index]
            * pcaf
            * blocks[index].volume_per_ha(ages[index])
            for index in available
        }
        available = [
            int(index)
            for index in available
            if volumes[int(index)] / areas[int(index)] >= min_volume
        ]
        if not available:
            return False
        harvested = 0.0
        for index in sorted(available, key=lambda item: -ages[item]):
            harvested += removal * volumes[index]
            residual[index] *= 1.0 - removal
            last_entry[index] = year
            if harvested >= target:
                break
        if harvested < target:
            return False
        ages += width
    return True


def max_even_flow(blocks, **kwargs) -> float:
    total_area = sum(block.area_ha for block in blocks)
    upper = max(
        1.0,
        total_area * max(float(block.y[-1]) for block in blocks) / 5,
    )
    low, high = 0.0, upper
    for _ in range(50):
        mid = (low + high) / 2
        if simulate_partial(blocks, mid, **kwargs):
            low = mid
        else:
            high = mid
    return low


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--instance-root", type=Path, default=None)
    parser.add_argument("--horizon", type=int, default=250)
    parser.add_argument("--width", type=int, default=5)
    parser.add_argument("--min-age", type=int, default=80)
    parser.add_argument("--removal", type=float, default=0.30)
    parser.add_argument("--reentry", type=int, default=20)
    parser.add_argument("--pcaf", type=float, default=0.65)
    parser.add_argument("--min-volume", type=float, default=50.0)
    parser.add_argument("--write-docs", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    payload = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    entry = next(
        (item for item in payload.get("instances", []) if item.get("slug") == args.slug),
        None,
    )
    if entry is None:
        raise SystemExit(f"slug not in queue: {args.slug}")
    root = args.instance_root or (REPO_ROOT / "instances" / args.slug)
    compiled = root / "ws4" / "build" / "compiled"
    aac = float(entry.get("aac_m3") or 0)
    if aac <= 0:
        raise SystemExit(f"no positive AAC for {args.slug}")
    aac_area = float(entry.get("aac_area_ha") or 0)
    aoi = float(entry.get("area_ha") or 0)
    thlb_summary = root / "data" / "source" / "thlb" / "thlb.summary.json"
    proxy_thlb = 0.0
    if thlb_summary.is_file():
        proxy_thlb = float(json.loads(thlb_summary.read_text()).get("thlb_ha") or 0)

    blocks = load_blocks(compiled, include_unmanaged=True)
    gross = float(sum(block.area_ha for block in blocks))
    vmax = max_even_flow(
        blocks,
        horizon=args.horizon,
        width=args.width,
        min_age=args.min_age,
        removal=args.removal,
        reentry=args.reentry,
        pcaf=args.pcaf,
        min_volume=args.min_volume,
    )
    factor = aac / vmax if vmax > 0 else float("nan")
    net = factor * gross
    result = {
        "schema_version": 2,
        "slug": args.slug,
        "file_id": entry.get("file_id"),
        "display_name": entry.get("display_name"),
        "kind": "partial_cut",
        "published_aac_m3_per_year": aac,
        "aac_area_ha": aac_area,
        "aoi_ha": aoi,
        "proxy_thlb_ha": proxy_thlb,
        "gross_vri_fragment_ha": round(gross, 2),
        "assumptions": {
            "horizon_years": args.horizon,
            "period_width_years": args.width,
            "minimum_harvest_age": args.min_age,
            "removal_fraction": args.removal,
            "reentry_years": args.reentry,
            "pcaf": args.pcaf,
            "min_volume_m3_per_ha": args.min_volume,
            "harvest_rule": "oldest-first; partial volume removal; residual stand grows",
        },
        "max_even_flow_m3_per_year": round(vmax, 1),
        "thlb_factor": round(factor, 4),
        "net_area_ha": round(net, 2),
        "netdown_vs_aac_area": round(net / aac_area, 4) if aac_area else None,
        "netdown_vs_aoi": round(net / aoi, 4) if aoi else None,
        "netdown_vs_proxy_thlb": round(net / proxy_thlb, 4) if proxy_thlb else None,
        "netdown_vs_gross_vri": round(net / gross, 4) if gross else None,
    }
    out = args.out or (root / "config")
    out.mkdir(parents=True, exist_ok=True)
    (out / "w4w_calibration_v2.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    rows = []
    for block in blocks:
        rows.append(
            {
                "block_id": block.block_id,
                "track_id": block.track_id,
                "area_ha": round(block.area_ha, 4),
                "age": block.age,
                "curve_id": block.curve_id,
                "calibrated_thlb_factor": factor,
                "calibrated_net_area_ha": round(block.area_ha * factor, 4),
            }
        )
    pd.DataFrame(rows).to_csv(out / "w4w_plausible_inputs_v2.csv", index=False)
    if args.write_docs:
        (out / "W4W-CALIBRATION-V2.md").write_text(
            "\n".join(
                [
                    f"# {args.slug} — partial-cut W4W calibration v2",
                    "",
                    f"Published AAC: **{aac:,.0f} m³/year**.",
                    "",
                    "| Input | Value |",
                    "|---|---:|",
                    f"| Gross VRI fragments | {gross:,.2f} ha |",
                    f"| Minimum harvest age | {args.min_age} years |",
                    f"| Removal per entry | {args.removal:.0%} |",
                    f"| Re-entry period | {args.reentry} years |",
                    f"| Effective PCAF/yield factor | {args.pcaf:.2f} |",
                    f"| Max even flow at factor 1.0 | {vmax:,.1f} m³/yr |",
                    f"| Calibrated THLB factor | {factor:.4f} |",
                    f"| Calibrated net area | {net:,.2f} ha |",
                    f"| Net area vs Proxy THLB | {(net / proxy_thlb if proxy_thlb else 0):.1%} |",
                    "",
                    "This is a simplified partial-cut replica. It models residual "
                    "stand growth, 30% volume removal, 20-year re-entry, and an "
                    "effective yield factor that absorbs full-cycle-tree and road "
                    "netdowns. It is not a statutory AAC calculation.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"Wrote {out / 'w4w_calibration_v2.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
