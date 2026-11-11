#!/usr/bin/env python3
"""Search the extracted text in the local woodlot document library.

# ruff: noqa: E501
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LIB = REPO_ROOT / "data" / "library" / "woodlot"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--context", type=int, default=1)
    parser.add_argument("--category", default=None)
    parser.add_argument("--regex", action="store_true")
    args = parser.parse_args(argv)

    index_path = LIB / "index.json"
    if not index_path.exists():
        raise SystemExit(f"library index not found: {index_path}")
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    by_text = {
        str(record.get("text")): record
        for record in payload.get("documents", [])
        if record.get("text")
    }
    pattern = re.compile(args.query if args.regex else re.escape(args.query), re.I)
    matches = 0
    for text_path in sorted((LIB / "text").rglob("*.txt")):
        rel = str(text_path.relative_to(LIB))
        record = by_text.get(rel, {})
        if args.category and record.get("category") != args.category:
            continue
        lines = text_path.read_text(encoding="utf-8", errors="replace").splitlines()
        for number, line in enumerate(lines, 1):
            match = pattern.search(line)
            if not match:
                continue
            matches += 1
            print(f"\n{record.get('title', text_path.stem)}  [{record.get('category', '?')}]")
            print(f"  {text_path}:{number}")
            start = max(0, number - 1 - args.context)
            end = min(len(lines), number + args.context)
            for position in range(start, end):
                text = lines[position].strip()
                if len(text) > 700:
                    anchor = match.start() if position + 1 == number else 0
                    left = max(0, anchor - 280)
                    right = min(len(text), anchor + 420)
                    text = f"...{text[left:right]}..."
                marker = ">" if position + 1 == number else " "
                print(f"  {marker} {position + 1}: {text}")
            if matches >= args.limit:
                print(f"\nStopped at {args.limit} matches.")
                return 0
    print(f"\n{matches} matches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
