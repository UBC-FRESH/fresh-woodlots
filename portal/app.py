"""Multi-instance portal for the BC woodlot licence pilots.

The portal is deliberately small: it discovers the built pilot instances,
renders a landing page with the key public-data facts, and mounts each WS4 web
application under ``/instance/<slug>``.
"""

from __future__ import annotations

import html
import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from markdown_it import MarkdownIt
from ws4.web.app import create_app

from .fhops_page import _fhops_page
from .fhops_studio import render_studio
from .fhops_theatre import render_theatre

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_READ_ONLY = os.environ.get("PUBLIC_READ_ONLY", "0") == "1"
DEMO_MODE = os.environ.get("DEMO_MODE", "0") == "1"
INSTANCES_ROOT = ROOT / "instances"
QUEUE_PATH = ROOT / "queue" / "woodlot_build_queue.json"
MARKDOWN = (
    MarkdownIt(
        "commonmark",
        {"html": False, "linkify": True, "typographer": True},
    )
    .enable("table")
    .enable("strikethrough")
)

SPECS: dict[str, dict[str, str]] = {
    "wl-w0026": {
        "file_id": "W0026",
        "label": "Chinook Woodlots",
        "subtitle": "Coastal woodlot · Campbell River",
    },
    "wl-w2023": {
        "file_id": "W2023",
        "label": "Boomer Enterprises",
        "subtitle": "Interior woodlot · Okanagan",
    },
    "wl-w1548": {
        "file_id": "W1548",
        "label": "Fibre Farms",
        "subtitle": "Northern woodlot · Prince George",
    },
}


@dataclass
class Instance:
    slug: str
    file_id: str
    label: str
    subtitle: str
    root: Path
    area_ha: float | None
    aac_m3: float | None
    thlb_ha: float | None
    thlb_fraction: float | None
    blocks: int | None
    runs: list[str]
    ready: bool
    reason: str = ""
    mount: str = ""
    partial: bool = False
    fhops: dict[str, object] | None = None
    w4w: dict[str, object] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "file_id": self.file_id,
            "label": self.label,
            "subtitle": self.subtitle,
            "area_ha": self.area_ha,
            "aac_m3": self.aac_m3,
            "thlb_ha": self.thlb_ha,
            "thlb_fraction": self.thlb_fraction,
            "blocks": self.blocks,
            "runs": self.runs,
            "ready": self.ready,
            "reason": self.reason,
            "mount": self.mount,
            "partial": self.partial,
            "fhops": self.fhops,
            "fhops_url": f"/fhops/{self.slug}" if self.fhops else None,
            "w4w": self.w4w,
        }


