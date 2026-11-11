#!/usr/bin/env bash
# Build one community-forest pilot instance end to end.
#
# Usage:
#   scripts/build_instance.sh cfa-k1e
#
# Run scripts/prepare_pilot.py first. The script stops before serving; the last
# lines print the serve command.
set -euo pipefail

SLUG="${1:-}"
if [[ -z "$SLUG" ]]; then
  echo "usage: $0 <slug>   (for example: cfa-k1e)" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTANCE="$ROOT/instances/$SLUG"
if [[ ! -d "$INSTANCE" ]]; then
  echo "missing instance: $INSTANCE" >&2
  echo "run: python scripts/prepare_pilot.py" >&2
  exit 1
fi
if [[ ! -d "$ROOT/data/downloads/proxy_thlb/provincial_pthlb.gdb" ]]; then
  echo "missing Provincial Proxy THLB: $ROOT/data/downloads/proxy_thlb" >&2
  echo "run: python scripts/fetch_thlb.py" >&2
  exit 1
fi

FEMIC_SRC="${FEMIC_SRC:-/srv/shared-data/gep/ws4/femic/src}"
FEMIC_SHARED_DATA_ROOT="${FEMIC_SHARED_DATA_ROOT:-/srv/shared-data/gep/ws4/femic/external/femic-public-data/data}"
TIPSY_DATABASE="${TIPSY_DATABASE:-/srv/shared-data/gep/iversen-jamie-msc-thesis/btc_install_wine/Database}"
TIPSY_CATALOG="${TIPSY_CATALOG:-$ROOT/data/tipsy/manifest.json}"
if [[ "${FEMIC_ALLOW_PARTIAL_BUNDLE:-0}" == "1" ]]; then
  export PYTHONPATH="$ROOT/scripts/femic_partial:$FEMIC_SRC${PYTHONPATH:+:$PYTHONPATH}"
else
  export PYTHONPATH="$FEMIC_SRC${PYTHONPATH:+:$PYTHONPATH}"
fi

FILE_ID="$(python3 - "$ROOT" "$SLUG" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1]); slug = sys.argv[2]
manifest = root / "instances" / "pilot_manifest.json"
if manifest.exists():
    for entry in json.loads(manifest.read_text()).get("pilots", []):
        if entry.get("slug") == slug:
            print(entry["file_id"])
            raise SystemExit
queue = json.loads((root / "queue" / "woodlot_build_queue.json").read_text())
for item in queue.get("instances", []):
    if item.get("slug") == slug:
        print(item["file_id"])
        raise SystemExit
raise SystemExit(f"slug not in manifest or queue: {slug}")
PY
)"
LOWER="$(printf '%s' "$FILE_ID" | tr '[:upper:]' '[:lower:]')"
RUN_CONFIG="config/run_profile.$SLUG.yaml"
AAC="$(python3 - "$ROOT" "$SLUG" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1]); slug = sys.argv[2]
payload = json.loads((root / "queue" / "woodlot_build_queue.json").read_text())
for entry in payload.get("instances", []):
    if entry.get("slug") == slug:
        print(entry.get("aac_m3") or "")
        break
PY
)"

cd "$INSTANCE"
mkdir -p runtime/logs

echo "[1/10] preflight"
if [[ "${SKIP_UPSTREAM:-0}" == "1" ]]; then
  echo "salvage mode: reusing existing VRI, VDYP, and bundle artifacts"
  export FEMIC_EXTERNAL_DATA_ROOT="$INSTANCE/data/external"
else
  python3 "$ROOT/scripts/prepare_vri.py" \
    --instance-root . \
    --shared-root "$FEMIC_SHARED_DATA_ROOT"
  export FEMIC_EXTERNAL_DATA_ROOT="$INSTANCE/data/external"
  python3 -m femic prep validate-case \
    --instance-root . \
    --run-config "$RUN_CONFIG" \
    --tipsy-config-dir config/tipsy

  echo "[2/10] inventory and VDYP curves"
  # The legacy run also invokes 01b. Remove the previous managed-curve output so
  # 01b uses its empty-yield path; the fresh-tipsy bridge writes the real table
  # in step 4.
  rm -f "data/04_output-tsa$LOWER.csv" "data/04_output-$LOWER.csv"
  python3 -m femic run --instance-root . --run-config "$RUN_CONFIG"
fi

echo "[3/10] short-name aliases for non-numeric case code $LOWER"
[[ -e "data/03_input-$LOWER.csv" ]] || \
  ln -s "03_input-tsa$LOWER.csv" "data/03_input-$LOWER.csv"
[[ -e "data/vdyp_prep-$LOWER.pkl" ]] || \
  ln -s "vdyp_prep-tsa$LOWER.pkl" "data/vdyp_prep-$LOWER.pkl"
