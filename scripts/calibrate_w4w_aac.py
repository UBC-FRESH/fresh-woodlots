#!/usr/bin/env python3
"""Calibrate a simplified Woodlot-for-Windows-style AAC for W0026.

The model is deliberately simple and transparent:

- one stand per WS4 fragment (managed or unmanaged curve as available);
- oldest-first priority queue;
- 250-year constant (non-declining even-flow) harvest target;
- clearcut/regrowth with a minimum harvest age;
- a single multiplicative THLB factor.

The published W0026 AAC is 7,311 m3/year. We solve for the THLB factor that
makes the simplified model produce that rate, and report the implied net area
against the public areas.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTANCE = REPO_ROOT / "instances" / "wl-w0026"
COMPILED = INSTANCE / "ws4" / "build" / "compiled"
AAC = 7311.0
AAC_AREA = 1110.0
AOI = 1027.92
PROXY_THLB = 667.38
GROSS_VRI = 732.48


@dataclass
class Block:
    block_id: int
    track_id: int
    area_ha: float
    age: float
    curve_id: int
    x: np.ndarray
    y: np.ndarray

    def volume_per_ha(self, age: float) -> float:
        return float(np.interp(age, self.x, self.y, left=0.0, right=float(self.y[-1])))


def load_blocks(include_unmanaged: bool = True) -> list[Block]:
    fragments = pd.read_parquet(COMPILED / "fragments.parquet")
    features = pd.read_parquet(COMPILED / "features.parquet")
    curves = pd.read_parquet(COMPILED / "curves.parquet")
    managed = (
        features[features["label"] == "feature.Yield.managed.Total"]
        .drop_duplicates("track_id")
        .set_index("track_id")["curve_id"]
        .to_dict()
    )
    unmanaged = (
        features[features["label"] == "feature.Yield.unmanaged.Total"]
        .drop_duplicates("track_id")
        .set_index("track_id")["curve_id"]
        .to_dict()
    )
    curve_lookup = {
        int(curve_id): group.sort_values("x")[["x", "y"]]
        for curve_id, group in curves.groupby("curve_id")
    }
    blocks: list[Block] = []
    for row in fragments.itertuples():
        track = int(row.track_id)
        curve_id = managed.get(track) if track in managed else unmanaged.get(track)
        if curve_id is None:
            continue
        if not include_unmanaged and track not in managed:
            continue
        curve = curve_lookup[int(curve_id)]
        blocks.append(
            Block(
                block_id=int(row.block_id),
                track_id=track,
                area_ha=float(row.area_ha),
                age=float(row.age),
                curve_id=int(curve_id),
                x=curve["x"].to_numpy(dtype=float),
                y=curve["y"].to_numpy(dtype=float),
            )
        )
    return blocks


def simulate(
    blocks: list[Block],
    target_m3_per_year: float,
    *,
    horizon: int = 250,
    width: int = 5,
    min_age: int = 40,
    factor: float = 1.0,
) -> bool:
    if target_m3_per_year <= 0:
        return True
    ages = np.array([block.age for block in blocks], dtype=float)
    areas = np.array([block.area_ha * factor for block in blocks], dtype=float)
    target = target_m3_per_year * width
    periods = horizon // width
    for _ in range(periods):
        available = np.where(ages >= min_age)[0]
        if available.size == 0:
            return False
        volumes = np.array(
            [blocks[i].volume_per_ha(ages[i]) * areas[i] for i in available]
        )
        order = available[np.argsort(-ages[available], kind="stable")]
        volume_by_index = dict(zip(available.tolist(), volumes.tolist(), strict=True))
        harvested = 0.0
        for index in order:
            harvested += volume_by_index[int(index)]
            ages[int(index)] = 0.0
            if harvested >= target:
                break
        if harvested < target:
            return False
        ages += width
    return True


def max_even_flow(
    blocks: list[Block], *, horizon: int = 250, width: int = 5, min_age: int = 40
) -> float:
    total_area = sum(block.area_ha for block in blocks)
    max_yield = max(float(block.y[-1]) for block in blocks)
    upper = max(1.0, total_area * max_yield / width)
    low, high = 0.0, upper
    for _ in range(50):
        mid = (low + high) / 2
        if simulate(blocks, mid, horizon=horizon, width=width, min_age=min_age):
            low = mid
        else:
            high = mid
    return low


def run_case(
    blocks: list[Block],
    *,
    horizon: int,
    width: int,
    min_age: int,
    base_area: float,
) -> dict[str, object]:
    vmax = max_even_flow(blocks, horizon=horizon, width=width, min_age=min_age)
    factor = AAC / vmax if vmax > 0 else float("nan")
    net_area = factor * base_area
    return {
        "base_area_ha": round(base_area, 2),
        "max_even_flow_m3_per_year": round(vmax, 1),
        "thlb_factor": round(factor, 4),
        "net_area_ha": round(net_area, 2),
        "netdown_vs_aac_area": round(net_area / AAC_AREA, 4),
        "netdown_vs_aoi": round(net_area / AOI, 4),
        "netdown_vs_proxy_thlb": round(net_area / PROXY_THLB, 4),
        "netdown_vs_gross_vri": round(net_area / GROSS_VRI, 4),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--horizon", type=int, default=250)
    parser.add_argument("--width", type=int, default=5)
    parser.add_argument("--min-age", type=int, default=40)
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "data" / "aac" / "w0026",
    )
    args = parser.parse_args(argv)

    all_blocks = load_blocks(include_unmanaged=True)
    managed_blocks = load_blocks(include_unmanaged=False)
    all_area = float(sum(block.area_ha for block in all_blocks))
    managed_area = float(sum(block.area_ha for block in managed_blocks))

    cases: dict[str, object] = {}
    cases["all_vri"] = run_case(
        all_blocks,
        horizon=args.horizon,
        width=args.width,
        min_age=args.min_age,
        base_area=all_area,
    )
    cases["managed_thlb"] = run_case(
        managed_blocks,
        horizon=args.horizon,
        width=args.width,
        min_age=args.min_age,
        base_area=managed_area,
    )

    sensitivity = []
    for name, blocks, base in (
        ("all_vri", all_blocks, all_area),
        ("managed_thlb", managed_blocks, managed_area),
    ):
        for min_age in (40, 60, 80):
            for width in (5, 10):
                result = run_case(
                    blocks,
                    horizon=args.horizon,
                    width=width,
                    min_age=min_age,
                    base_area=base,
                )
                sensitivity.append(
                    {
                        "model": name,
                        "min_age": min_age,
                        "width": width,
                        **result,
                    }
                )

    payload = {
        "instance": "wl-w0026",
        "published_aac_m3_per_year": AAC,
        "aac_area_ha": AAC_AREA,
        "aoi_ha": AOI,
        "proxy_thlb_ha": PROXY_THLB,
        "gross_vri_fragment_ha": round(all_area, 2),
        "managed_fragment_ha": round(managed_area, 2),
        "assumptions": {
            "horizon_years": args.horizon,
            "period_width_years": args.width,
            "minimum_harvest_age": args.min_age,
            "harvest_rule": "oldest-first priority queue",
            "flow": "constant non-declining even flow",
            "regeneration": "clearcut, reset age to 0; same yield curve",
            "thlb": "single multiplicative factor applied to fragment area",
            "partial_cut": "not modelled in this first calibration",
            "private_land": "not separately identified; the factor absorbs it",
        },
        "cases": cases,
        "sensitivity": sensitivity,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "w4w_calibration.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    recommended = cases["all_vri"]
    factor = float(recommended["thlb_factor"])
    table = []
    for block in all_blocks:
        table.append(
            {
                "block_id": block.block_id,
                "track_id": block.track_id,
                "area_ha": round(block.area_ha, 4),
                "age": block.age,
                "curve_id": block.curve_id,
                "volume_at_age_m3": round(
                    block.area_ha * block.volume_per_ha(block.age), 1
                ),
                "calibrated_thlb_factor": factor,
                "calibrated_net_area_ha": round(block.area_ha * factor, 4),
            }
        )
    pd.DataFrame(table).to_csv(args.out / "w4w_plausible_inputs.csv", index=False)

    print(json.dumps(payload, indent=2, sort_keys=True)[:6000])
    print(f"\nWrote {args.out / 'w4w_calibration.json'}")
    print(f"Wrote {args.out / 'w4w_plausible_inputs.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