class LazyWS4:
    """Build a WS4 sub-application on first request.

    Mounting hundreds of WS4 apps at import time is expensive and mostly
    unnecessary: a visitor only opens one or two woodlots per session.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self._app: Any = None
        self._lock = threading.Lock()

    def _build(self) -> Any:
        if self._app is not None:
            return self._app
        with self._lock:
            if self._app is None:
                root = self.root
                targets = root / "config" / "targets" / "evenflow_aac.yaml"
                overview = (
                    root / "ws4" / "geometry" / "blocks_overview.geojson"
                )
                initial = (
                    root / "ws4" / "runs" / "aac_baseline" / "schedule.csv"
                )
                self._app = create_app(
                    dataset=root / "ws4" / "build" / "compiled",
                    runs=root / "ws4" / "runs",
                    targets=(
                        targets
                        if targets.exists() and not PUBLIC_READ_ONLY
                        else None
                    ),
                    initial_schedule=initial if initial.exists() else None,
                    allow_runs=DEMO_MODE and not PUBLIC_READ_ONLY,
                    geometry=root / "ws4" / "geometry" / "blocks.geojson",
                    geometry_overview=(
                        overview if overview.exists() else None
                    ),
                    crs="EPSG:4326",
                )
        return self._app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        await self._build()(scope, receive, send)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _queue_rows() -> dict[str, dict[str, Any]]:
    payload = _read_json(QUEUE_PATH)
    return {
        str(row.get("slug")): row
        for row in payload.get("instances", [])
        if row.get("slug")
    }


def _block_count(instance_root: Path) -> int | None:
    try:
        import pandas as pd

        frame = pd.read_parquet(
            instance_root / "ws4" / "build" / "compiled" / "blocks.parquet"
        )
    except Exception:
        return None
    return int(len(frame))


def discover() -> list[Instance]:
    """Return every woodlot in the queue, built or not.

    The queue is the authority: all 845 active licences appear on the portal,
    while only instances with a compiled WS4 dataset get a model link.
    """

    queue = _queue_rows()
    instances: list[Instance] = []
    for slug, row in sorted(
        queue.items(), key=lambda item: str(item[1].get("file_id") or item[0])
    ):
        root = INSTANCES_ROOT / slug
        spec = SPECS.get(slug)
        file_id = (
            spec["file_id"]
            if spec
            else str(row.get("file_id") or slug.split("-")[-1].upper())
        )
        label = (
            spec["label"]
            if spec
            else str(row.get("display_name") or file_id).title()
        )
        subtitle = spec["subtitle"] if spec else "Woodlot licence"
        thlb: dict[str, Any] = {}
        fhops: dict[str, Any] | None = None
        w4w: dict[str, Any] | None = None
        runs: list[str] = []
        dataset = root / "ws4" / "build" / "compiled"
        ready = False
        if root.is_dir():
            thlb = _read_json(
                root / "data" / "source" / "thlb" / "thlb.summary.json"
            )
            fhops = _read_json(root / "fhops" / "summary.json") or None
            w4w_payload = _read_json(root / "config" / "w4w_calibration.json")
            if w4w_payload:
                case = (w4w_payload.get("cases") or {}).get("all_vri") or {}
                factor = case.get("thlb_factor")
                w4w = {
                    "aac_m3": w4w_payload.get("published_aac_m3_per_year"),
                    "net_area_ha": case.get("net_area_ha"),
                    "thlb_factor": factor,
                    "max_even_flow_m3": case.get("max_even_flow_m3_per_year"),
                    "pct_proxy_thlb": case.get("netdown_vs_proxy_thlb"),
                    "warning": (
                        "method check"
                        if isinstance(factor, (int, float))
                        and (factor < 0.4 or factor > 2.0)
                        else ""
                    ),
                }
            runs_root = root / "ws4" / "runs"
            if runs_root.exists():
                runs = sorted(
                    path.name
                    for path in runs_root.iterdir()
                    if path.is_dir()
                    and not path.name.startswith(("pre_thlb", "pre_vri"))
                    and path.name not in {"archive", "scenarios"}
                )
            ready = dataset.is_dir() and (dataset / "manifest.json").exists()

        aac_value = row.get("aac_m3")
        try:
            aac_m3 = float(aac_value) if aac_value is not None else None
        except (TypeError, ValueError):
            aac_m3 = None
        area_value = row.get("area_ha")
        try:
            area_ha = float(area_value) if area_value is not None else None
        except (TypeError, ValueError):
            area_ha = None

        reason = ""
        if not ready:
            status = str(row.get("status") or "")
            if status == "pending_aac" or aac_m3 is None:
                reason = "AAC pending"
            elif status == "building":
                reason = "building"
            elif status == "failed":
                reason = "build failed"
            else:
                reason = "queued"

        instances.append(
            Instance(
                slug=slug,
                file_id=file_id,
                label=label,
                subtitle=subtitle,
                root=root,
                area_ha=area_ha,
                aac_m3=aac_m3,
                thlb_ha=thlb.get("thlb_ha"),
                thlb_fraction=thlb.get("thlb_fraction"),
                blocks=_block_count(root) if ready else None,
                runs=runs,
                ready=ready,
                reason=reason,
                partial=str(row.get("bundle", "")).lower() == "partial",
                fhops=fhops,
                w4w=w4w,
            )
        )
    return instances


app = FastAPI(title="Woodlots BC Planning Portal")

SOURCES_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sources &amp; methods · Woodlots BC Planning Portal</title>
  <style>
    :root { --ink: #17231f; --muted: #5b6b64; --line: #d8e0db;
            --paper: #f7faf7; --accent: #6b4f2a; }
    * { box-sizing: border-box; }
    body { margin: 0; color: var(--ink); background: var(--paper);
           font: 16px/1.6 system-ui, -apple-system, Segoe UI, sans-serif; }
    main { max-width: 900px; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; }
    a { color: var(--accent); }
    h1 { font-size: clamp(2rem, 4vw, 2.8rem); margin: .4rem 0 1rem; }
    h2 { margin: 2rem 0 .6rem; }
    .kicker { color: var(--accent); font-weight: 700; letter-spacing: .08em;
              text-transform: uppercase; font-size: .75rem; }
    .lede { color: var(--muted); font-size: 1.05rem; }
    table { width: 100%; border-collapse: collapse; margin: .8rem 0 1.5rem;
            background: #fff; font-size: .92rem; }
    th, td { text-align: left; padding: .55rem .65rem;
             border-bottom: 1px solid var(--line); vertical-align: top; }
    th { background: #eef4ef; font-size: .78rem; text-transform: uppercase;
         letter-spacing: .05em; }
    code { background: #eef4ef; padding: .1rem .3rem; border-radius: 4px; }
    ul { padding-left: 1.2rem; }
    .note { background: #fff8e8; border: 1px solid #f0dfb8;
            border-radius: 10px; padding: .9rem 1rem; }
    footer { margin-top: 2.5rem; padding-top: 1rem;
             border-top: 1px solid var(--line); color: var(--muted);
             font-size: .85rem; }
  </style>
</head>
<body>
<main>
  <p><a href="/">← Back to the portal</a></p>
  <p class="kicker">UBC FRESH · public-data pilot</p>
  <h1>Sources &amp; methods</h1>
  <p class="lede">Every woodlot licence instance in this portal is built
  from public data. The chain is reproducible: catalog, AOI, VRI clip, THLB
  split, FEMIC curves, WS4 compile, AAC search, and a first-period FHOPS
  operational pilot.</p>

  <h2>Data sources</h2>
  <table>
    <thead><tr><th>Dataset</th><th>Use</th><th>Licence</th></tr></thead>
    <tbody>
      <tr><td>Forest Tenure Managed Licence<br>
        <code>WHSE_FOREST_TENURE.FTEN_MANAGED_LICENCE_POLY_SVW</code></td>
        <td>Woodlot boundaries and file IDs</td>
        <td>Open Government Licence – BC</td></tr>
      <tr><td>Issued Woodlot Licence Listings (AAC report)</td>
        <td>AAC and AAC area per woodlot</td>
        <td>Open Government Licence – BC</td></tr>
      <tr><td>Vegetation Resources Inventory Rank 1 (2025)</td>
        <td>Inventory polygons, species, age, site index</td>
        <td>Open Government Licence – BC</td></tr>
      <tr><td>Provincial Proxy Timber Harvesting Land Base</td>
        <td>Managed / unmanaged land-base split</td>
        <td>Open Government Licence – BC</td></tr>
      <tr><td>VDYP7 input polygon/layer tables</td>
        <td>Natural-stand yield curves</td>
        <td>Open Government Licence – BC</td></tr>
      <tr><td>TIPSY database tables</td>
        <td>Managed-stand yield surfaces</td>
        <td>BC government; raw tables not redistributed</td></tr>
      <tr><td>TSA boundaries and site productivity</td>
        <td>Boundary and site-index context</td>
        <td>Open Government Licence – BC</td></tr>
    </tbody>
  </table>

  <h2>Model chain</h2>
  <ol>
    <li>Fetch the 845 active woodlot boundaries and 798 public AAC values.</li>
    <li>Clip the VRI to each woodlot and split fragments by the Proxy THLB.</li>
    <li>Build VDYP curves and fresh-tipsy managed curves through FEMIC.</li>
    <li>Compile the fragments into a WS4 dataset and validate it.</li>
    <li>Run a 1.2× AAC even-flow search for the first 100 years.</li>
    <li>Generate and solve a first-period FHOPS operational pilot.</li>
  </ol>

  <h2>Caveats</h2>
  <ul>
    <li>The Proxy THLB is a strategic estimate, not the statutory TSR THLB.</li>
    <li>Where TIPSY lacks a BC species code, the build uses a documented
      surrogate (for example MB→AT, BL→AT, SE→SW, PY→PLI, H→HWI).</li>
    <li>VDYP still runs the Windows console under Wine; the managed-curve
      stage uses fresh-tipsy without Wine.</li>
    <li>The FHOPS plans are first-period, ground-based, rate-fixed pilots.
      They do not model roads, terrain, landing geometry, or real costs.</li>
    <li>Some woodlots cannot hold their AAC at the 1.2× band through all ten
      periods; that gap is a model result, not a build failure.</li>
    <li>This is not a statutory timber supply analysis. Use professional
      judgment and the cited public sources.</li>
  </ul>

  <h2>Build status</h2>
  <p class="note">__BUILT__ of __TOTAL__ active woodlots are built with full
  WS4 bundles and AAC baselines; __PENDING__ licences are catalogued while
  their public AAC is pending. Raw TIPSY tables and government model bundles
  are not redistributed by this portal.</p>

  <footer>UBC FRESH · Woodlots BC Planning Portal ·
  <a href="/">portal home</a></footer>
</main>
</body>
</html>"""

