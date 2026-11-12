"""FHOPS pilot page for one woodlot instance."""

from __future__ import annotations

import html
from typing import Any

TREELAB_MOUNTED = False

FHOPS_CSS = """<style>
  :root { color-scheme: light; --ink: #17231f; --muted: #5b6b64;
           --line: #d8e0db; --paper: #f7faf7; --accent: #1f6f4a;
           --warm: #b45309; }
  * { box-sizing: border-box; }
  body { margin: 0; color: var(--ink); background: var(--paper);
         font: 16px/1.5 system-ui, -apple-system, Segoe UI, sans-serif; }
  .hero { max-width: 1100px; margin: 0 auto; padding: 2.6rem 1.5rem 1.2rem; }
  .kicker { margin: 0; color: var(--warm); font-weight: 700; font-size: .75rem;
            letter-spacing: .08em; text-transform: uppercase; }
  h1 { margin: .35rem 0 .2rem; font-size: clamp(2rem, 4vw, 2.8rem); }
  .sub { margin: 0; color: var(--muted); }
  .actions { display: flex; flex-wrap: wrap; gap: .6rem; margin-top: 1.2rem; }
  .button { display: inline-block; padding: .6rem .9rem; border-radius: 9px;
            background: var(--accent); color: #fff; text-decoration: none;
            font-weight: 700; }
  .button.secondary { background: #fff; color: var(--accent);
                      border: 1px solid var(--accent); }
  .button.studio { background: var(--warm); border-color: var(--warm); }
  main { max-width: 1100px; margin: 0 auto; padding: 0 1.5rem 3rem; }
  .stats { display: grid; gap: .7rem;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            margin: 1.2rem 0; }
  .stat { background: #fff; border: 1px solid var(--line); border-radius: 12px;
          padding: .8rem .9rem; }
  .stat span { display: block; color: var(--muted); font-size: .7rem;
               text-transform: uppercase; letter-spacing: .06em; }
  .stat strong { display: block; margin-top: .15rem; font-size: 1.15rem; }
  .panel { background: #fff; border: 1px solid var(--line); border-radius: 14px;
           padding: 1rem; margin: 1rem 0; }
  .panel h2 { margin: 0 0 .35rem; font-size: 1.25rem; }
  .hint { color: var(--muted); font-size: .9rem; }
  #fhops-map { height: 460px; width: 100%; border-radius: 10px;
               background: #eef3ef; margin-top: .8rem; }
  .map-note { margin: .55rem .2rem 0; color: var(--muted); font-size: .82rem; }
  .downloads { columns: 2; margin: .6rem 0 0; padding-left: 1.1rem; }
  .downloads li { margin: .25rem 0; break-inside: avoid; }
  .downloads a { color: var(--accent); }
  .caveat { border-left: 4px solid var(--warm); }
  footer { max-width: 1100px; margin: 0 auto; padding: 1.2rem 1.5rem 3rem;
           color: var(--muted); font-size: .82rem; border-top: 1px solid var(--line); }
  @media (max-width: 640px) { .downloads { columns: 1; } }
</style>"""

FHOPS_JS = """<script>
const fhopsMap = L.map('fhops-map', { scrollWheelZoom: false })
  .setView([54.5, -124.5], 6);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 14,
  attribution: '&copy; OpenStreetMap contributors',
}).addTo(fhopsMap);
fetch('/fhops/__SLUG__/scheduled.geojson')
  .then((response) => response.json())
  .then((data) => {
    const layer = L.geoJSON(data, {
      style: { color: '#9a3412', weight: 2, fillColor: '#f59e0b', fillOpacity: 0.55 },
      onEachFeature: (feature, featureLayer) => {
        const p = feature.properties || {};
        const days = (p.first_day ?? '—') + '–' + (p.last_day ?? '—');
        featureLayer.bindPopup(
          '<strong>' + (p.label || p.block_id) + '</strong><br>' +
          'Machines: ' + (p.machines || '—') + '<br>' +
          'Days: ' + days + '<br>' +
          'Assignments: ' + (p.assignments ?? '—')
        );
      },
    }).addTo(fhopsMap);
    if (layer.getBounds().isValid()) {
      fhopsMap.fitBounds(layer.getBounds(), { padding: [30, 30] });
    }
  })
  .catch(() => {
    const target = document.getElementById('fhops-map');
    if (target) target.textContent = 'Scheduled block map unavailable';
  });
</script>"""

