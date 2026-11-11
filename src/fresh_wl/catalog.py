"""Catalog helpers for BC woodlot licence boundaries.

The source is the public BC Geographic Warehouse *Forest Tenure Managed
Licence* layer. Woodlot licences use ``W`` forest file IDs (``W0001`` ... ``W2500``).
The layer is published under the Open Government Licence - British Columbia.

The module keeps the network fetch separate from the catalog transform so the
grouping and area rules can be tested without a live connection.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

CRS = "EPSG:3005"
SOURCE_LAYER = "WHSE_FOREST_TENURE.FTEN_MANAGED_LICENCE_POLY_SVW"
SOURCE_URL = (
    "https://maps.gov.bc.ca/arcgis/rest/services/whse/"
    "bcgw_pub_whse_forest_tenure/MapServer/8"
)
SOURCE_WHERE = "LIFE_CYCLE_STATUS_CODE='ACTIVE' AND FOREST_FILE_ID LIKE 'W%'"
SOURCE_PAGE = (
    "https://catalogue.data.gov.bc.ca/dataset/forest-tenure-managed-licence"
)
OUT_FIELDS: tuple[str, ...] = (
    "OBJECTID",
    "FOREST_FILE_ID",
    "MAP_LABEL",
    "CLIENT_NAME",
    "FEATURE_AREA_SQM",
    "FILE_STATUS_CODE",
    "LIFE_CYCLE_STATUS_CODE",
    "ADMIN_DISTRICT_NAME",
    "ML_TYPE_CODE",
)
CATALOG_COLUMNS: tuple[str, ...] = (
    "slug",
    "file_id",
    "display_name",
    "licensee",
    "area_ha",
    "polygon_count",
    "schedule_a_ha",
    "schedule_b_ha",
    "district",
    "status",
    "map_label_count",
    "aac_m3",
    "aac_area_ha",
    "aac_licensee",
    "aac_district",
)
AAC_URL = (
    "https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/"
    "forestry/timber-tenures/apportionment/"
    "ftarpt_f000_file_status_register_mar2026rpt.xls"
)
AAC_PAGE = (
    "https://www2.gov.bc.ca/gov/content/industry/forestry/forest-tenures/"
    "timber-harvesting-rights/woodlot-licences"
)
AAC_FILE_TYPE = "A04"
AAC_FILENAME = "ftarpt_f000_file_status_register_mar2026rpt.xls"
_WOODLOT_FILE_ID = re.compile(r"^W\d{4}$")


def is_woodlot_file_id(value: object) -> bool:
    """Return whether a forest file ID is a woodlot licence.

    Parameters
    ----------
    value : object
        Candidate forest file ID, possibly ``None`` or padded.

    Returns
    -------
    bool
        ``True`` for active-style woodlot IDs such as ``W0001`` or ``W2500``.
    """

    return bool(_WOODLOT_FILE_ID.match(str(value or "").strip().upper()))


def slugify(value: str) -> str:
    """Return a stable lowercase slug for a woodlot label.

    Parameters
    ----------
    value : str
        Human-readable label.

    Returns
    -------
    str
        Lowercase ASCII slug with single hyphens. Empty input yields
        ``"unnamed"``.
    """

    text = value.strip().lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "unnamed"


def _first_text(values: Iterable[object]) -> str:
    for value in values:
        text = str(value or "").strip()
        if text and text.lower() != "nan":
            return text
    return ""


def _unique_text(values: Iterable[object]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text.lower() == "nan" or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def features_to_frame(
    features: Sequence[dict[str, Any]], crs: str = CRS
) -> gpd.GeoDataFrame:
    """Convert ArcGIS GeoJSON features to a GeoDataFrame.

    Parameters
    ----------
    features : sequence of dict
        GeoJSON features with ``properties`` and ``geometry`` members.
    crs : str, default ``"EPSG:3005"``
        Coordinate reference system of the incoming geometries.

    Returns
    -------
    geopandas.GeoDataFrame
        One row per source polygon. An empty input returns an empty frame with
        the expected columns.
    """

    rows: list[dict[str, Any]] = []
    for feature in features:
        properties = dict(feature.get("properties") or {})
        geometry = feature.get("geometry")
        if not geometry:
            continue
        properties["geometry"] = shape(geometry)
        rows.append(properties)
    if not rows:
        return gpd.GeoDataFrame(
            columns=[*OUT_FIELDS, "geometry"], geometry="geometry", crs=crs
        )
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=crs)


def dissolve_catalog(
    features: gpd.GeoDataFrame, crs: str = CRS
) -> gpd.GeoDataFrame:
    """Dissolve source licence polygons into one row per woodlot.

    Parameters
    ----------
    features : geopandas.GeoDataFrame
        Source polygons with ``FOREST_FILE_ID``, ``CLIENT_NAME``,
        ``ML_TYPE_CODE``, ``FILE_STATUS_CODE``, and ``ADMIN_DISTRICT_NAME``.
    crs : str, default ``"EPSG:3005"``
        CRS used for area calculations when the input has no CRS.

    Returns
    -------
    geopandas.GeoDataFrame
        One row per woodlot, sorted by ``file_id``. Area columns are hectares
        computed in the projected CRS.
    """

    if features.empty:
        return gpd.GeoDataFrame(
            columns=[*CATALOG_COLUMNS, "geometry"], geometry="geometry", crs=crs
        )

    frame = features.copy()
    if frame.crs is None:
        frame = frame.set_crs(crs)
    elif str(frame.crs).upper() != crs.upper():
        frame = frame.to_crs(crs)

    frame["FOREST_FILE_ID"] = (
        frame["FOREST_FILE_ID"].astype(str).str.strip().str.upper()
    )
    frame = frame[frame["FOREST_FILE_ID"].map(is_woodlot_file_id)].copy()
    if frame.empty:
        return gpd.GeoDataFrame(
            columns=[*CATALOG_COLUMNS, "geometry"], geometry="geometry", crs=crs
        )

    frame["ML_TYPE_CODE"] = (
        frame.get("ML_TYPE_CODE", pd.Series("", index=frame.index))
        .fillna("")
        .astype(str)
        .str.upper()
    )
    frame["_area_ha"] = frame.geometry.area / 10_000.0

    records: list[dict[str, Any]] = []
    for file_id, group in frame.groupby("FOREST_FILE_ID", sort=True):
        geometry = group.geometry.union_all()
        if geometry is None or geometry.is_empty:
            continue
        schedule_a = float(
            group.loc[group["ML_TYPE_CODE"] == "SCHEDULE_A", "_area_ha"].sum()
        )
        schedule_b = float(
            group.loc[group["ML_TYPE_CODE"] == "SCHEDULE_B", "_area_ha"].sum()
        )
        licensee = _first_text(group.get("CLIENT_NAME", []))
        records.append(
            {
                "slug": f"wl-{file_id.lower()}",
                "file_id": file_id,
                "display_name": licensee or file_id,
                "licensee": licensee,
                "area_ha": round(float(geometry.area) / 10_000.0, 2),
                "polygon_count": int(len(group)),
                "schedule_a_ha": round(schedule_a, 2),
                "schedule_b_ha": round(schedule_b, 2),
                "district": "; ".join(
                    _unique_text(group.get("ADMIN_DISTRICT_NAME", []))
                ),
                "status": "; ".join(
                    _unique_text(group.get("FILE_STATUS_CODE", []))
                ),
                "map_label_count": len(
                    _unique_text(group.get("MAP_LABEL", []))
                ),
                "geometry": geometry,
            }
        )

    result = gpd.GeoDataFrame(records, geometry="geometry", crs=crs)
    return result.sort_values("file_id").reset_index(drop=True)


def read_aac_table(path: Path) -> pd.DataFrame:
    """Read the public issued-tenure AAC report and keep woodlot rows.

    Parameters
    ----------
    path : pathlib.Path
        Downloaded ``ftarpt_f000_file_status_register`` workbook.

    Returns
    -------
    pandas.DataFrame
        One row per woodlot with ``file_id``, ``aac_m3``, ``aac_area_ha``,
        ``aac_licensee``, and ``aac_district``.
    """

    frame = pd.read_excel(path, sheet_name=0, header=2, engine="xlrd")
    frame = frame[frame["FILE_TYPE_CODE"].astype(str).str.upper() == AAC_FILE_TYPE]
    if frame.empty:
        raise ValueError(f"No {AAC_FILE_TYPE} rows in {path}")
    result = pd.DataFrame(
        {
            "file_id": frame["FOREST_FILE_ID"].astype(str).str.strip().str.upper(),
            "aac_m3": pd.to_numeric(frame["AAC_TOTAL"], errors="coerce"),
            "aac_area_ha": pd.to_numeric(frame["AREA_TOTAL"], errors="coerce"),
            "aac_licensee": frame["CLIENT_NAME / LICENSEE"].astype(str).str.strip(),
            "aac_district": frame["ORG_UNIT_NAME / DISTRICT"].astype(str).str.strip(),
        }
    )
    return result.sort_values("file_id").reset_index(drop=True)


def merge_aac(catalog: gpd.GeoDataFrame, aac: pd.DataFrame) -> gpd.GeoDataFrame:
    """Attach AAC values to the woodlot catalog.

    Parameters
    ----------
    catalog : geopandas.GeoDataFrame
        Output of :func:`dissolve_catalog`.
    aac : pandas.DataFrame
        Output of :func:`read_aac_table`.

    Returns
    -------
    geopandas.GeoDataFrame
        Catalog with AAC columns added. Missing AAC values remain ``NaN``.
    """

    frame = catalog.copy()
    if "file_id" not in aac.columns:
        raise ValueError("AAC table has no file_id column")
    merged = frame.merge(aac, on="file_id", how="left", validate="one_to_one")
    return gpd.GeoDataFrame(merged, geometry="geometry", crs=frame.crs)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_catalog(
    catalog: gpd.GeoDataFrame,
    *,
    catalog_dir: Path,
    boundary_dir: Path,
    retrieved_at: str,
    source_feature_count: int,
    source_object_ids: int,
    simplify_m: float = 25.0,
    aac_source: dict[str, Any] | None = None,
) -> dict[str, Path]:
    """Write the catalog, boundaries, and provenance manifest.

    Parameters
    ----------
    catalog : geopandas.GeoDataFrame
        Output of :func:`dissolve_catalog`.
    catalog_dir : pathlib.Path
        Directory for CSV, JSON, and the source manifest.
    boundary_dir : pathlib.Path
        Directory for the GeoPackage and web GeoJSON.
    retrieved_at : str
        ISO-8601 retrieval timestamp for the source query.
    source_feature_count : int
        Number of source polygons returned by the query.
    source_object_ids : int
        Number of source object IDs returned by the count query.
    simplify_m : float, default 25.0
        Simplification tolerance in metres for the web GeoJSON.
    aac_source : dict or None, optional
        AAC source metadata and SHA256, when the public listing was merged.

    Returns
    -------
    dict of str to pathlib.Path
        Written artifact paths keyed by short name.
    """

    catalog_dir.mkdir(parents=True, exist_ok=True)
    boundary_dir.mkdir(parents=True, exist_ok=True)
    frame = catalog.sort_values("file_id").reset_index(drop=True)
    for column in CATALOG_COLUMNS:
        if column not in frame.columns:
            frame[column] = None

    csv_path = catalog_dir / "woodlot_catalog.csv"
    frame.drop(columns=["geometry"]).loc[:, list(CATALOG_COLUMNS)].to_csv(
        csv_path, index=False
    )

    wgs84 = frame.to_crs("EPSG:4326")
    bounds = wgs84.geometry.bounds
    json_records: list[dict[str, Any]] = []
    for position, row in frame.iterrows():
        record = {
            column: row[column]
            for column in CATALOG_COLUMNS
            if column != "geometry"
        }
        record["bbox_wgs84"] = [
            round(float(bounds.loc[position, "minx"]), 6),
            round(float(bounds.loc[position, "miny"]), 6),
            round(float(bounds.loc[position, "maxx"]), 6),
            round(float(bounds.loc[position, "maxy"]), 6),
        ]
        json_records.append(record)

    json_path = catalog_dir / "woodlot_catalog.json"
    payload = {
        "schema_version": 1,
        "retrieved_at": retrieved_at,
        "source": {
            "name": "BC Geographic Warehouse - Forest Tenure Managed Licence",
            "layer": SOURCE_LAYER,
            "url": SOURCE_URL,
            "catalogue_page": SOURCE_PAGE,
            "where": SOURCE_WHERE,
            "crs": CRS,
            "licence": "Open Government Licence - British Columbia",
            "source_object_ids": source_object_ids,
            "source_features": source_feature_count,
        },
        "aac_source": aac_source,
        "count": len(json_records),
        "total_area_ha": round(float(frame["area_ha"].sum()), 2),
        "woodlots": json_records,
    }
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    gpkg_path = boundary_dir / "woodlot_boundaries.gpkg"
    if gpkg_path.exists():
        gpkg_path.unlink()
    frame.to_file(gpkg_path, layer="woodlot_boundaries", driver="GPKG")

    web = frame[["slug", "file_id", "display_name", "area_ha", "geometry"]].copy()
    web["geometry"] = web.geometry.simplify(simplify_m, preserve_topology=True)
    web = web.to_crs("EPSG:4326")
    geojson_path = boundary_dir / "woodlot_boundaries_simplified.geojson"
    if geojson_path.exists():
        geojson_path.unlink()
    web.to_file(geojson_path, driver="GeoJSON")

    manifest_path = catalog_dir / "source_manifest.json"
    artifacts = (csv_path, json_path, gpkg_path, geojson_path)
    manifest = {
        "schema_version": 1,
        "retrieved_at": retrieved_at,
        "source": payload["source"],
        "aac_source": aac_source,
        "count": len(json_records),
        "total_area_ha": payload["total_area_ha"],
        "simplify_m": simplify_m,
        "outputs": {
            path.name: {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in artifacts
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    return {
        "catalog_csv": csv_path,
        "catalog_json": json_path,
        "boundaries_gpkg": gpkg_path,
        "boundaries_geojson": geojson_path,
        "manifest": manifest_path,
    }


def write_build_queue(
    catalog: gpd.GeoDataFrame,
    path: Path,
    *,
    generated_at: str | None = None,
) -> Path:
    """Write one pending build entry per woodlot.

    Existing statuses are preserved when the queue already exists, so the
    artifact can be regenerated without losing progress.

    Parameters
    ----------
    catalog : geopandas.GeoDataFrame
        Output of :func:`dissolve_catalog`.
    path : pathlib.Path
        Destination JSON path.
    generated_at : str or None, default None
        ISO-8601 timestamp. Defaults to the current UTC time.

    Returns
    -------
    pathlib.Path
        The written queue path.
    """

    timestamp = generated_at or datetime.now(UTC).isoformat(
        timespec="seconds"
    )
    prior_entries: dict[str, dict[str, Any]] = {}
    if path.exists():
        try:
            prior = json.loads(path.read_text(encoding="utf-8"))
            prior_entries = {
                str(entry.get("slug")): entry
                for entry in prior.get("instances", [])
                if entry.get("slug")
            }
        except (json.JSONDecodeError, OSError):
            prior_entries = {}

    instances: list[dict[str, Any]] = []
    for row in catalog.sort_values("file_id").itertuples(index=False):
        aac_m3 = getattr(row, "aac_m3", None)
        aac_area_ha = getattr(row, "aac_area_ha", None)
        if aac_m3 is not None and pd.isna(aac_m3):
            aac_m3 = None
        if aac_area_ha is not None and pd.isna(aac_area_ha):
            aac_area_ha = None
        entry: dict[str, Any] = {
            "slug": row.slug,
            "file_id": row.file_id,
            "display_name": row.display_name,
            "area_ha": row.area_ha,
            "aac_m3": aac_m3,
            "aac_area_ha": aac_area_ha,
            "status": "pending",
            "phase": "W1",
            "steps": [
                "aoi",
                "femic_inventory",
                "femic_curves",
                "ws4_build",
                "ws4_baseline",
                "fhops_scenario",
                "portal_mount",
            ],
        }
        prior_entry = prior_entries.get(row.slug)
        if prior_entry is not None:
            for key in ("status", "notes", "instance_root"):
                if key in prior_entry:
                    entry[key] = prior_entry[key]
        instances.append(entry)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": timestamp,
                "count": len(instances),
                "instances": instances,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path