_LEGAL_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__ · Woodlots BC Planning Portal</title>
  <style>
    :root { --ink: #17231f; --muted: #5b6b64; --line: #d8e0db;
            --paper: #f7faf7; --accent: #6b4f2a; }
    * { box-sizing: border-box; }
    body { margin: 0; color: var(--ink); background: var(--paper);
           font: 16px/1.6 system-ui, -apple-system, Segoe UI, sans-serif; }
    main { max-width: 820px; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; }
    a { color: var(--accent); }
    h1 { font-size: clamp(2rem, 4vw, 2.8rem); margin: .4rem 0 1rem; }
    h2 { margin: 2rem 0 .5rem; }
    .lede { color: var(--muted); font-size: 1.05rem; }
    footer { margin-top: 2.5rem; padding-top: 1rem;
             border-top: 1px solid var(--line); color: var(--muted);
             font-size: .85rem; }
  </style>
</head>
<body>
<main>
  <p><a href="/">← Back to the portal</a></p>
  <h1>__TITLE__</h1>
  __BODY__
  <footer>UBC FRESH · Woodlots BC Planning Portal ·
  <a href="/about">Sources &amp; methods</a> ·
  <a href="/privacy">Privacy</a></footer>
</main>
</body>
</html>"""

TERMS_BODY = """
<p class="lede">This portal is a free, public-data planning pilot for BC
woodlot licences. It is offered as-is for exploration, teaching, and
discussion.</p>

<h2>No warranty</h2>
<p>The models, schedules, and operational plans are pilot outputs. They may
contain errors, omissions, or assumptions that do not fit a particular
woodlot licence. Nothing here is a substitute for professional judgment.</p>

<h2>Not a statutory analysis</h2>
<p>The portal is not a statutory timber supply analysis, an AAC
determination, or a substitute for a registered professional. Do not use it
for legal, regulatory, or investment decisions.</p>

<h2>Data and attribution</h2>
<p>The portal uses public BC data under the Open Government Licence –
British Columbia. Source, retrieval date, and provenance are recorded in the
catalog, the build queue, and the Sources &amp; methods page. Raw TIPSY tables
and government model bundles are not redistributed.</p>

<h2>Acceptable use</h2>
<p>Do not use the service to attack, scrape at scale, or overload the host.
Do not present the outputs as official government analyses. Do not remove
attribution or disclaimers when reusing results.</p>

<h2>Changes</h2>
<p>The project may change, pause, or withdraw the service during the pilot.
Check the Sources &amp; methods page for the current assumptions.</p>
"""

PRIVACY_BODY = """
<p class="lede">This portal is a read-only public-data pilot. It does not
require an account and does not store personal profiles.</p>

<h2>What is collected</h2>
<p>Cloudflare Access and the reverse proxy may record IP address, user agent,
request path, timestamp, and authentication status for security and
operations. The application itself does not create user accounts or collect
personal information.</p>

<h2>Cookies</h2>
<p>Cloudflare Access may set a session cookie to keep an authenticated user
signed in. The portal does not use advertising, analytics, or tracking
cookies.</p>

<h2>Retention</h2>
<p>Proxy and access logs are retained for up to 30 days for security and
troubleshooting, then removed or aggregated.</p>

<h2>Model data</h2>
<p>The WS4 and FHOPS datasets contain public forest inventory and tenure
data. They do not contain personal information.</p>

<h2>Contact</h2>
<p>For questions about access, logging, or removal, contact Woodlots BC or the
UBC FRESH project team.</p>
"""

INSTANCES = discover()
INSTANCE_BY_SLUG = {instance.slug: instance for instance in INSTANCES}
MOUNTED_SLUGS: set[str] = set()


@app.get("/about", response_class=HTMLResponse)
async def about() -> HTMLResponse:
    instances = discover()
    built = sum(1 for item in instances if item.ready)
    pending = sum(1 for item in instances if item.aac_m3 is None)
    page = (
        SOURCES_HTML.replace("__BUILT__", str(built))
        .replace("__TOTAL__", str(len(instances)))
        .replace("__PENDING__", str(pending))
    )
    return HTMLResponse(page)


@app.get("/terms", response_class=HTMLResponse)
async def terms() -> HTMLResponse:
    return HTMLResponse(
        _LEGAL_TEMPLATE.replace("__TITLE__", "Terms").replace(
            "__BODY__", TERMS_BODY
        )
    )


@app.get("/privacy", response_class=HTMLResponse)
async def privacy() -> HTMLResponse:
    return HTMLResponse(
        _LEGAL_TEMPLATE.replace("__TITLE__", "Privacy").replace(
            "__BODY__", PRIVACY_BODY
        )
    )


@app.get("/health")
async def health() -> JSONResponse:
    instances = discover()
    return JSONResponse(
        {
            "status": "ok",
            "instances": len(instances),
            "ready": sum(1 for instance in instances if instance.ready),
            "buildable": sum(
                1 for instance in instances if instance.aac_m3 is not None
            ),
            "pending_aac": sum(
                1 for instance in instances if instance.aac_m3 is None
            ),
            "read_only": PUBLIC_READ_ONLY,
            "demo_mode": DEMO_MODE,
        }
    )


@app.get("/api/instances")
async def api_instances() -> JSONResponse:
    return JSONResponse(
        {"instances": [instance.as_dict() for instance in discover()]}
    )


@app.get("/api/geojson/woodlots", response_model=None)
async def woodlot_geojson() -> FileResponse | JSONResponse:
    path = ROOT / "data" / "boundaries" / "woodlot_boundaries_simplified.geojson"
    if not path.exists():
        return JSONResponse(
            {"error": "Woodlot boundaries not generated"}, status_code=404
        )
    return FileResponse(path, media_type="application/geo+json")


@app.get("/rationale/{slug}", response_class=HTMLResponse)
async def rationale(slug: str) -> HTMLResponse:
    if slug not in _queue_rows():
        return HTMLResponse("unknown woodlot", status_code=404)
    path = INSTANCES_ROOT / slug / "config" / "W4W-CALIBRATION.md"
    if not path.is_file():
        return HTMLResponse("no W4W calibration yet", status_code=404)
    body = MARKDOWN.render(path.read_text(encoding="utf-8"))
    return HTMLResponse(
        f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>W4W rationale · {html.escape(slug)}</title>
        <style>
          :root {{ color-scheme: light; --ink:#17231f; --muted:#5b6b64;
                   --line:#d8e0db; --paper:#f7faf7; --accent:#6b4f2a; }}
          body {{ margin:0; color:var(--ink); background:var(--paper);
                  font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif; }}
          main {{ max-width:900px; margin:0 auto; padding:2rem 1.2rem 4rem; }}
          a {{ color:var(--accent); }}
          h1,h2,h3 {{ line-height:1.2; margin:1.6rem 0 .5rem; }}
          h1 {{ font-size:clamp(1.8rem,4vw,2.6rem); }}
          h2 {{ border-bottom:1px solid var(--line); padding-bottom:.3rem; }}
          p,li {{ max-width:75ch; }}
          table {{ border-collapse:collapse; width:100%; margin:1rem 0;
                   background:#fff; font-size:.92rem; }}
          th,td {{ border:1px solid var(--line); padding:.45rem .6rem;
                   text-align:left; vertical-align:top; }}
          th {{ background:#eef3ef; }}
          code {{ background:#eef3ef; border-radius:4px; padding:.1rem .3rem; }}
          pre {{ background:#fff; border:1px solid var(--line); border-radius:10px;
                 padding:1rem; overflow-x:auto; }}
          blockquote {{ margin:1rem 0; padding:.2rem 1rem;
                        border-left:4px solid var(--accent); color:var(--muted);
                        background:#fff; }}
        </style></head>
        <body><main>
        <p><a href="/instance/{html.escape(slug)}/">← back to model</a></p>
        {body}
        </main></body></html>"""
    )


