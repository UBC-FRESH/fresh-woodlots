#!/usr/bin/env python3
"""Clip FEMIC fragments to the woodlot AOI and split by THLB.

FEMIC's custom-boundary mode selects VRI polygons that intersect the boundary
but does not clip them. This step:

1. intersects the exported fragments with the AOI;
2. if a prepared Proxy THLB layer exists, computes each fragment's net
   contribution to the THLB as ``intersection_area × pthlb_fact`` and splits
   the fragment record into managed and unmanaged shares;
3. recomputes ``AREA_HA`` as the net (factor-weighted) area.

The output is ``fragments_clipped.shp``, which is the WS4 build input.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd


def _clean(frame: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    drop = [column for column in frame.columns if column.startswith("index_")]
    result = frame.drop(columns=drop, errors="ignore").copy()
    result["AREA_HA"] = result.geometry.area / 10_000.0
    return result[result["AREA_HA"] > 0].copy()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-root", type=Path, required=True)
    parser.add_argument(
        "--thlb",
        type=Path,
        default=None,
        help="Prepared THLB GeoPackage (default: data/source/thlb/thlb.gpkg)",
    )
    args = parser.parse_args(argv)

    instance_root = args.instance_root.resolve()
    slug = instance_root.name
    fragments_path = (
        instance_root / "output" / "patchworks" / "fragments" / "fragments.shp"
    )
    aoi_path = instance_root / "data" / "source" / "aoi" / f"{slug}.gpkg"
    thlb_path = args.thlb or (instance_root / "data" / "source" / "thlb" / "thlb.gpkg")
    if not fragments_path.exists():
        raise FileNotFoundError(fragments_path)
    if not aoi_path.exists():
        raise FileNotFoundError(aoi_path)

    fragments = gpd.read_file(fragments_path).to_crs("EPSG:3005")
    aoi = gpd.read_file(aoi_path, layer="aoi").to_crs("EPSG:3005")
    clipped = gpd.overlay(
        fragments, aoi[["geometry"]], how="intersection", keep_geom_type=True
    )
    clipped = _clean(clipped)

    if thlb_path.exists():
        thlb = gpd.read_file(thlb_path, layer="thlb").to_crs("EPSG:3005")
        thlb = thlb[thlb["pthlb_fact"].fillna(0) > 0].copy()
        if thlb.empty:
            result = clipped
            result["IFM"] = "managed"
            print("THLB layer has no positive pthlb_fact; all fragments managed")
        else:
            clipped = clipped.reset_index(drop=True)
            clipped["_fragment_row"] = range(len(clipped))
            parts = gpd.overlay(
                clipped[["_fragment_row", "geometry"]],
                thlb[["pthlb_fact", "geometry"]],
                how="intersection",
                keep_geom_type=True,
            )
            parts["_weighted_ha"] = (
                parts.geometry.area / 10_000.0 * parts["pthlb_fact"]
            )
            weighted = parts.groupby("_fragment_row")["_weighted_ha"].sum()
            total_ha = clipped.geometry.area / 10_000.0
            managed_ha = clipped["_fragment_row"].map(weighted).fillna(0.0)
            managed_ha = managed_ha.clip(upper=total_ha)
            managed = clipped.copy()
            managed["AREA_HA"] = managed_ha
            managed["IFM"] = "managed"
            unmanaged = clipped.copy()
            unmanaged["AREA_HA"] = total_ha - managed_ha
            unmanaged["IFM"] = "unmanaged"
            managed = managed[managed["AREA_HA"] > 1e-6]
            unmanaged = unmanaged[unmanaged["AREA_HA"] > 1e-6]
            result = gpd.GeoDataFrame(
                pd.concat([managed, unmanaged], ignore_index=True),
                geometry="geometry",
                crs=clipped.crs,
            )
            result = result.drop(columns=["_fragment_row"], errors="ignore")
            print(
                f"THLB net split: managed {managed['AREA_HA'].sum():,.2f} ha, "
                f"unmanaged {unmanaged['AREA_HA'].sum():,.2f} ha, "
                f"rows {len(managed)} + {len(unmanaged)}"
            )
    else:
        result = clipped
        result["IFM"] = "managed"
        print("No prepared THLB layer; all clipped fragments are managed")

    out_dir = fragments_path.parent
    out_path = out_dir / "fragments_clipped.shp"
    for suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
        candidate = out_path.with_suffix(suffix)
        if candidate.exists():
            candidate.unlink()
    result.to_file(out_path)

    print(
        f"Clipped fragments: {len(fragments)} -> {len(result)} rows, "
        f"{fragments.geometry.area.sum() / 1e4:,.2f} -> "
        f"{result['AREA_HA'].sum():,.2f} net ha"
    )
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
