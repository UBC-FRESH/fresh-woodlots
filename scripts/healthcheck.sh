#!/usr/bin/env bash
# Check the portal health, instance count, and a mounted app.
#
# Local:
#   scripts/healthcheck.sh http://127.0.0.1:8795
#
# Cloudflare Access protected:
#   CF_ACCESS_CLIENT_ID=... CF_ACCESS_CLIENT_SECRET=... \
#     scripts/healthcheck.sh https://fresh-woodlots.01101.dev
set -euo pipefail

BASE="${1:-http://127.0.0.1:8795}"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

curl_args=(-sS -o "$TMP" -w '%{http_code}')
if [[ -n "${CF_ACCESS_CLIENT_ID:-}" && -n "${CF_ACCESS_CLIENT_SECRET:-}" ]]; then
  curl_args+=(
    -H "CF-Access-Client-Id: $CF_ACCESS_CLIENT_ID"
    -H "CF-Access-Client-Secret: $CF_ACCESS_CLIENT_SECRET"
  )
fi

fetch() {
  local path="$1"
  local code
  code="$(curl "${curl_args[@]}" "$BASE$path")"
  if [[ "$code" == "302" ]]; then
    echo "Access protected: $BASE$path redirects to Cloudflare Access." >&2
    echo "Set CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET, or run" >&2
    echo "the check against the container-local URL." >&2
    exit 2
  fi
  if [[ "$code" != "200" ]]; then
    echo "FAIL $path -> $code" >&2
    exit 1
  fi
}

fetch /health
python3 - "$TMP" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1]))
if payload.get("status") != "ok":
    raise SystemExit(f"health status is not ok: {payload}")
buildable = payload.get("buildable")
if payload.get("instances") != 845 or buildable != 798:
    raise SystemExit(f"unexpected instance counts: {payload}")
if payload.get("ready", 0) > buildable:
    raise SystemExit(f"more ready instances than buildable: {payload}")
print(
    f"health ok: {payload['ready']}/{payload['instances']} built; "
    f"{buildable} buildable; {payload.get('pending_aac', 0)} AAC pending"
)
PY

fetch /api/instances
python3 - "$TMP" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1]))
rows = payload.get("instances", [])
ready = [row for row in rows if row.get("ready")]
if len(rows) != 845:
    raise SystemExit(f"expected 845 instances, got {len(rows)}")
print(f"instances ok: {len(rows)} catalogued, {len(ready)} built")
PY

for path in / /about /terms /privacy /instance/wl-w0026/; do
  fetch "$path"
  echo "ok $path"
done

echo "healthcheck passed: $BASE"
