"""Tests for the woodlot catalog transform."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon

from fresh_wl.catalog import (
    dissolve_catalog,
    is_woodlot_file_id,
    merge_aac,
    read_aac_table,
    slugify,
)


def _frame() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        [
            {
                "FOREST_FILE_ID": "W0026",
                "MAP_LABEL": "W0026 1 SCHEDULE_A",
                "CLIENT_NAME": "CHINOOK WOODLOTS LTD.",
                "ML_TYPE_CODE": "SCHEDULE_A",
                "FILE_STATUS_CODE": "HI",
                "ADMIN_DISTRICT_NAME": "Campbell River",
                "geometry": Polygon([(0, 0), (100, 0), (100, 100), (0, 100)]),
            },
            {
                "FOREST_FILE_ID": "W0026",
                "MAP_LABEL": "W0026 2 SCHEDULE_B",
                "CLIENT_NAME": "CHINOOK WOODLOTS LTD.",
                "ML_TYPE_CODE": "SCHEDULE_B",
                "FILE_STATUS_CODE": "HI",
                "ADMIN_DISTRICT_NAME": "Campbell River",
                "geometry": Polygon([(200, 0), (400, 0), (400, 200), (200, 200)]),
            },
            {
                "FOREST_FILE_ID": "K1A",
                "MAP_LABEL": "K1A A SCHEDULE_A",
                "CLIENT_NAME": "A COMMUNITY FOREST",
                "ML_TYPE_CODE": "SCHEDULE_A",
                "FILE_STATUS_CODE": "HC",
                "ADMIN_DISTRICT_NAME": "Nadina",
                "geometry": Polygon([(500, 0), (510, 0), (510, 10), (500, 10)]),
            },
        ],
        geometry="geometry",
        crs="EPSG:3005",
    )


def test_is_woodlot_file_id() -> None:
    assert is_woodlot_file_id("W0026")
    assert is_woodlot_file_id(" w1548 ")
    assert not is_woodlot_file_id("K1A")
    assert not is_woodlot_file_id("W26")
    assert not is_woodlot_file_id(None)


def test_slugify() -> None:
    assert slugify("Chinook & Co.") == "chinook-and-co"
    assert slugify("  ") == "unnamed"


def test_dissolve_groups_polygons_and_sums_schedules() -> None:
    catalog = dissolve_catalog(_frame())

    assert len(catalog) == 1
    row = catalog.iloc[0]
    assert row["file_id"] == "W0026"
    assert row["slug"] == "wl-w0026"
    assert row["polygon_count"] == 2
    assert row["area_ha"] == 5.0
    assert row["schedule_a_ha"] == 1.0
    assert row["schedule_b_ha"] == 4.0
    assert row["district"] == "Campbell River"
    assert row["status"] == "HI"


def test_dissolve_sorts_by_file_id() -> None:
    frame = _frame()
    extra = frame.iloc[[0]].copy()
    extra["FOREST_FILE_ID"] = "W0027"
    extra["geometry"] = Polygon([(600, 0), (610, 0), (610, 10), (600, 10)])
    catalog = dissolve_catalog(
        gpd.GeoDataFrame(
            pd.concat([frame, extra], ignore_index=True),
            geometry="geometry",
            crs="EPSG:3005",
        )
    )

    assert list(catalog["file_id"]) == ["W0026", "W0027"]


def test_merge_aac_attaches_values() -> None:
    catalog = dissolve_catalog(_frame())
    aac = pd.DataFrame(
        {
            "file_id": ["W0026"],
            "aac_m3": [7311.0],
            "aac_area_ha": [1110.0],
            "aac_licensee": ["CHINOOK WOODLOTS LTD."],
            "aac_district": ["Campbell River Natural Resource District"],
        }
    )

    merged = merge_aac(catalog, aac)

    assert merged.loc[0, "aac_m3"] == 7311.0
    assert merged.loc[0, "aac_area_ha"] == 1110.0


def test_read_aac_table_has_803_unique_woodlots() -> None:
    pytest.importorskip("xlrd")
    path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "downloads"
        / "ftarpt_f000_file_status_register_mar2026rpt.xls"
    )
    if not path.exists():
        pytest.skip("AAC workbook not downloaded")

    aac = read_aac_table(path)

    assert len(aac) == 803
    assert aac["file_id"].is_unique
    assert aac["aac_m3"].notna().sum() >= 800
