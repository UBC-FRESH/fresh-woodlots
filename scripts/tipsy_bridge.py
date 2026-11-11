#!/usr/bin/env python3
"""Build a FEMIC-compatible ``04_output`` table with fresh-tipsy.

FEMIC's legacy pipeline stops at the BatchTIPSY handoff and expects a Windows
``TIPSYbtc.exe`` run under Wine to produce ``04_output-tsa<code>.csv``. This
bridge uses the public ``fresh-tipsy`` table engine instead, so the managed
curve stage needs no Windows process.

The bridge reads FEMIC's ``03_input`` CSV, selects the closest TIPSY table for
each feature, interpolates 10-year ages, and writes the transposed columns that
FEMIC's post-TIPSY parser understands:

``feature_id, MVcon_<age>, MVdec_<age>, HTcon_<age>, HTdec_<age>, gVol_<age>,
CC_<age>``

Ages beyond the source table are held at the table's last value; ages before
the source table are zero. Both choices are recorded in the sidecar manifest.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIPSY_SRC = Path(
    os.environ.get("FRESH_TIPSY_SRC", REPO_ROOT.parent / "fresh-tipsy" / "src")
)
if str(DEFAULT_TIPSY_SRC) not in sys.path:
    sys.path.insert(0, str(DEFAULT_TIPSY_SRC))

from fresh_tipsy.curves.engine import CurveEngine  # noqa: E402
from fresh_tipsy.curves.interpolation import interpolate_block  # noqa: E402
from fresh_tipsy.curves.metrics import build_curve_point  # noqa: E402
from fresh_tipsy.curves.models import (  # noqa: E402
    CurveQuery,
    Provenance,
    QueryResult,
    TableSelection,
)
from fresh_tipsy.tables.catalog import CatalogEntry, CatalogQuery  # noqa: E402

AGES: tuple[int, ...] = tuple(range(0, 351, 10))
BROADLEAF = {"AT", "AC", "ACT", "EP", "WB", "BW", "MB"}
PNC_PREFERENCE = ("N", "C", "P")


def _load_species_overrides(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    mapping = payload.get("species_code_overrides", payload)
    if not isinstance(mapping, dict):
        raise ValueError(f"Species overrides must be a mapping: {path}")
    return {
        str(key).strip().upper(): str(value).strip().upper()
        for key, value in mapping.items()
        if str(key).strip() and str(value).strip()
    }


def _first_nonzero_si(record: pd.Series) -> float:
    for column in record.index:
        if not str(column).endswith("_si"):
            continue
        value = pd.to_numeric(record[column], errors="coerce")
        if pd.notna(value) and float(value) > 0:
            return float(value)
    return 0.0


def _species_and_site(
    record: pd.Series, overrides: dict[str, str]
) -> tuple[str, str, float, int]:
    planted_pct = pd.to_numeric(record.get("planted_percent"), errors="coerce")
    planted_species = str(record.get("planted_species1") or "").strip()
    natural_species = str(record.get("natural_species1") or "").strip()
    use_planted = bool(planted_pct and planted_pct > 0 and planted_species)
    raw_species = planted_species if use_planted else natural_species
    if not raw_species:
        raw_species = planted_species or natural_species
    raw_code = raw_species.upper()
    mapped = overrides.get(raw_code, raw_code)
    si_column = f"{raw_code.lower()}_si"
    si_value = pd.to_numeric(record.get(si_column), errors="coerce")
    if pd.notna(si_value) and float(si_value) > 0:
        site_index = float(si_value)
    else:
        site_index = _first_nonzero_si(record)
    density_raw = (
        record.get("planted_density1")
        if use_planted
        else record.get("natural_density1")
    )
    density = pd.to_numeric(density_raw, errors="coerce")
    density_int = int(density) if pd.notna(density) and float(density) > 0 else 0
    return mapped, raw_code, site_index, density_int


def _prefer_pnc(entries: list[CatalogEntry]) -> list[CatalogEntry]:
    for pnc in PNC_PREFERENCE:
        subset = [entry for entry in entries if entry.pnc == pnc]
        if subset:
            return subset
    return entries


def _choose_entry(
    entries: list[CatalogEntry], site_index: float
) -> tuple[CatalogEntry, float]:
    if not entries:
        raise ValueError("No TIPSY table entries available for the species")
    exact = [
        entry
        for entry in entries
        if entry.site_from <= site_index <= entry.site_to
    ]
    if exact:
        entry = min(
            exact, key=lambda item: (item.site_to - item.site_from, item.asset_id)
        )
        return entry, site_index
    entry = min(
        entries,
        key=lambda item: min(
            abs(site_index - item.site_from), abs(site_index - item.site_to)
        ),
    )
    clamped = min(max(site_index, float(entry.site_from)), float(entry.site_to))
    return entry, clamped


def _closest_block(table: object, density: int) -> tuple[int, object]:
    blocks = [
        (index, block)
        for index, block in enumerate(table.blocks)  # type: ignore[attr-defined]
        if block.treatment is None
    ]
    if not blocks:
        raise ValueError("TIPSY table has no untreated blocks")
    if density <= 0:
        return blocks[0]
    return min(blocks, key=lambda item: abs(item[1].marker.initial_density - density))


def _curve_values(
    *,
    engine: CurveEngine,
    entry: CatalogEntry,
    site_index: float,
    density: int,
    species: str,
) -> dict[str, float]:
    if site_index <= 0:
        raise ValueError(f"No usable site index for species {species}")
    query = CurveQuery(species_code=entry.species_code, site_index=site_index, age=1)
    selection = TableSelection(
        entry=entry,
        query=query,
        provenance=Provenance.from_entry(entry),
        rationale="fresh-tipsy bridge selection",
    )
    table = engine.load_table(selection)
    block_index, block = _closest_block(table, density)
    first_age = float(entry.first_age or 1.0)
    last_age = float(entry.last_age or first_age)

    values: dict[str, float] = {}
    for age in AGES:
        if age < first_age:
            mv = gross = height = crown = 0.0
        else:
            query_age = min(max(float(age), first_age), last_age)
            row = interpolate_block(block, block_index, query_age)
            point = build_curve_point(QueryResult(selection=selection, row=row))
            mv = float(point.volume_merch_m3_ha or 0.0)
            gross = float(point.volume_gross_m3_ha or 0.0)
            height = float(point.height_site_m or 0.0)
            crown = float(point.crown_cover_pct or 0.0)
        values[f"MVcon_{age}"] = mv if species not in BROADLEAF else 0.0
        values[f"MVdec_{age}"] = mv if species in BROADLEAF else 0.0
        values[f"HTcon_{age}"] = height if species not in BROADLEAF else 0.0
        values[f"HTdec_{age}"] = height if species in BROADLEAF else 0.0
        values[f"gVol_{age}"] = gross
        values[f"CC_{age}"] = crown
    return values


def _ensure_case_input(instance_root: Path, tsa: str) -> None:
    data_root = instance_root / "data"
    case_input = data_root / f"03_input-{tsa}.csv"
    tsa_input = data_root / f"03_input-tsa{tsa}.csv"
    if case_input.exists():
        return
    if tsa_input.exists():
        case_input.symlink_to(tsa_input.name)
        print(f"Linked {case_input.name} -> {tsa_input.name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-root", type=Path, required=True)
    parser.add_argument("--tsa", required=True, help="FEMIC case code, e.g. k1e")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=REPO_ROOT / "data" / "tipsy" / "manifest.json",
        help="fresh-tipsy manifest",
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="TIPSY Database directory used to read source .tab tables",
    )
    parser.add_argument(
        "--overrides",
        type=Path,
        default=None,
        help="YAML with species_code_overrides (default: none)",
    )
    parser.add_argument(
        "--fresh-tipsy-src",
        type=Path,
        default=DEFAULT_TIPSY_SRC,
        help="fresh-tipsy src directory",
    )
    args = parser.parse_args(argv)

    if str(args.fresh_tipsy_src) not in sys.path:
        sys.path.insert(0, str(args.fresh_tipsy_src))

    instance_root = args.instance_root.resolve()
    _ensure_case_input(instance_root, args.tsa)
    input_path = instance_root / "data" / f"03_input-{args.tsa}.csv"
    output_path = instance_root / "data" / f"04_output-tsa{args.tsa}.csv"
    sidecar_path = instance_root / "data" / f"04_output-tsa{args.tsa}.provenance.json"

    overrides = _load_species_overrides(args.overrides)
    engine = CurveEngine.from_manifest(args.catalog, source_root=args.source)
    frame = pd.read_csv(input_path)
    if "feature_id" not in frame.columns:
        raise ValueError(f"Input CSV has no feature_id column: {input_path}")

    rows: list[dict[str, object]] = []
    provenance_rows: list[dict[str, object]] = []
    for record in frame.to_dict(orient="records"):
        series = pd.Series(record)
        species, raw_species, site_index, density = _species_and_site(
            series, overrides
        )
        entries = _prefer_pnc(
            list(
                engine.catalog.search(
                    CatalogQuery(species_code=species, format="tab")
                )
            )
        )
        surrogate = None
        if not entries:
            candidates = (
                ("AT",)
                if species in BROADLEAF
                else ("SW", "FDC", "PLI", "AT")
            )
            for candidate in candidates:
                candidate_entries = _prefer_pnc(
                    list(
                        engine.catalog.search(
                            CatalogQuery(species_code=candidate, format="tab")
                        )
                    )
                )
                if candidate_entries:
                    entries = candidate_entries
                    surrogate = candidate
                    break
        try:
            entry, clamped_si = _choose_entry(entries, site_index)
        except ValueError as exc:
            raise ValueError(
                f"feature {series['feature_id']}: raw={raw_species} "
                f"mapped={species}: {exc}"
            ) from exc
        mapped_species = surrogate or species
        values = _curve_values(
            engine=engine,
            entry=entry,
            site_index=clamped_si,
            density=density,
            species=mapped_species,
        )
        rows.append({"feature_id": int(series["feature_id"]), **values})
        provenance_rows.append(
            {
                "feature_id": int(series["feature_id"]),
                "raw_species": raw_species,
                "mapped_species": mapped_species,
                "surrogate": surrogate,
                "requested_site_index": site_index,
                "used_site_index": clamped_si,
                "requested_density": density,
                "table": entry.asset_id,
                "table_source": entry.relative_path,
                "table_sha256": entry.sha256,
                "table_first_age": entry.first_age,
                "table_last_age": entry.last_age,
                "age_rule": "zero before first_age; hold last value after last_age",
            }
        )

    output = pd.DataFrame(rows)
    output.to_csv(output_path, index=False)
    sidecar_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "workflow": "fresh-tipsy -> FEMIC 04_output bridge",
                "input": str(input_path),
                "output": str(output_path),
                "catalog": str(args.catalog),
                "source": str(args.source),
                "overrides": overrides,
                "ages": list(AGES),
                "features": provenance_rows,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {len(output)} feature rows to {output_path}")
    print(f"Wrote provenance to {sidecar_path}")
    for item in provenance_rows:
        print(
            f"  {item['feature_id']}: {item['raw_species']} -> "
            f"{item['mapped_species']} SI {item['requested_site_index']:.1f} "
            f"(used {item['used_site_index']:.1f}) table {item['table']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