[[ -e "data/vdyp_curves_smooth-$LOWER.feather" ]] || \
  ln -s "vdyp_curves_smooth-tsa$LOWER.feather" "data/vdyp_curves_smooth-$LOWER.feather"
[[ -e "data/vdyp_ply-$LOWER.feather" ]] || \
  ln -s "vdyp_ply-tsa$LOWER.feather" "data/vdyp_ply-$LOWER.feather"
[[ -e "data/vdyp_lyr-$LOWER.feather" ]] || \
  ln -s "vdyp_lyr-tsa$LOWER.feather" "data/vdyp_lyr-$LOWER.feather"

echo "[4/10] managed curves with fresh-tipsy (no BatchTIPSY)"
python3 "$ROOT/scripts/tipsy_bridge.py" \
  --instance-root . \
  --tsa "$LOWER" \
  --source "$TIPSY_DATABASE" \
  --catalog "$TIPSY_CATALOG" \
  --overrides config/species_overrides.yaml

echo "[5/10] post-TIPSY bundle"
FEMIC_ALLOW_STALE_TIPSY_OUTPUT=1 python3 -m femic tsa post-tipsy \
  --instance-root . \
  --run-config "$RUN_CONFIG" \
  --tsa "$LOWER"

echo "[6/10] Patchworks interchange and WS4 compile"
python3 -m femic export patchworks \
  --instance-root . \
  --tsa "$LOWER" \
  --bundle-dir data/model_input_bundle \
  --output-dir output/patchworks \
  --ifm-mode legacy_binary \
  --ifm-threshold -1
python3 "$ROOT/scripts/prepare_thlb.py" --instance-root .
python3 "$ROOT/scripts/clip_fragments.py" --instance-root .
ws4 build \
  --xml output/patchworks/forestmodel.xml \
  --fragments output/patchworks/fragments/fragments_clipped.shp \
  --out ws4/build/compiled
ws4 validate --dataset ws4/build/compiled

echo "[7/10] smoke schedule and map geometry"
python3 "$ROOT/scripts/prepare_ws4_runtime.py" --instance-root .

echo "[8/10] smoke liquidation simulation"
ws4 simulate \
  --dataset ws4/build/compiled \
  --schedule ws4/schedules/earliest_cc.csv \
  --years 100 \
  --out ws4/runs/smoke_liquidation
ws4 report --run ws4/runs/smoke_liquidation || true

echo "[9/10] AAC targets, search, and balanced baseline"
AAC_SEARCH_TIME="${AAC_SEARCH_TIME:-00:02:00}"
OPT_THREADS="${OPT_THREADS:-8}"
python3 "$ROOT/scripts/write_aac_targets.py" \
  --slug "$SLUG" \
  --output config/targets/evenflow_aac.yaml \
  --upper-factor 1.2
ws4 optimize \
  --dataset ws4/build/compiled \
  --targets config/targets/evenflow_aac.yaml \
  --threads "$OPT_THREADS" \
  --time-limit "$AAC_SEARCH_TIME" \
  --years 100 \
  --seed 42 \
  --seed-greedy \
  --out ws4/runs/aac_search
ws4 simulate \
  --dataset ws4/build/compiled \
  --schedule ws4/runs/aac_search/schedule.csv \
  --years 100 \
  --out ws4/runs/aac_baseline
ws4 report \
  --run ws4/runs/aac_baseline \
  --targets config/targets/evenflow_aac.yaml || true

echo "[9b/10] W4W base-scenario calibration"
python3 "$ROOT/scripts/calibrate_w4w_aac.py" \
  --slug "$SLUG" --quick --write-docs || \
  echo "warning: W4W calibration failed for $SLUG"

echo "[10/10] FHOPS operational pilot"
if [[ -n "$AAC" ]] && command -v fhops >/dev/null 2>&1 && [[ "${SKIP_FHOPS:-0}" != "1" ]]; then
  python3 "$ROOT/scripts/build_fhops_pilot.py" \
    --instance-root . \
    --aac "$AAC" \
    --daily-rate "${FHOPS_RATE:-150}" \
    --days "${FHOPS_DAYS:-300}"
  (
    cd fhops
    mkdir -p out
    fhops validate scenario.yaml
    fhops solve-heur scenario.yaml --out out/heur_solution.csv
    fhops evaluate scenario.yaml --assignments out/heur_solution.csv
  )
else
  echo "Skipping FHOPS: no AAC or fhops CLI not installed"
fi

echo
echo "Built $SLUG"
echo "Serve with:"
echo "  cd $INSTANCE && ws4 serve \\"
echo "    --dataset ws4/build/compiled --runs ws4/runs \\"
echo "    --geometry ws4/geometry/blocks.geojson --port 8795"
