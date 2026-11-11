#!/usr/bin/env python3
"""Regenerate the Markdown index from the document-library JSON manifest."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LIB = REPO_ROOT / "data" / "library" / "woodlot"


def main() -> int:
    payload = json.loads((LIB / "index.json").read_text(encoding="utf-8"))
    lines = [
        "# Woodlot document library",
        "",
        f"Generated: {payload.get('generated_at', '')}",
        "",
        "All files are local copies of publicly linked BC government documents.",
        "See `LICENSE-NOTES.md` before redistributing anything.",
        "",
        "## Search",
        "",
        "```bash",
        "python scripts/search_doc_library.py --query \"allowable annual cut\"",
        "rg -n -i \"allowable annual cut\" data/library/woodlot/text",
        "```",
        "",
        "## Index",
        "",
    ]
    current = None
    for record in payload.get("documents", []):
        category = str(record.get("category"))
        if category != current:
            current = category
            lines += [
                "",
                f"### {category}",
                "",
                "| Document | Local file | Text | Source |",
                "|---|---|---|---|",
            ]
        lines.append(
            f"| {record.get('title')} | `{record.get('path')}` |"
            f" `{record.get('text')}` | {record.get('url') or '—'} |"
        )
    if payload.get("failed"):
        lines += ["", "## Failed downloads", "", "| URL | Error |", "|---|---|"]
        for item in payload["failed"]:
            lines.append(f"| {item.get('url')} | {item.get('error')} |")
    (LIB / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {LIB / 'INDEX.md'} ({len(payload.get('documents', []))} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