@app.get("/static/map.js")
async def map_js() -> FileResponse:
    return FileResponse(
        ROOT / "portal" / "static" / "map.js", media_type="application/javascript"
    )


def _card(instance: Instance) -> str:
    thlb = (
        f"{instance.thlb_ha:,.0f} ha ({instance.thlb_fraction:.1%})"
        if instance.thlb_ha is not None and instance.thlb_fraction is not None
        else "not prepared"
    )
    aac = f"{instance.aac_m3:,.0f} m³/yr" if instance.aac_m3 else "pending"
    aac_thlb = (
        f"{instance.aac_m3 / instance.thlb_ha:,.1f} m³/ha/yr"
        if instance.aac_m3 and instance.thlb_ha
        else "—"
    )
    area = f"{instance.area_ha:,.0f} ha" if instance.area_ha else "pending"
    blocks = f"{instance.blocks:,}" if instance.blocks is not None else "—"
    runs = ", ".join(instance.runs) if instance.runs else "none"
    if instance.fhops:
        fhops = (
            f"{instance.fhops.get('completed_blocks', '?')} blocks, "
            f"{instance.fhops.get('makespan_day', '?')} days"
        )
    else:
        fhops = "not run"
    w4w_text = ""
    w4w_link = ""
    if instance.w4w:
        w4w_text = (
            f"{instance.w4w.get('net_area_ha', '—')} ha net, "
            f"factor {instance.w4w.get('thlb_factor', '—')}, "
            f"{instance.w4w.get('pct_proxy_thlb', 0):.0%} of Proxy THLB"
        )
        if instance.w4w.get("warning"):
            w4w_text += " · ⚠ method check"
        w4w_link = f'<a href="/rationale/{instance.slug}">W4W rationale</a>'
    w4w_row = (
        f'<p class="runs">W4W: {html.escape(w4w_text)} · {w4w_link}</p>'
        if w4w_text
        else ""
    )
    search = html.escape(
        f"{instance.file_id} {instance.label} {instance.subtitle}".lower()
    )
    featured = instance.slug in SPECS
    if instance.slug in MOUNTED_SLUGS:
        link = f'<a class="open" href="/instance/{instance.slug}/">Open model</a>'
        badge = '<span class="badge ok">ready</span>'
        if instance.partial:
            badge += ' <span class="badge wait">partial</span>'
        if featured:
            badge += ' <span class="badge pilot">featured</span>'
    elif instance.ready:
        link = ""
        badge = '<span class="badge wait">ready · restart portal</span>'
    else:
        link = ""
        badge = f'<span class="badge wait">{html.escape(instance.reason)}</span>'
    actions: list[str] = []
    if link:
        actions.append(link)
    if instance.fhops:
        actions.append(
            f'<a class="open secondary" href="/fhops/{html.escape(instance.slug)}">'
            "Open FHOPS pilot</a>"
        )
    actions_html = (
        f'<div class="actions">{"".join(actions)}</div>' if actions else ""
    )
    studio_link = (
        f' · <a href="/fhops/{html.escape(instance.slug)}/studio">3D studio</a>'
        if instance.fhops
        else ""
    )
    return f"""
    <article class="card{ ' featured' if featured else '' }" data-search="{search}">
      <header>
        <div>
          <p class="file">{html.escape(instance.file_id)}</p>
          <h2>{html.escape(instance.label)}</h2>
          <p class="sub">{html.escape(instance.subtitle)}</p>
        </div>
        {badge}
      </header>
      <dl>
        <div><dt>Area</dt><dd>{area}</dd></div>
        <div><dt>AAC</dt><dd>{aac}</dd></div>
        <div><dt>AAC / THLB</dt><dd>{aac_thlb}</dd></div>
        <div><dt>THLB</dt><dd>{thlb}</dd></div>
        <div><dt>WS4 blocks</dt><dd>{blocks}</dd></div>
      </dl>
      <p class="runs">Runs: {html.escape(runs)}</p>
      <p class="runs">FHOPS: {html.escape(fhops)}{studio_link}</p>
      {w4w_row}
      {actions_html}
    </article>
    """