FHOPS_DOWNLOADS = {
    "summary.json": "summary.json",
    "scenario.yaml": "scenario.yaml",
    "solution.csv": "out/heur_solution.csv",
    "blocks.csv": "data/blocks.csv",
    "machines.csv": "data/machines.csv",
    "landings.csv": "data/landings.csv",
    "calendar.csv": "data/calendar.csv",
    "prod_rates.csv": "data/prod_rates.csv",
}


def _fmt(value: object, digits: int = 0) -> str:
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def _fhops_page(instance: Any) -> str:
    summary = instance.fhops or {}
    slug = html.escape(instance.slug)
    scheduled = instance.root / "fhops" / "out" / "scheduled_blocks.geojson"
    period_volume = summary.get("total_production_m3")
    makespan = summary.get("makespan_day")
    plan_kind = summary.get("plan_kind")
    try:
        average_rate = float(period_volume) / float(makespan)
    except (TypeError, ValueError, ZeroDivisionError):
        average_rate = None
    if plan_kind == "tenyear":
        plan_label = "10 years"
        stats = [
            ("Annual AAC", f"{_fmt(instance.aac_m3)} m³/yr"),
            ("10-year harvested", f"{_fmt(period_volume)} m³"),
            ("Completed blocks", _fmt(summary.get("completed_blocks"))),
            ("Makespan", f"{_fmt(summary.get('makespan_years'))} years"),
            ("Horizon", f"{_fmt(summary.get('horizon_days'))} days"),
            ("Average scheduled rate", f"{_fmt(average_rate)} m³/day"),
        ]
    elif plan_kind in ("rolling10", "multiyear"):
        plan_label = (
            "10 years · multi-year"
            if plan_kind == "multiyear"
            else "10 years · rolling"
        )
        stats = [
            ("Annual AAC", f"{_fmt(instance.aac_m3)} m³/yr"),
            (
                "Annual harvested",
                f"{_fmt(summary.get('annual_total_production_m3'))} m³",
            ),
            ("10-year harvested", f"{_fmt(period_volume)} m³"),
            ("Blocks treated", _fmt(summary.get("blocks_treated"))),
            (
                "Annual processed",
                f"{_fmt(summary.get('annual_processed_m3'))} m³",
            ),
            (
                "Annual staged",
                f"{_fmt(summary.get('annual_staged_m3'))} m³",
            ),
            ("Horizon", "3,650 days · 10 years"),
            ("Makespan", plan_label),
        ]
    else:
        stats = [
            ("Annual AAC", f"{_fmt(instance.aac_m3)} m³/yr"),
            ("Period volume (10 yr)", f"{_fmt(period_volume)} m³"),
            ("Completed blocks", _fmt(summary.get("completed_blocks"))),
            ("Makespan", f"{_fmt(makespan)} days"),
            ("Average scheduled rate", f"{_fmt(average_rate)} m³/day"),
            ("Configured rate", f"{_fmt(summary.get('rate_m3_per_day'))} m³/day"),
            ("Horizon", f"{_fmt(summary.get('horizon_days'))} days"),
            (
                "Sequencing violations",
                _fmt(summary.get("sequencing_violation_count")),
            ),
        ]
    stats_html = "".join(
        f'<div class="stat"><span>{html.escape(label)}</span>'
        f"<strong>{html.escape(value)}</strong></div>"
        for label, value in stats
    )
    download_html = "".join(
        f'<li><a href="/fhops/{slug}/download/{name}">{html.escape(name)}</a></li>'
        for name in FHOPS_DOWNLOADS
    )
    tree_lab_link = ""
    if TREELAB_MOUNTED:
        tree_lab_href = "/treelab/"
        if instance.slug == "cfa-k3x":
            tree_lab_href = "/treelab/?case=k3x-6683&run=demo-1"
        tree_lab_link = (
            f'<a class="button secondary" href="{tree_lab_href}">'
            "Open Tree Lab 3D/replay</a>"
        )
    horizon_label = html.escape(str(summary.get("horizon_days") or 450))
    if plan_kind == "tenyear":
        plan_hint = (
            "<p class='hint'>Ten-year seasonal plan: the scenario schedules "
            "ten years of AAC volume using a 180-day operating season per "
            "year. It is a compressed tactical pilot, not a global ten-year "
            "MILP or a production schedule.</p>"
        )
    elif plan_kind == "multiyear":
        plan_hint = (
            "<p class='hint'>Ten-year multi-year plan: each year is an "
            "optimized 180-day annual season with a different block "
            "allocation. The plan cuts and stages the full annual AAC; "
            "processed volume is the portion through the processor in that "
            "season. This is not a global ten-year MILP or a production "
            "schedule.</p>"
        )
    elif plan_kind == "rolling10":
        plan_hint = (
            "<p class='hint'>Ten-year rolling plan: each year is an optimized "
            "180-day annual season, repeated over ten years. The annual plan "
            "cuts and stages the full AAC; processed volume is the portion "
            "through the processor in that season. This is not a production "
            "schedule.</p>"
        )
    else:
        plan_hint = (
            "<p class='hint'>First-period, ground-based, rate-fixed pilot. "
            "The scenario compresses ten years of AAC volume into a short "
            "operating horizon; it is not annual production and not a "
            "production operating plan.</p>"
        )
    if plan_kind == "tenyear":
        kicker = "ten-year seasonal plan"
    elif plan_kind in ("rolling10", "multiyear"):
        kicker = "ten-year multi-year plan"
    else:
        kicker = "first-period operational pilot"
    if scheduled.is_file():
        map_html = (
            '<div id="fhops-map"></div>'
            '<p class="map-note">Orange blocks are the first-period FHOPS '
            "schedule. Click a block for its machines and working days.</p>"
        )
        map_script = FHOPS_JS.replace("__SLUG__", slug)
    else:
        map_html = (
            '<p class="hint">Scheduled block map was not generated for this '
            "instance. The summary and model files are still available.</p>"
        )
        map_script = ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FHOPS pilot · {html.escape(instance.label)} ·
  Woodlots BC Planning Portal</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  {FHOPS_CSS}
