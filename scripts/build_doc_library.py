#!/usr/bin/env python3
"""Build a searchable local library from the BC woodlot licence pages.

Long source URLs and table rows are intentionally kept on one line.
# ruff: noqa: E501

The library keeps the source HTML, the downloaded documents, extracted text,
and a JSON/Markdown index with source URLs and SHA256 hashes.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "data" / "library" / "woodlot"
RAW = LIB / "raw"
TEXT = LIB / "text"
PAGES = LIB / "pages"
USER_AGENT = "woodlot-doc-library/0.1 (+https://github.com/UBC-FRESH)"

SOURCES = [
    (
        "woodlot-licence",
        "https://www2.gov.bc.ca/gov/content/industry/forestry/forest-tenures/"
        "timber-harvesting-rights/woodlot-licence",
    ),
    (
        "aac-calculator",
        "https://www2.gov.bc.ca/gov/content/industry/forestry/forest-tenures/"
        "timber-harvesting-rights/woodlot-licence/allowable-annual-cut-calculator-tool",
    ),
]

EXTRA = [
    (
        "management-plan-handbook",
        "https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/"
        "forestry/timber-tenures/woodlots/woodlot_mngmt_plan_handbook.pdf",
    ),
    (
        "management-plan-template",
        "https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/"
        "forestry/timber-tenures/woodlots/wl_management_plan_template_accepted_jan_2009.doc",
    ),
    (
        "inventory-handbook",
        "https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/"
        "forestry/timber-tenures/woodlots/wl_inventory_handbook_version_1_final_1.pdf",
    ),
]

CONTENT_EXT = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/x-msi": ".msi",
    "application/octet-stream": "",
    "text/html": ".html",
    "video/x-ms-wmv": ".wmv",
    "application/zip": ".zip",
}


def _slug(text: str, fallback: str = "document") -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return text[:90] or fallback


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fetch(url: str, timeout: int = 180) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(), response.headers.get("Content-Type", "")


def _links(page_url: str, document: str) -> list[tuple[str, str]]:
    found: dict[str, str] = {}
    for match in re.finditer(
        r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>', document, re.S | re.I
    ):
        href = html.unescape(match.group(1)).strip()
        text = re.sub("<[^>]+>", " ", match.group(2))
        text = html.unescape(re.sub(r"\s+", " ", text)).strip()
        if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue
        url = urllib.parse.urljoin(page_url, href)
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            continue
        # Only direct documents, asset downloads, FTP documents, and legislation.
        candidate = (
            "/assets/" in parsed.path
            or "/ftp/" in parsed.path
            or "bclaws.gov.bc.ca/civix" in parsed.netloc + parsed.path
            or "forms.gov.bc.ca" in parsed.netloc
            or Path(parsed.path).suffix.lower()
            in {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".msi", ".zip", ".wmv"}
        )
        if not candidate:
            continue
        # Strip fragments for de-duplication; keep the first descriptive title.
        clean = urllib.parse.urlunparse(parsed._replace(fragment=""))
        if clean not in found or len(text) > len(found[clean]):
            found[clean] = text
    return sorted(found.items())


def _category(url: str, title: str) -> str:
    text = f"{url} {title}".lower()
    if "woodlot-for-windows" in text or "/aac" in text or "aac calculator" in text:
        return "aac-tool"
    if "bclaws.gov.bc.ca" in text:
        return "legislation"
    if "cut_control" in text or "cut-control" in text or "cut control" in text:
        return "cut-control"
    if "transfers/" in text or "rait" in text or "transfer" in text:
        return "transfers"
    if "first_nations" in text or "first nations" in text or "information_sharing" in text:
        return "first-nations"
    if "policy" in text or "policies" in text or "bulletin" in text:
        return "policy"
    if any(
        key in text
        for key in (
            "wlp_",
            "woodlot_licence_plan",
            "management_plan",
            "mngmt_plan",
            "inventory_handbook",
            "stocking",
            "plan template",
        )
    ):
        return "woodlot-planning"
    if ".wmv" in text:
        return "training"
    if ".msi" in text:
        return "software"
    return "other"


def _filename(url: str, title: str, content_type: str) -> str:
    parsed = urllib.parse.urlparse(url)
    base = urllib.parse.unquote(Path(parsed.path).name)
    stem = Path(base).stem
    suffix = Path(base).suffix.lower()
    if not base or base.lower() in {"download"} or len(stem) < 3:
        stem = _slug(title, "document")
        base = stem
    if not suffix:
        suffix = CONTENT_EXT.get(content_type.split(";")[0].strip().lower(), "")
        if not suffix:
            suffix = ".bin"
        base = stem + suffix
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-") or "document"
    return base


def _extract_text(raw: Path, out: Path, content_type: str) -> tuple[str, str]:
    suffix = raw.suffix.lower()
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        if suffix == ".pdf":
            result = subprocess.run(
                ["pdftotext", "-layout", str(raw), str(out)],
                capture_output=True,
                text=True,
                timeout=180,
            )
            if result.returncode != 0 or not out.exists() or out.stat().st_size < 20:
                subprocess.run(
                    ["pdftotext", str(raw), str(out)],
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
        elif suffix == ".docx":
            subprocess.run(
                ["pandoc", "-t", "plain", "--wrap=none", str(raw), "-o", str(out)],
                check=True,
                capture_output=True,
                timeout=120,
            )
        elif suffix == ".doc":
            result = subprocess.run(
                ["antiword", str(raw)],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                out.write_text(result.stdout, encoding="utf-8", errors="replace")
            else:
                strings = subprocess.run(
                    ["strings", str(raw)], capture_output=True, text=True, timeout=120
                )
                out.write_text(strings.stdout, encoding="utf-8", errors="replace")
        elif suffix in {".html", ".htm"}:
            text = raw.read_text(encoding="utf-8", errors="replace")
            text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.S | re.I)
            text = re.sub(r"<[^>]+>", " ", text)
            text = html.unescape(re.sub(r"\s+", " ", text))
            out.write_text(text, encoding="utf-8")
        elif suffix in {".xls", ".xlsx"}:
            import pandas as pd

            frame = pd.read_excel(raw, sheet_name=None)
            with out.open("w", encoding="utf-8") as handle:
                for sheet, data in frame.items():
                    handle.write(f"### sheet: {sheet}\n")
                    handle.write(data.to_csv(index=False))
                    handle.write("\n")
        else:
            return "", "not-text"
    except Exception as error:  # noqa: BLE001 - record extraction failure
        return "", f"error: {error}"
    if not out.exists():
        return "", "no-output"
    text = out.read_text(encoding="utf-8", errors="replace")
    return str(out.relative_to(LIB)), "ok" if len(text.strip()) > 20 else "empty"


def main() -> int:
    LIB.mkdir(parents=True, exist_ok=True)
    for directory in (RAW, TEXT, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, object]] = []
    seen: set[str] = set()
    failed: list[dict[str, str]] = []
    now = datetime.now(UTC).isoformat(timespec="seconds")

    links: list[tuple[str, str, str]] = []
    for slug, page_url in SOURCES:
        try:
            payload, content_type = _fetch(page_url)
            page_path = PAGES / f"{slug}.html"
            page_path.write_bytes(payload)
            page_text = PAGES / f"{slug}.txt"
            page_text.write_text(
                html.unescape(
                    re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", payload.decode("utf-8", "replace")))
                ),
                encoding="utf-8",
            )
            print(f"page {page_url} -> {page_path} ({len(payload)} bytes)")
            for url, title in _links(page_url, payload.decode("utf-8", "replace")):
                links.append((url, title, slug))
        except Exception as error:  # noqa: BLE001
            failed.append({"url": page_url, "error": str(error), "source": slug})
            print(f"page failed {page_url}: {error}")

    for slug, url in EXTRA:
        links.append((url, slug.replace("-", " ").title(), "extra"))

    # De-duplicate across pages, preserving the most descriptive title.
    unique: dict[str, tuple[str, str]] = {}
    for url, title, source in links:
        if url not in unique or len(title) > len(unique[url][0]):
            unique[url] = (title, source)

    for url, (title, source) in sorted(unique.items()):
        if url in seen:
            continue
        seen.add(url)
        category = _category(url, title)
        try:
            payload, content_type = _fetch(url)
            filename = _filename(url, title, content_type)
            destination = RAW / category / filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                destination = destination.with_name(
                    f"{destination.stem}-{hashlib.sha256(url.encode()).hexdigest()[:8]}"
                    f"{destination.suffix}"
                )
            destination.write_bytes(payload)
            text_rel, text_status = _extract_text(
                destination, TEXT / category / f"{destination.stem}.txt", content_type
            )
            record = {
                "title": title or filename,
                "source_page": source,
                "url": url,
                "category": category,
                "path": str(destination.relative_to(LIB)),
                "content_type": content_type,
                "bytes": len(payload),
                "sha256": _sha256(destination),
                "text": text_rel,
                "text_status": text_status,
                "status": "ok",
            }
            records.append(record)
            print(f"ok {category}/{filename} ({len(payload)} bytes, text={text_status})")
        except Exception as error:  # noqa: BLE001
            failed.append({"url": url, "error": str(error), "source": source})
            print(f"FAIL {url}: {error}")

    # Copy the W0026 dossier documents and index them as a special collection.
    w0026 = ROOT / "data" / "aac" / "w0026"
    if w0026.is_dir():
        dest = RAW / "woodlot-specific" / "W0026"
        dest.mkdir(parents=True, exist_ok=True)
        for path in sorted(w0026.glob("*.pdf")):
            target = dest / path.name
            if not target.exists():
                shutil.copy2(path, target)
            text_rel, text_status = _extract_text(
                target, TEXT / "woodlot-specific" / "W0026" / f"{target.stem}.txt", "application/pdf"
            )
            records.append(
                {
                    "title": f"W0026 {path.stem}",
                    "source_page": "W0026 dossier",
                    "url": "",
                    "category": "woodlot-specific",
                    "path": str(target.relative_to(LIB)),
                    "content_type": "application/pdf",
                    "bytes": target.stat().st_size,
                    "sha256": _sha256(target),
                    "text": text_rel,
                    "text_status": text_status,
                    "status": "ok",
                }
            )

    payload = {
        "schema_version": 1,
        "generated_at": now,
        "sources": [{"id": slug, "url": url} for slug, url in SOURCES],
        "count": len(records),
        "documents": sorted(records, key=lambda item: (str(item["category"]), str(item["title"]))),
        "failed": failed,
    }
    (LIB / "index.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lines = [
        "# Woodlot document library",
        "",
        f"Generated: {now}",
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
    for record in payload["documents"]:
        category = str(record["category"])
        if category != current:
            current = category
            lines += ["", f"### {category}", "", "| Document | Local file | Text | Source |", "|---|---|---|---|"]
        lines.append(
            f"| {record['title']} | `{record['path']}` | `{record['text']}` |"
            f" {record['url'] or '—'} |"
        )
    if failed:
        lines += ["", "## Failed downloads", "", "| URL | Error |", "|---|---|"]
        for item in failed:
            lines.append(f"| {item['url']} | {item['error']} |")
    (LIB / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"library: {LIB}")
    print(f"documents: {len(records)}; failed: {len(failed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