@app.get("/fhops/{slug}/theatre.json", response_model=None)
async def fhops_theatre_data(slug: str) -> FileResponse:
    instance = INSTANCE_BY_SLUG.get(slug)
    if instance is None:
        raise HTTPException(status_code=404, detail="unknown woodlot")
    path = instance.root / "fhops" / "out" / "theatre.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="theatre data missing")
    return FileResponse(path, media_type="application/json")


@app.get("/fhops/{slug}/theatre", response_class=HTMLResponse)
async def fhops_theatre(slug: str) -> HTMLResponse:
    instance = INSTANCE_BY_SLUG.get(slug)
    if instance is None:
        raise HTTPException(status_code=404, detail="unknown woodlot")
    return HTMLResponse(
        render_theatre(
            slug=instance.slug,
            label=instance.label,
            file_id=instance.file_id,
            subtitle=instance.subtitle,
        )
    )


@app.get("/fhops/{slug}/timeline.json", response_model=None)
async def fhops_timeline(slug: str) -> FileResponse:
    instance = INSTANCE_BY_SLUG.get(slug)
    if instance is None:
        raise HTTPException(status_code=404, detail="unknown woodlot")
    path = instance.root / "fhops" / "out" / "timeline.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="timeline missing")
    return FileResponse(path, media_type="application/json")