</head>
<body>
  <header class="hero">
    <p class="kicker">FHOPS · {kicker}</p>
    <h1>{html.escape(instance.label)}</h1>
    <p class="sub">{html.escape(instance.file_id)} ·
    {html.escape(instance.subtitle)}</p>
    <div class="actions">
      <a class="button studio" href="/fhops/{slug}/studio">Open 3D block studio</a>
      {tree_lab_link}
      <a class="button" href="/fhops/{slug}/theatre">Open tree-scale theatre</a>
      <a class="button secondary" href="/instance/{slug}/">Open WS4 model</a>
      <a class="button secondary" href="/">All woodlots</a>
    </div>
  </header>
  <main>
    <section class="stats">{stats_html}</section>
    <section class="panel">
      <h2>Solved block plan</h2>
      {plan_hint}
      {map_html}
    </section>
    <section class="panel">
      <h2>Model files</h2>
      <p class="hint">Download the exact scenario data and solved block assignment.</p>
      <ul class="downloads">{download_html}</ul>
    </section>
    <section class="panel caveat">
      <h2>Read this as a pilot</h2>
      <p class="hint">The FHOPS pilot tests whether a public-data operational
      model is useful. It uses a {horizon_label}-day horizon, fixed rates,
      one ground-based system, and no road or cost model. Treat the schedule
      as a conversation starter, not a commitment.</p>
    </section>
  </main>
  <footer>Model outputs are pilot scenarios; use professional judgment and the
  cited public sources. <a href="/about">Sources &amp; methods</a> ·
  <a href="/terms">Terms</a> · <a href="/privacy">Privacy</a>.</footer>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  {map_script}
</body>
</html>"""


