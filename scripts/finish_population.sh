#!/usr/bin/env bash
# Finish the population after the build and FHOPS background jobs stop.
#
# Run only when no batch_build.py / batch_fhops.py process is active.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if pgrep -f 'batch_build.py|batch_fhops.py' >/dev/null 2>&1; then
  echo "A build or FHOPS batch is still running; try again when it completes." >&2
  exit 1
fi

echo "[1/7] sync queue"
python3 scripts/sync_queue.py

echo "[2/7] calibrate any built instance without a calibration"
python3 scripts/calibrate_all.py --jobs 8

echo "[3/7] FHOPS for built instances without summaries"
python3 scripts/batch_fhops.py --jobs 8

if [[ "${RUN_FEATURED_TENYEAR:-0}" == "1" ]]; then
  echo "[3b/7] ten-year FHOPS for featured pilots"
  python3 scripts/build_fhops_tenyear.py \
    --only wl-w1548 --only wl-w2023 --iterations 800
fi

if [[ "${RUN_FEATURED_PARETO:-0}" == "1" ]]; then
  echo "[3c/7] Pareto sweeps for featured pilots"
  python3 scripts/build_pareto_sweep.py \
    --only wl-w1548 --only wl-w2023 \
    --factors 0.85,1.00,1.15 --seeds 1 --iterations 30
fi

echo "[4/7] regenerate scenarios for all built instances"
python3 scripts/prepare_demo.py

echo "[5/7] rebuild the calibration register"
python3 scripts/build_calibration_register.py

echo "[6/7] restart the portal"
sudo systemctl restart freshwl-portal
sleep 10
scripts/healthcheck.sh http://127.0.0.1:8795

echo "[7/7] rebuild and publish the Sphinx docs"
(
  cd docs
  /home/gep/.venv/bin/sphinx-build -W --keep-going -b html . _build/html
)
git add docs/aac/CALIBRATION-REGISTER.md docs/aac/CALIBRATION-REGISTER.csv docs/library/woodlot-INDEX.md
git diff --cached --quiet || git commit -m "Update W4W calibration register after population build"
git push origin main

echo "Done."
