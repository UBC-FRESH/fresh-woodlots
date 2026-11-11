#!/usr/bin/env python3
"""Freeze woodlot pilot AOIs and scaffold their FEMIC workspaces.

This is P1.1/P1.2. It does not run the model. It writes, for each pilot:

- a single-woodlot AOI GeoPackage in EPSG:3005 and a web GeoJSON in EPSG:4326;
- a FEMIC run profile with custom-boundary mode;
- a provisional TIPSY rule config, clearly labelled as a placeholder;
- a per-pilot README and a shared pilot manifest with source hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _run_profile(slug: str, file_id: str) -> dict[str, object]:
    return {
        "selection": {
            "tsa": [file_id.lower()],
            "boundary_path": f"data/source/aoi/{slug}.gpkg",
            "boundary_layer": "aoi",
            "boundary_code": file_id.lower(),
            "strata": [],
            "stratification": {
                "bec_grouping": "subzone",
                "species_combo_count": 2,
                "include_tm_species2_for_single": True,
                "top_area_coverage": 0.90,
            },
        },
        "modes": {
            "resume": False,
            "dry_run": False,
            "verbose": True,
            "skip_checks": False,
        },
        "source_paths": {
            "vri_rel_candidates": [
                "bc/vri/2025/VEG_COMP_LYR_R1_POLY_2025.gpkg",
            ],
            "vdyp_input_rel_candidates": [
                "bc/vri/2025/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2025.gdb",
            ],
        },
        "run": {
            "run_id": f"{slug}_pilot",
            "log_dir": "runtime/logs",
        },
    }


def _tipsy_config(
    file_id: str, now: str, overrides: dict[str, str]
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "tsa_code": file_id.lower(),
        "species_code_overrides": overrides,
        "metadata": {
            "source_tsr": [],
            "author": "fresh-woodlots",
            "created_utc": now,
            "notes": (
                "Provisional generic public-data defaults for a pilot. "
                "Replace with local TSR, FSP, or RESULTS/SPAR evidence before "
                "any operational use."
            ),
        },
        "defaults": {
            "e": {
                "OAF2": 0.95,
                "FIZ": "I",
                "Regen_Method": "P",
                "Proportion": 1,
                "Density": 1200,
                "Util_DBH_cm": 12.5,
            },
            "f": {
                "OAF2": 0.95,
                "FIZ": "I",
                "Regen_Method": "P",
                "Proportion": 1,
                "Density": 1200,
                "SI_c1": 1.0,
                "SI_c2": 0.0,
                "Util_DBH_cm": 12.5,
            },
        },
        "rules": [
            {
                "id": "pilot_generic_fallback",
                "when": {},
                "assign": {
                    "e": {
                        "Regen_Delay": 2,
                        "Density": 1200,
                        "Util_DBH_cm": 12.5,
                    },
                    "f": {
                        "Regen_Delay": 1,
                        "Density": 1200,
                        "Util_DBH_cm": 12.5,
                    },
                },
                "notes": (
                    "Generic fallback for the public-data pilot. It is not a "
                    "local silviculture prescription."
                ),
            }
        ],
    }


def _pilot_readme(
    *,
    slug: str,
    file_id: str,
    label: str,
    area_ha: float,
    district: str,
    retrieved_at: str,
    boundary_rel: str,
    aac_m3: float | None = None,
) -> str:
    aac_text = f"{aac_m3:,.0f} m³/yr" if aac_m3 else "pending"
    return f"""# {label} pilot

| Field | Value |
| --- | --- |
| Woodlot file ID | `{file_id}` |
| Slug | `{slug}` |
| Area | {area_ha:,.2f} ha |
| AAC | {aac_text} |
| Region | {district} |
| AOI | `{boundary_rel}` (EPSG:3005, layer `aoi`) |
| Source | BC Geographic Warehouse Forest Tenure Managed Licence |
| Retrieved | {retrieved_at} |

## Status

The workspace is scaffolded. Build status is recorded in
`docs/reports/p1-pilot.md`; the commands below are the reproducible chain.

## Build

