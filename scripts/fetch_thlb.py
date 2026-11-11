#!/usr/bin/env python3
"""Download and extract the Provincial Proxy THLB file geodatabase."""

from __future__ import annotations

import argparse
import shutil
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
URL = "https://coms.api.gov.bc.ca/api/v1/object/28d59553-b76c-4c02-86c7-f1c7efe65b26"
DEFAULT_DEST = REPO_ROOT / "data" / "downloads"
GDB_NAME = "provincial_pthlb.gdb"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--url", default=URL)
    args = parser.parse_args(argv)

    dest = args.dest
    dest.mkdir(parents=True, exist_ok=True)
    gdb = dest / "proxy_thlb" / GDB_NAME
    if gdb.exists():
        print(f"Proxy THLB already present: {gdb}")
        return 0

    archive = dest / "proxy_thlb.zip"
    print(f"Downloading {args.url}")
    with urllib.request.urlopen(args.url, timeout=600) as response:
        with archive.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    print(f"Extracting to {dest / 'proxy_thlb'}")
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(dest / "proxy_thlb")
    print(f"Proxy THLB ready: {gdb}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
