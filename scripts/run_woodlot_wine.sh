#!/usr/bin/env bash
# Launch Woodlot for Windows 4.4 from the project-local Wine prefix.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export WINEPREFIX="${WINEPREFIX:-$ROOT/data/wine/woodlot}"
export WINEDEBUG="${WINEDEBUG:--all}"
APP="$WINEPREFIX/drive_c/Program Files (x86)/Woodlot for Windows 4.4/Woodlot/Woodlot4.exe"

if [[ ! -f "$APP" ]]; then
  echo "Woodlot is not installed at: $APP" >&2
  echo "See docs/W4W-WINE.md for install steps." >&2
  exit 1
fi

if [[ -z "${DISPLAY:-}" ]]; then
  export DISPLAY=:99
  if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
    Xvfb "$DISPLAY" -screen 0 1600x1000x24 >/tmp/woodlot-xvfb.log 2>&1 &
    sleep 2
  fi
fi

cd "$(dirname "$APP")"
exec wine "$(basename "$APP")"