@app.get("/fhops/{slug}/studio", response_class=HTMLResponse)
async def fhops_studio(slug: str) -> HTMLResponse:
    instance = INSTANCE_BY_SLUG.get(slug)
    if instance is None:
        raise HTTPException(status_code=404, detail="unknown woodlot")
    return HTMLResponse(
        render_studio(
            slug=instance.slug,
            label=instance.label,
            file_id=instance.file_id,
            subtitle=instance.subtitle,
            summary=instance.fhops or {},
            aac_m3=instance.aac_m3,
        )
    )


@app.get("/fhops/{slug}", response_class=HTMLResponse)
async def fhops_page(slug: str) -> HTMLResponse:
    instance = INSTANCE_BY_SLUG.get(slug)
    if instance is None:
        raise HTTPException(status_code=404, detail="unknown woodlot")
    return HTMLResponse(_fhops_page(instance))


@app.get("/fhops/{slug}/scheduled.geojson", response_model=None)
async def fhops_scheduled(slug: str) -> FileResponse:
    instance = INSTANCE_BY_SLUG.get(slug)
    if instance is None:
        raise HTTPException(status_code=404, detail="unknown woodlot")
    path = instance.root / "fhops" / "out" / "scheduled_blocks.geojson"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="scheduled block map missing")
    return FileResponse(path, media_type="application/geo+json")