```bash
export FEMIC_SHARED_DATA_ROOT=\\
  /srv/shared-data/gep/ws4/femic/external/femic-public-data/data
export PYTHONPATH=/srv/shared-data/gep/ws4/femic/src
ROOT=/srv/shared-data/gep/ws4/fresh-woodlots

# 0. Clip VRI and build the per-instance external data root
python $ROOT/scripts/prepare_vri.py \\
  --instance-root . --shared-root $FEMIC_SHARED_DATA_ROOT
export FEMIC_EXTERNAL_DATA_ROOT=$PWD/data/external

# 1. Inventory and VDYP curves
python -m femic run --instance-root . --run-config config/run_profile.{slug}.yaml

# 2. Managed TIPSY curves without Wine
python $ROOT/scripts/tipsy_bridge.py \\
  --instance-root . --tsa {file_id.lower()} \\
  --source /srv/shared-data/gep/iversen-jamie-msc-thesis/btc_install_wine/Database \\
  --catalog /srv/shared-data/gep/ws4/fresh-woodlots/data/tipsy/manifest.json \\
  --overrides config/species_overrides.yaml

# 3. Post-TIPSY bundle (no BatchTIPSY)
FEMIC_ALLOW_STALE_TIPSY_OUTPUT=1 python -m femic tsa post-tipsy \\
  --instance-root . --run-config config/run_profile.{slug}.yaml --tsa {file_id.lower()}

# 4. Patchworks interchange and WS4 compile
python -m femic export patchworks --instance-root . --tsa {file_id.lower()} \\
  --bundle-dir data/model_input_bundle --output-dir output/patchworks \\
  --ifm-mode legacy_binary --ifm-threshold -1
python $ROOT/scripts/prepare_thlb.py --instance-root .
python $ROOT/scripts/clip_fragments.py \\
  --instance-root .
ws4 build --xml output/patchworks/forestmodel.xml \\
  --fragments output/patchworks/fragments/fragments_clipped.shp \\
  --out ws4/build/compiled
ws4 validate --dataset ws4/build/compiled

# 5. Smoke schedule, geometry, and liquidation simulation
python $ROOT/scripts/prepare_ws4_runtime.py \\
  --instance-root .
ws4 simulate --dataset ws4/build/compiled \\
  --schedule ws4/schedules/earliest_cc.csv --years 100 \\
  --out ws4/runs/smoke_liquidation

# 6. AAC targets, search, and balanced baseline
python $ROOT/scripts/write_aac_targets.py \\
  --slug {slug} --output config/targets/evenflow_aac.yaml
ws4 optimize --dataset ws4/build/compiled \\
  --targets config/targets/evenflow_aac.yaml --years 100 \\
  --time-limit 00:02:00 --threads 8 --seed 42 --out ws4/runs/aac_search
ws4 simulate --dataset ws4/build/compiled \\
  --schedule ws4/runs/aac_search/schedule.csv --years 100 \\
  --out ws4/runs/aac_baseline
ws4 report --run ws4/runs/aac_baseline \\
  --targets config/targets/evenflow_aac.yaml

# 7. Serve
ws4 serve --dataset ws4/build/compiled --runs ws4/runs \\
  --geometry ws4/geometry/blocks.geojson --port 8799
```

For a non-numeric case code, FEMIC writes `03_input-tsa{file_id.lower()}.csv`
and `vdyp_* -tsa{file_id.lower()}.*`, while the post-TIPSY step looks for the
unprefixed case names. The bridge and the post-TIPSY step create the short
aliases. This is a FEMIC naming limitation, not a model assumption.

## Caveats

- The TIPSY config is a **provisional generic fallback**, not a local
  silviculture prescription. Replace it with public TSR/FSP or RESULTS/SPAR
  evidence before any operational use.
- `fresh-vdyp` 0.1.0 still uses the Windows console for full yield tables.
  This pilot records a time-boxed Wine exception while the Wine-free equation
  lane is developed.
- The AOI is the union of the public Schedule A and Schedule B polygons for
  this woodlot licence.
- FEMIC selects VRI polygons that intersect a custom boundary but does not
  clip them. The build clips the exported fragments to the AOI before WS4.
  The curves still come from the intersecting VRI polygons, so a pre-clipped
  VRI source is the next data fix.
- The AAC baseline uses the public issued woodlot listing and a short heuristic
  search. It is a planning scenario, not a statutory timber supply analysis.
