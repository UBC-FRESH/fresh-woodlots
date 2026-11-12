#!/usr/bin/env python3
"""HTTP and artifact QA for every built woodlot portal instance."""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "queue" / "woodlot_build_queue.json"
DEFAULT_BASE = "http://127.0.0.1:8795"
OUT_MD = REPO_ROOT / "docs" / "QA-POPULATION.md"
OUT_JSON = REPO_ROOT / "docs" / "reports" / "release-candidate-qa.json"
PATHS = (
    "/fhops/{slug}",
    "/fhops/{slug}/studio",
    "/fhops/{slug}/theatre",
    "/fhops/{slug}/scheduled.geojson",
    "/fhops/{slug}/timeline.json",
    "/fhops/{slug}/theatre.json",
)
LOCAL_FILES = (
    "fhops/summary.json",
    "fhops/out/scheduled_blocks.geojson",
    "fhops/out/timeline.json",
    "fhops/out/theatre.json",
    "config/w4w_calibration.json",
)


def get(
    base: str, path: str, timeout: float = 20.0, method: str = "GET"
) -> tuple[int, bytes]:
    request = Request(
        base + path,
        data=b"{}" if method == "POST" else None,
        method=method,
        headers={
            "User-Agent": "woodlots-qa/1.0",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()
    except (URLError, TimeoutError, OSError) as error:
        return 0, str(error).encode("utf-8", "replace")


def check_instance(base: str, slug: str) -> dict[str, object]:
    root = REPO_ROOT / "instances" / slug
    result: dict[str, object] = {"slug": slug, "failures": []}
    failures: list[str] = result["failures"]  # type: ignore[assignment]
    for relative in LOCAL_FILES:
        path = root / relative
        if not path.is_file():
            failures.append(f"missing {relative}")
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            failures.append(f"bad {relative}: {error}")
            continue
        if relative.endswith("summary.json"):
            if not float(payload.get("total_production_m3") or 0) > 0:
                failures.append("summary has no production")
        if relative.endswith("scheduled_blocks.geojson"):
            if not payload.get("features"):
                failures.append("scheduled blocks empty")
        if relative.endswith("timeline.json"):
            if not payload.get("events"):
                failures.append("timeline events empty")
        if relative.endswith("theatre.json"):
            if not payload.get("blocks"):
                failures.append("theatre blocks empty")
        if relative.endswith("w4w_calibration.json"):
            case = (payload.get("cases") or {}).get("all_vri") or {}
            if not isinstance(case.get("thlb_factor"), (int, float)):
                failures.append("calibration factor missing")
    for template in PATHS:
        path = template.format(slug=slug)
        status, body = get(base, path)
        if status != 200:
            failures.append(f"HTTP {status} {path}")
            continue
        if path.endswith(".json") or path.endswith(".geojson"):
            try:
                json.loads(body)
            except json.JSONDecodeError:
                failures.append(f"invalid JSON {path}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--jobs", type=int, default=16)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    slugs = [
        str(entry["slug"])
        for entry in queue.get("instances", [])
        if entry.get("status") == "built"
    ]
    if args.limit:
        slugs = slugs[: args.limit]
    started = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as executor:
        futures = {
            executor.submit(check_instance, args.base, slug): slug for slug in slugs
        }
        for index, future in enumerate(as_completed(futures), start=1):
            results.append(future.result())
            if index % 100 == 0:
                print(f"checked {index}/{len(slugs)}", flush=True)
    results.sort(key=lambda item: str(item["slug"]))
    failures = [item for item in results if item["failures"]]
    health_status, health_body = get(args.base, "/health")
    health = {}
    if health_status == 200:
        try:
            health = json.loads(health_body)
        except json.JSONDecodeError:
            health = {}
    read_only = bool(health.get("read_only"))
    write_checks = []
    if read_only:
        for path in (
            "/instance/wl-w0026/api/runs",
            "/treelab/api/cases/w0026-61/run",
        ):
            status, _ = get(args.base, path, method="POST")
            write_checks.append({"path": path, "status": status})
            if status != 403:
                failures.append(
                    {
                        "slug": "read-only-guard",
                        "failures": [f"POST {path} returned {status}, expected 403"],
                    }
                )
    elapsed = time.time() - started
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base": args.base,
        "instances": len(results),
        "failures": len(failures),
        "elapsed_s": round(elapsed, 1),
        "checks": len(PATHS) + len(LOCAL_FILES),
        "read_only": read_only,
        "write_checks": write_checks,
        "health": health,
        "results": results,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Release-candidate QA",
        "",
        f"Generated: `{payload['generated_at']}`  ",
        f"Base URL: `{args.base}`  ",
        f"Built instances checked: **{len(results)}**  ",
        f"Checks per instance: **{payload['checks']}**  ",
        f"Read-only mode: **{read_only}**  ",
        f"Write checks: **{len(write_checks)}**  ",
        f"Failures: **{len(failures)}**  ",
        f"Elapsed: **{elapsed:.1f}s**",
        "",
        "Each instance was checked for the FHOPS summary, scheduled blocks, "
        "timeline, theatre, W4W calibration, and six portal routes. In "
        "read-only mode, two POST endpoints are also checked for a **403**.",
        "",
    ]
    if failures:
        lines += ["## Failures", "", "| Instance | Failures |", "|---|---|"]
        for item in failures:
            lines.append(
                f"| {item['slug']} | {'; '.join(item['failures'])} |"
            )
    else:
        lines += ["## Result", "", "All checks passed."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT_MD}")
    print(f"wrote {OUT_JSON}")
    print(f"{len(results)} instances, {len(failures)} failures, {elapsed:.1f}s")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
