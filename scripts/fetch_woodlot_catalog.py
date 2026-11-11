#!/usr/bin/env python3
"""Fetch the public BC woodlot licence catalog.

The source is the BC Geographic Warehouse *Forest Tenure Managed Licence*
layer, queried through the public ArcGIS REST endpoint. Only active ``W``
forest file IDs are kept.

Examples
--------
Run from the repository root::

    python scripts/fetch_woodlot_catalog.py

Write the artifacts somewhere else::

    python scripts/fetch_woodlot_catalog.py --out /tmp/woodlot-catalog
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from fresh_wl.catalog import (  # noqa: E402
    AAC_FILE_TYPE,
    AAC_FILENAME,
    AAC_PAGE,
    AAC_URL,
    CRS,
    OUT_FIELDS,
    SOURCE_URL,
    SOURCE_WHERE,
    dissolve_catalog,
    features_to_frame,
    merge_aac,
    read_aac_table,
    write_build_queue,
    write_catalog,
)

USER_AGENT = "fresh-woodlots/0.1 (+https://github.com/UBC-FRESH)"
MAX_CHUNK = 100


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        with destination.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    return destination


def _query(params: dict[str, str]) -> dict[str, object]:
    url = f"{SOURCE_URL}/query?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError(f"ArcGIS query failed: {payload['error']}")
    return payload


def fetch_object_ids() -> list[int]:
    """Return every active woodlot source object ID."""

    payload = _query(
        {
            "where": SOURCE_WHERE,
            "returnIdsOnly": "true",
            "f": "json",
        }
    )
    ids = payload.get("objectIds") or []
    if not ids:
        raise RuntimeError(f"No features returned for query: {SOURCE_WHERE}")
    return sorted(int(value) for value in ids)


def fetch_features(object_ids: list[int]) -> gpd.GeoDataFrame:
    """Fetch and concatenate source polygons for the given object IDs."""

    frames: list[gpd.GeoDataFrame] = []
    for start in range(0, len(object_ids), MAX_CHUNK):
        chunk = object_ids[start : start + MAX_CHUNK]
        payload = _query(
            {
                "objectIds": ",".join(str(value) for value in chunk),
                "outFields": ",".join(OUT_FIELDS),
                "returnGeometry": "true",
                "outSR": "3005",
                "f": "geojson",
            }
        )
        features = payload.get("features") or []
        if not isinstance(features, list):
            raise RuntimeError("Unexpected ArcGIS GeoJSON payload")
        if features:
            frames.append(features_to_frame(features, crs=CRS))
    if not frames:
        raise RuntimeError("No geometry returned for the requested object IDs")
    return gpd.GeoDataFrame(
        pd.concat(frames, ignore_index=True), geometry="geometry", crs=CRS
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "data",
        help="Output root (default: <repo>/data)",
    )
    parser.add_argument(
        "--queue",
        type=Path,
        default=REPO_ROOT / "queue" / "woodlot_build_queue.json",
        help="Build queue path (default: <repo>/queue/woodlot_build_queue.json)",
    )
    parser.add_argument(
        "--simplify-m",
        type=float,
        default=25.0,
        help="Web GeoJSON simplification tolerance in metres (default: 25)",
    )
    parser.add_argument(
        "--aac",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Merge the public issued woodlot AAC listing (default: yes)",
    )
    parser.add_argument(
        "--aac-url",
        default=AAC_URL,
        help="Public issued woodlot AAC workbook URL",
    )
    parser.add_argument(
        "--aac-file",
        type=Path,
        default=REPO_ROOT / "data" / "downloads" / AAC_FILENAME,
        help="Local AAC workbook path (default: data/downloads/<name>)",
    )
    args = parser.parse_args(argv)

    retrieved_at = datetime.now(UTC).isoformat(timespec="seconds")
    object_ids = fetch_object_ids()
    features = fetch_features(object_ids)
    catalog = dissolve_catalog(features)

    if catalog.empty:
        raise RuntimeError("No woodlot licences remained after filtering")

    aac_source: dict[str, object] | None = None
    if args.aac:
        aac_path = _download(args.aac_url, args.aac_file)
        aac = read_aac_table(aac_path)
        catalog = merge_aac(catalog, aac)
        matched = int(catalog["aac_m3"].notna().sum())
        aac_source = {
            "name": "Issued Woodlot Licence Listings (AAC report)",
            "file_type": AAC_FILE_TYPE,
            "url": args.aac_url,
            "catalogue_page": AAC_PAGE,
            "path": str(aac_path),
            "sha256": _sha256(aac_path),
            "rows": len(aac),
            "matched": matched,
            "licence": "Open Government Licence - British Columbia",
        }

    paths = write_catalog(
        catalog,
        catalog_dir=args.out / "catalog",
        boundary_dir=args.out / "boundaries",
        retrieved_at=retrieved_at,
        source_feature_count=len(features),
        source_object_ids=len(object_ids),
        simplify_m=args.simplify_m,
        aac_source=aac_source,
    )
    queue_path = write_build_queue(catalog, args.queue, generated_at=retrieved_at)

    total_area = float(catalog["area_ha"].sum())
    print(f"Retrieved {len(object_ids)} source objects at {retrieved_at}")
    print(
        f"Catalog: {len(catalog)} active woodlots, "
        f"{total_area:,.0f} ha, {len(features)} source polygons"
    )
    if aac_source is not None:
        total_aac = float(catalog["aac_m3"].fillna(0).sum())
        print(
            f"AAC: {aac_source['matched']}/{len(catalog)} matched, "
            f"{total_aac:,.0f} m3/yr total"
        )
    for name, path in paths.items():
        print(f"  {name}: {path}")
    print(f"  build_queue: {queue_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
