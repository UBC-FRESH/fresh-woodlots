#!/usr/bin/env python3
"""Clip the public Provincial Proxy THLB to one woodlot AOI.

Source: BC Data Catalogue, *Provincial Proxy Timber Harvesting Land Base
(Proxy THLB)*, published by the Forest Analysis and Inventory Branch. The
layer is intended for strategic forest estate modelling, not operational
decisions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GDB = (
    REPO_ROOT / "data" / "downloads" / "proxy_thlb" / "provincial_pthlb.gdb"
)
DEFAULT_LAYER = "provincial_pthlb"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-root", type=Path, required=True)
    parser.add_argument("--gdb", type=Path, default=DEFAULT_GDB)
    parser.add_argument("--layer", default=DEFAULT_LAYER)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output GeoPackage (default: <instance>/data/source/thlb/thlb.gpkg)",
    )
    args = parser.parse_args(argv)

    instance_root = args.instance_root.resolve()
    slug = instance_root.name
    aoi_path = instance_root / "data" / "source" / "aoi" / f"{slug}.gpkg"
    if not aoi_path.exists():
        raise FileNotFoundError(aoi_path)
    if not args.gdb.exists():
        raise FileNotFoundError(args.gdb)

    aoi = gpd.read_file(aoi_path, layer="aoi").to_crs("EPSG:3005")
    thlb = gpd.read_file(
        args.gdb, layer=args.layer, bbox=tuple(aoi.total_bounds)
    ).to_crs("EPSG:3005")
    thlb = thlb[thlb["pthlb_fact"].fillna(0) > 0].copy()
    if thlb.empty:
        raise SystemExit(f"No proxy THLB features intersect {slug}")

    clipped = gpd.overlay(thlb, aoi[["geometry"]], how="intersection")
    clipped = clipped[clipped.geometry.area > 0].copy()
    if clipped.empty:
        raise SystemExit(f"Proxy THLB does not overlap the {slug} AOI")

    file_id = slug.split("-")[-1].upper()
    unit = f"Woodlot - {file_id}"
    woodlot_only = clipped[
        clipped["man_unit"].astype(str).str.upper() == unit.upper()
    ]
    if not woodlot_only.empty:
        clipped = woodlot_only
    clipped["thlb_area_ha"] = clipped.geometry.area / 10_000.0 * clipped["pthlb_fact"]

    out_path = args.out or (
        instance_root / "data" / "source" / "thlb" / "thlb.gpkg"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    clipped.to_file(out_path, layer="thlb", driver="GPKG")

    aoi_ha = float(aoi.geometry.area.sum()) / 10_000.0
    thlb_ha = float(clipped["thlb_area_ha"].sum())
    summary = {
        "slug": slug,
        "file_id": file_id,
        "aoi_ha": round(aoi_ha, 2),
        "thlb_ha": round(thlb_ha, 2),
        "thlb_fraction": round(thlb_ha / aoi_ha, 4) if aoi_ha else None,
        "feature_count": len(clipped),
        "man_units": sorted(clipped["man_unit"].astype(str).unique()),
        "source": {
            "name": "Provincial Proxy Timber Harvesting Land Base (Proxy THLB)",
            "publisher": "Forest Analysis and Inventory Branch, BC",
            "gdb": str(args.gdb),
            "layer": args.layer,
            "gdb_sha256": _sha256(args.gdb / "a00000001.gdbtable")
            if (args.gdb / "a00000001.gdbtable").exists()
            else None,
            "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds"),
        },
        "output": str(out_path),
    }
    summary_path = out_path.with_suffix(".summary.json")
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"THLB: {thlb_ha:,.2f} ha of {aoi_ha:,.2f} ha "
        f"({summary['thlb_fraction']:.1%}), {len(clipped)} polygons"
    )
    print(f"Wrote {out_path}")
    print(f"Wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
