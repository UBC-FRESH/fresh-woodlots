#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
exec uvicorn portal.app:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8795}"