@app.get("/fhops/{slug}/download/{name}", response_model=None)
async def fhops_download(slug: str, name: str) -> FileResponse:
    instance = INSTANCE_BY_SLUG.get(slug)
    if instance is None:
        raise HTTPException(status_code=404, detail="unknown woodlot")
    from .fhops_page import FHOPS_DOWNLOADS

    relative = FHOPS_DOWNLOADS.get(name)
    if relative is None:
        raise HTTPException(status_code=404, detail="unknown FHOPS file")
    path = instance.root / "fhops" / relative
    if not path.is_file():
        raise HTTPException(status_code=404, detail="FHOPS file missing")
    return FileResponse(path, filename=path.name)


@app.get("/", response_class=HTMLResponse)
async def landing() -> HTMLResponse:
    instances = discover()
    featured = sorted(
        [item for item in instances if item.slug in SPECS],
        key=lambda item: list(SPECS).index(item.slug),
    )
    others = [item for item in instances if item.slug not in SPECS]
    total = len(instances)
    ready = sum(1 for item in instances if item.ready)
    pending_aac = sum(1 for item in instances if item.aac_m3 is None)
    cards = "\n".join(_card(instance) for instance in featured + others)
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Woodlots BC Planning Portal</title>
  <link rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <style>
    :root {{ color-scheme: light; --ink: #17231f; --muted: #5b6b64;
             --line: #d8e0db; --paper: #f7faf7; --accent: #6b4f2a; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font: 16px/1.5 system-ui, -apple-system, Segoe UI, sans-serif;
            color: var(--ink); background: var(--paper); }}
    header.hero {{ padding: 3rem 1.5rem 2rem; max-width: 1100px; margin: 0 auto; }}
    .kicker {{ color: var(--accent); font-weight: 700; letter-spacing: .08em;
               text-transform: uppercase; font-size: .75rem; }}
    h1 {{ font-size: clamp(2rem, 4vw, 3.2rem); margin: .4rem 0;
          letter-spacing: -.02em; }}
    .lede {{ color: var(--muted); max-width: 65ch; font-size: 1.05rem; }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 0 1.5rem 3rem; }}
    .map-wrap {{ background: #fff; border: 1px solid var(--line);
                 border-radius: 14px; overflow: hidden; margin-bottom: 1rem; }}
    #map {{ height: 420px; width: 100%; background: #eef3ef; }}
    .map-note {{ margin: .6rem 1rem .8rem; color: var(--muted);
                 font-size: .82rem; }}
    .pilot-label {{ background: #6b4f2a; color: #fff; border: none;
                    border-radius: 5px; font-weight: 700; font-size: .66rem;
                    padding: .1rem .3rem; box-shadow: none;
                    white-space: nowrap; }}
    .pilot-label::before {{ border-top-color: #6b4f2a; }}
    #woodlot-search {{ width: 100%; padding: .7rem .9rem; border: 1px solid var(--line);
                   border-radius: 9px; font: inherit; margin-bottom: 1rem;
                   background: #fff; }}
    .grid {{ display: grid; gap: 1rem;
             grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}
    .card {{ background: #fff; border: 1px solid var(--line); border-radius: 14px;
             padding: 1.2rem; display: flex; flex-direction: column; gap: .9rem; }}
    .card.featured {{ border-color: var(--accent);
                      box-shadow: 0 0 0 1px var(--accent) inset; }}
    .badge.pilot {{ background: #f3e8d8; color: #5c3d1f; }}
    .card header {{ display: flex; justify-content: space-between; gap: 1rem; }}
    .file {{ margin: 0; font-size: .75rem; font-weight: 700; color: var(--accent);
             letter-spacing: .08em; }}
    h2 {{ margin: .15rem 0; font-size: 1.35rem; }}
    .sub {{ margin: 0; color: var(--muted); font-size: .9rem; }}
    .badge {{ height: fit-content; border-radius: 999px; padding: .2rem .55rem;
              font-size: .72rem; font-weight: 700; white-space: nowrap; }}
    .badge.ok {{ background: #e4f4ea; color: #135c38; }}
    .badge.wait {{ background: #fdf1dc; color: #7a4d00; }}
    dl {{ margin: 0; display: grid; grid-template-columns: 1fr 1fr; gap: .5rem .8rem; }}
    dt {{ font-size: .7rem; text-transform: uppercase; letter-spacing: .06em;
          color: var(--muted); }}
    dd {{ margin: .1rem 0 0; font-weight: 650; }}
    .runs {{ margin: 0; color: var(--muted); font-size: .82rem; }}
    .actions {{ display: flex; gap: .5rem; flex-wrap: wrap; margin-top: auto; }}
    .open {{ display: inline-block; padding: .6rem .9rem;
             text-align: center; border-radius: 9px; background: var(--accent);
             color: #fff; text-decoration: none; font-weight: 700; }}
    .open.secondary {{ background: #fff; color: var(--accent);
                       border: 1px solid var(--accent); }}
    footer {{ max-width: 1100px; margin: 0 auto; padding: 1.2rem 1.5rem 3rem;
              color: var(--muted); font-size: .82rem;
              border-top: 1px solid var(--line); }}
  </style>
</head>
<body>
  <header class="hero">
    <p class="kicker">UBC FRESH · public-data pilot</p>
    <h1>Woodlots BC Planning Portal</h1>
    <p class="lede">All {total} active woodlot licences, each with a WS4
    strategic model and a first-period FHOPS operational pilot, built only
    from public data. Models built: {ready}. Licences catalogued with AAC
    pending: {pending_aac}. The three featured pilots are Chinook Woodlots,
    Boomer Enterprises, and Fibre Farms.</p>
  </header>
  <main>
    <section class="map-wrap">
      <div id="map"></div>
      <p class="map-note">All {total} active woodlot licences. The three
      featured pilots are highlighted; click a pilot to open its model.</p>
    </section>
    <input id="woodlot-search" type="search"
           placeholder="Search woodlot licence…"
           aria-label="Search woodlot licence">
    <section class="grid">
      {cards}
    </section>
  </main>
  <footer>Not a statutory timber supply analysis. Model outputs are pilot
  scenarios; use professional judgment and the cited public sources.
  <a href="/about">Sources &amp; methods</a> ·
  <a href="/terms">Terms</a> ·
  <a href="/privacy">Privacy</a>.</footer>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="/static/map.js"></script>
</body>
</html>"""
    )


for _instance in INSTANCES:
    if not _instance.ready:
        continue
    _instance.mount = f"/instance/{_instance.slug}/"
    app.mount(
        _instance.mount.rstrip("/"),
        LazyWS4(_instance.root),
    )
    MOUNTED_SLUGS.add(_instance.slug)