- The run profile sets `selection.tsa` to the woodlot code as well as the boundary
  code. Current FEMIC normalizes an empty TSA list to the development default
  (`08`), which then conflicts with a custom boundary. This is a workaround;
  it should be removed when FEMIC treats custom boundaries as first-class.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pilots",
        type=Path,
        default=REPO_ROOT / "config" / "pilots.yaml",
        help="Pilot selection YAML",
    )
    parser.add_argument(
        "--boundaries",
        type=Path,
        default=REPO_ROOT / "data" / "boundaries" / "woodlot_boundaries.gpkg",
        help="Catalog GeoPackage",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=REPO_ROOT / "data" / "catalog" / "woodlot_catalog.json",
        help="Catalog JSON with retrieval metadata",
    )
    parser.add_argument(
        "--instances",
        type=Path,
        default=REPO_ROOT / "instances",
        help="Instance root",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=None,
        help="Limit to one or more slugs",
    )
    args = parser.parse_args(argv)

    selection = yaml.safe_load(args.pilots.read_text(encoding="utf-8"))
    pilots = selection.get("pilots", [])
    if not pilots:
        raise RuntimeError(f"No pilots found in {args.pilots}")
    if args.only:
        wanted = set(args.only)
        pilots = [pilot for pilot in pilots if pilot["slug"] in wanted]
        if not pilots:
            raise RuntimeError(f"No pilots matched --only {sorted(wanted)}")

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    retrieved_at = str(catalog.get("retrieved_at", ""))
    rows = {row["slug"]: row for row in catalog.get("woodlots", [])}
    boundaries = gpd.read_file(args.boundaries, layer="woodlot_boundaries")
    now = datetime.now(UTC).isoformat(timespec="seconds")

    manifest: list[dict[str, object]] = []
    for pilot in pilots:
        slug = str(pilot["slug"])
        file_id = str(pilot["file_id"]).upper()
        label = str(pilot["label"])
        if slug not in rows:
            raise RuntimeError(f"{slug} is not in the catalog")
        row = rows[slug]
        match = boundaries[boundaries["file_id"] == file_id]
        if match.empty:
            raise RuntimeError(f"{file_id} is not in {args.boundaries}")
        geometry = match.geometry.union_all()

        instance_root = args.instances / slug
        for relative in (
            "config/tipsy",
            "data/source/aoi",
            "output",
            "outputs",
            "plots",
            "runtime/logs",
            "tipsy_io/logs",
            "tipsy_io/scratch",
            "vdyp_io/logs",
            "vdyp_io/scratch",
        ):
            (instance_root / relative).mkdir(parents=True, exist_ok=True)
        aoi_dir = instance_root / "data" / "source" / "aoi"
        aoi_gpkg = aoi_dir / f"{slug}.gpkg"
        if aoi_gpkg.exists():
            aoi_gpkg.unlink()
        aoi = gpd.GeoDataFrame(
            {
                "slug": [slug],
                "file_id": [file_id],
                "display_name": [label],
                "area_ha": [round(float(geometry.area) / 10_000.0, 2)],
            },
            geometry=[geometry],
            crs=boundaries.crs,
        )
        aoi.to_file(aoi_gpkg, layer="aoi", driver="GPKG")
        aoi_geojson = aoi_dir / f"{slug}.geojson"
        if aoi_geojson.exists():
            aoi_geojson.unlink()
        aoi.to_crs("EPSG:4326").to_file(aoi_geojson, driver="GeoJSON")

        run_profile = instance_root / "config" / f"run_profile.{slug}.yaml"
        _write_yaml(run_profile, _run_profile(slug, file_id))
        overrides = {
            str(key).strip().upper(): str(value).strip().upper()
            for key, value in (pilot.get("species_code_overrides") or {}).items()
        }
        tipsy = instance_root / "config" / "tipsy" / f"{file_id.lower()}.yaml"
        _write_yaml(tipsy, _tipsy_config(file_id, now, overrides))
        _write_yaml(
            instance_root / "config" / "species_overrides.yaml",
            {"species_code_overrides": overrides},
        )

        boundary_rel = str(aoi_gpkg.relative_to(instance_root))
        readme = instance_root / "README.md"
        readme.write_text(
            _pilot_readme(
                slug=slug,
                file_id=file_id,
                label=label,
                area_ha=float(row["area_ha"]),
                district=str(row.get("district", "")),
                retrieved_at=retrieved_at,
                boundary_rel=boundary_rel,
                aac_m3=(
                    float(row["aac_m3"])
                    if row.get("aac_m3") is not None
                    and not pd.isna(row.get("aac_m3"))
                    else None
                ),
            ),
            encoding="utf-8",
        )

        manifest.append(
            {
                "slug": slug,
                "file_id": file_id,
                "label": label,
                "area_ha": row["area_ha"],
                "instance_root": str(instance_root.relative_to(REPO_ROOT)),
                "aoi": str(aoi_gpkg.relative_to(REPO_ROOT)),
                "aoi_sha256": _sha256(aoi_gpkg),
                "aoi_geojson": str(aoi_geojson.relative_to(REPO_ROOT)),
                "run_profile": str(run_profile.relative_to(REPO_ROOT)),
                "tipsy_config": str(tipsy.relative_to(REPO_ROOT)),
                "status": "aoi_frozen",
                "rationale": pilot.get("rationale", ""),
            }
        )

    manifest_path = args.instances / "pilot_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    prior_entries: dict[str, dict[str, object]] = {}
    if manifest_path.exists():
        try:
            prior = json.loads(manifest_path.read_text(encoding="utf-8"))
            prior_entries = {
                str(entry.get("slug")): entry
                for entry in prior.get("pilots", [])
                if entry.get("slug")
            }
        except (json.JSONDecodeError, OSError):
            prior_entries = {}
    merged = {**prior_entries, **{str(entry["slug"]): entry for entry in manifest}}
    merged_entries = sorted(
        merged.values(), key=lambda entry: str(entry.get("file_id", ""))
    )
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": now,
                "source_catalog": str(args.catalog.relative_to(REPO_ROOT)),
                "source_retrieved_at": retrieved_at,
                "pilots": merged_entries,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Prepared {len(manifest)} pilot workspaces")
    for entry in manifest:
        print(
            f"  {entry['slug']}: {entry['area_ha']:,.2f} ha -> "
            f"{entry['instance_root']}"
        )
    print(f"  manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
