#!/usr/bin/env python3
"""Clip the public VRI to one woodlot and build a per-instance data root.

FEMIC's custom-boundary mode selects VRI polygons that intersect the boundary
but does not clip them. This script:

1. reads the VRI Rank 1 polygon layer for the AOI bounding box;
2. clips it to the AOI;
3. writes a per-instance ``data/external`` root with the clipped VRI and
   symlinks to the shared TSA, site-productivity, and VDYP input sources.

Point ``FEMIC_EXTERNAL_DATA_ROOT`` at ``<instance>/data/external`` and the run
profile's ``source_paths.vri_rel_candidates`` at the clipped GeoPackage.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHARED_ROOT = Path(
    os.environ.get(
        "FEMIC_SHARED_DATA_ROOT",
        "/srv/shared-data/gep/ws4/femic/external/femic-public-data/data",
    )
)
VRI_REL = Path("bc/vri/2025/VEG_COMP_LYR_R1_POLY_2025.gdb")
VRI_LAYER = "VEG_COMP_LYR_R1_POLY"
SYMLINKS = (
    Path("bc/tsa/FADM_TSA.gdb"),
    Path("bc/siteprod/Site_Prod_BC.gdb"),
    Path("bc/siteprod/siteprod.tif"),
    Path("bc/siteprod/siteprod.bandmap.json"),
    Path("bc/vri/2025/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2025.gdb"),
    Path("misc.thlb.tif"),
)


def _symlink(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() or target.exists():
        return
    target.symlink_to(source)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-root", type=Path, required=True)
    parser.add_argument("--shared-root", type=Path, default=DEFAULT_SHARED_ROOT)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Per-instance external root (default: <instance>/data/external)",
    )
    args = parser.parse_args(argv)

    instance_root = args.instance_root.resolve()
    slug = instance_root.name
    aoi_path = instance_root / "data" / "source" / "aoi" / f"{slug}.gpkg"
    if not aoi_path.exists():
        raise FileNotFoundError(aoi_path)
    vri_gdb = args.shared_root / VRI_REL
    if not vri_gdb.exists():
        raise FileNotFoundError(vri_gdb)

    aoi = gpd.read_file(aoi_path, layer="aoi").to_crs("EPSG:3005")
    vri = gpd.read_file(vri_gdb, layer=VRI_LAYER, bbox=tuple(aoi.total_bounds))
    if vri.empty:
        raise SystemExit(f"No VRI polygons intersect {slug}")
    clipped = gpd.clip(vri.to_crs("EPSG:3005"), aoi)
    clipped = clipped[clipped.geometry.area > 0].copy()
    if clipped.empty:
        raise SystemExit(f"VRI clip is empty for {slug}")

    out_root = args.out or (instance_root / "data" / "external")
    out_vri = out_root / "bc" / "vri" / "2025" / "VEG_COMP_LYR_R1_POLY_2025.gpkg"
    out_vri.parent.mkdir(parents=True, exist_ok=True)
    if out_vri.exists():
        out_vri.unlink()
    clipped.to_file(out_vri, layer=VRI_LAYER, driver="GPKG")
    for relative in SYMLINKS:
        _symlink(args.shared_root / relative, out_root / relative)

    summary = {
        "slug": slug,
        "aoi_ha": round(float(aoi.geometry.area.sum()) / 10_000.0, 2),
        "vri_source": str(vri_gdb),
        "vri_layer": VRI_LAYER,
        "vri_features": len(clipped),
        "vri_area_ha": round(float(clipped.geometry.area.sum()) / 10_000.0, 2),
        "clipped_vri": str(out_vri),
        "external_root": str(out_root),
        "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    summary_path = out_root / "vri.summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"VRI clip: {len(clipped):,} polygons, "
        f"{summary['vri_area_ha']:,.2f} ha of {summary['aoi_ha']:,.2f} ha"
    )
    print(f"Wrote {out_vri}")
    print(f"Wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
