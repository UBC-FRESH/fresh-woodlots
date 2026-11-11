#!/usr/bin/env python3
"""Calibrate a simplified Woodlot-for-Windows-style AAC for one woodlot.

The model is deliberately simple and transparent:

- one stand per WS4 fragment (managed or unmanaged curve as available);
- oldest-first priority queue;
- 250-year constant (non-declining even-flow) harvest target;
- clearcut/regrowth with a minimum harvest age;
- a single multiplicative THLB factor.

The published AAC is the target. We solve for the THLB factor that makes the
simplified model produce that rate, and report the implied net area against the
public areas. This is a calibration, not a statutory AAC calculation.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "queue" / "woodlot_build_queue.json"


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


def load_blocks(compiled: Path, include_unmanaged: bool = True) -> list[Block]:
    fragments = pd.read_parquet(compiled / "fragments.parquet")
    features = pd.read_parquet(compiled / "features.parquet")
    curves = pd.read_parquet(compiled / "curves.parquet")
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
    aac: float,
    aac_area: float,
    aoi: float,
    proxy_thlb: float,
    gross_vri: float,
    horizon: int,
    width: int,
    min_age: int,
    base_area: float,
) -> dict[str, object]:
    vmax = max_even_flow(blocks, horizon=horizon, width=width, min_age=min_age)
    factor = aac / vmax if vmax > 0 else float("nan")
    net_area = factor * base_area
    return {
        "base_area_ha": round(base_area, 2),
        "max_even_flow_m3_per_year": round(vmax, 1),
        "thlb_factor": round(factor, 4),
        "net_area_ha": round(net_area, 2),
        "netdown_vs_aac_area": round(net_area / aac_area, 4) if aac_area else None,
        "netdown_vs_aoi": round(net_area / aoi, 4) if aoi else None,
        "netdown_vs_proxy_thlb": round(net_area / proxy_thlb, 4) if proxy_thlb else None,
        "netdown_vs_gross_vri": round(net_area / gross_vri, 4) if gross_vri else None,
    }


def resolve_instance(slug: str, instance_root: Path | None) -> tuple[Path, dict[str, object]]:
    entries = json.loads(QUEUE_PATH.read_text(encoding="utf-8")).get("instances", [])
    entry = next((item for item in entries if item.get("slug") == slug), None)
    if entry is None:
        raise SystemExit(f"slug not in queue: {slug}")
    root = instance_root or (REPO_ROOT / "instances" / slug)
    return root, entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", default="wl-w0026")
    parser.add_argument("--instance-root", type=Path, default=None)
    parser.add_argument("--horizon", type=int, default=250)
    parser.add_argument("--width", type=int, default=5)
    parser.add_argument("--min-age", type=int, default=40)
    parser.add_argument("--quick", action="store_true", help="run only the headline case")
    parser.add_argument("--write-docs", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    root, entry = resolve_instance(args.slug, args.instance_root)
    compiled = root / "ws4" / "build" / "compiled"
    if not (compiled / "fragments.parquet").is_file():
        raise SystemExit(f"no compiled dataset: {compiled}")
    aac = float(entry.get("aac_m3") or 0)
    if aac <= 0:
        raise SystemExit(f"no positive AAC for {args.slug}")
    aac_area = float(entry.get("aac_area_ha") or 0)
    aoi = float(entry.get("area_ha") or 0)
    thlb_summary = root / "data" / "source" / "thlb" / "thlb.summary.json"
    proxy_thlb = 0.0
    if thlb_summary.is_file():
        proxy_thlb = float(json.loads(thlb_summary.read_text()).get("thlb_ha") or 0)

    all_blocks = load_blocks(compiled, include_unmanaged=True)
    managed_blocks = load_blocks(compiled, include_unmanaged=False)
    all_area = float(sum(block.area_ha for block in all_blocks))
    managed_area = float(sum(block.area_ha for block in managed_blocks))

    cases: dict[str, object] = {
        "all_vri": run_case(
            all_blocks,
            aac=aac,
            aac_area=aac_area,
            aoi=aoi,
            proxy_thlb=proxy_thlb,
            gross_vri=all_area,
            horizon=args.horizon,
            width=args.width,
            min_age=args.min_age,
            base_area=all_area,
        )
    }
    if not args.quick:
        cases["managed_thlb"] = run_case(
            managed_blocks,
            aac=aac,
            aac_area=aac_area,
            aoi=aoi,
            proxy_thlb=proxy_thlb,
            gross_vri=all_area,
            horizon=args.horizon,
            width=args.width,
            min_age=args.min_age,
            base_area=managed_area,
        )

    sensitivity = []
    if not args.quick:
        for name, blocks, base in (
            ("all_vri", all_blocks, all_area),
            ("managed_thlb", managed_blocks, managed_area),
        ):
            for min_age in (40, 60, 80):
                for width in (5, 10):
                    sensitivity.append(
                        {
                            "model": name,
                            "min_age": min_age,
                            "width": width,
                            **run_case(
                                blocks,
                                aac=aac,
                                aac_area=aac_area,
                                aoi=aoi,
                                proxy_thlb=proxy_thlb,
                                gross_vri=all_area,
                                horizon=args.horizon,
                                width=width,
                                min_age=min_age,
                                base_area=base,
                            ),
                        }
                    )

    payload = {
        "schema_version": 1,
        "slug": args.slug,
        "file_id": entry.get("file_id"),
        "display_name": entry.get("display_name"),
        "published_aac_m3_per_year": aac,
        "aac_area_ha": aac_area,
        "aoi_ha": aoi,
        "proxy_thlb_ha": proxy_thlb,
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
        "interpretation": (
            "The published AAC is reproduced by scaling the gross VRI fragment "
            "area by the all-vri THLB factor. This is a simplified W4W replica, "
            "not a statutory AAC calculation."
        ),
    }

    out = args.out or (root / "config")
    out.mkdir(parents=True, exist_ok=True)
    (out / "w4w_calibration.json").write_text(
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
    pd.DataFrame(table).to_csv(out / "w4w_plausible_inputs.csv", index=False)

    if args.write_docs:
        lines = [
            f"# {args.slug} — W4W base-scenario rationale",
            "",
            "## Published AAC",
            "",
            f"**{aac:,.0f} m³/year** for `{entry.get('file_id')}` "
            f"({entry.get('display_name')}).",
            "",
            "## Calibration",
            "",
            "The simplified W4W replica uses oldest-first priority, a 250-year "
            "constant even-flow target, 5-year periods, minimum harvest age 40, "
            "and clearcut/regrowth with the WS4 compiled yield curves.",
            "",
            "| Input | Value |",
            "|---|---:|",
            f"| Gross VRI fragments | {all_area:,.2f} ha |",
            f"| Max even flow at factor 1.0 | "
            f"{recommended['max_even_flow_m3_per_year']:,.1f} m³/yr |",
            f"| Calibrated THLB factor | {factor:.4f} |",
            f"| Calibrated net area | {recommended['net_area_ha']:,.2f} ha |",
            f"| Published AAC / net area | {aac / recommended['net_area_ha']:,.2f} m³/ha/yr |",
            f"| Net area vs AAC area | "
            f"{recommended['netdown_vs_aac_area']:.1%} |",
            f"| Net area vs AOI | {recommended['netdown_vs_aoi']:.1%} |",
            f"| Net area vs Proxy THLB | "
            f"{recommended['netdown_vs_proxy_thlb'] or 0:.1%} |",
            "",
            "## Caveats",
            "",
            "This is a simplified calibration, not the actual Woodlot for Windows "
            "project. It does not model partial cutting, roads, private land, or "
            "all W4W constraints. The factor absorbs those differences. A real "
            "W4W project file or management plan would supersede this.",
            "",
            "The portal scenario `W4W published AAC (1.0×)` applies the published "
            "AAC as a target without the 1.2× uplift.",
        ]
        (out / "W4W-CALIBRATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        f"{args.slug}: AAC={aac:.0f}, all-area={all_area:.2f} ha, "
        f"Vmax={recommended['max_even_flow_m3_per_year']:.1f}, "
        f"factor={factor:.4f}, net={recommended['net_area_ha']:.2f} ha"
    )
    print(f"Wrote {out / 'w4w_calibration.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
