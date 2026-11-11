#!/usr/bin/env python3
"""Write even-flow AAC targets for one woodlot instance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = "product.HarvestedVolume.managed.Total.CC"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--queue",
        type=Path,
        default=REPO_ROOT / "queue" / "woodlot_build_queue.json",
    )
    parser.add_argument("--slug", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--period-width", type=int, default=10)
    parser.add_argument("--years", type=int, default=100)
    parser.add_argument(
        "--upper-factor",
        type=float,
        default=2.0,
        help="Maximum is AAC x period_width x upper_factor",
    )
    args = parser.parse_args(argv)

    payload = json.loads(args.queue.read_text(encoding="utf-8"))
    entry = next(
        (
            item
            for item in payload.get("instances", [])
            if item.get("slug") == args.slug
        ),
        None,
    )
    if entry is None:
        raise SystemExit(f"slug not in queue: {args.slug}")
    aac = entry.get("aac_m3")
    if aac is None or float(aac) <= 0:
        raise SystemExit(f"no positive AAC for {args.slug}")

    floor = float(aac) * args.period_width
    ceiling = floor * args.upper_factor
    periods = max(1, args.years // args.period_width)
    targets = [
        {
            "account": ACCOUNT,
            "period": period,
            "minimum": floor,
            "maximum": ceiling,
            "period_width": args.period_width,
            "priority": 2,
        }
        for period in range(1, periods + 1)
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        yaml.safe_dump({"targets": targets}, sort_keys=False), encoding="utf-8"
    )
    print(
        f"Wrote {len(targets)} targets to {args.output}: "
        f"AAC={float(aac):,.0f} m3/yr, band={floor:,.0f}-{ceiling:,.0f} "
        f"m3 per {args.period_width} years"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
