"""Full-screen 3D harvest animation for one FHOPS scenario."""

from __future__ import annotations

import html
from typing import Any

STUDIO_CSS = """<style>
  :root { color-scheme: dark; --ink: #e2e8f0; --muted: #94a3b8;
           --panel: rgba(8, 18, 28, .82); --line: rgba(148, 163, 184, .22);
           --accent: #f97316; --done: #14b8a6; }
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; }
  body { background: #050b12; color: var(--ink);
         font: 15px/1.45 system-ui, -apple-system, Segoe UI, sans-serif;
         overflow: hidden; }
  #studio-map { position: fixed; inset: 0; }
  .studio-head { position: fixed; z-index: 5; top: 1rem; left: 1rem;
                 right: 1rem; display: flex; justify-content: space-between;
                 gap: 1rem; align-items: flex-start; pointer-events: none; }
  .studio-title { background: var(--panel); border: 1px solid var(--line);
                  border-radius: 14px; padding: .75rem 1rem;
                  backdrop-filter: blur(10px); pointer-events: auto; }
  .studio-kicker { margin: 0 0 .2rem; color: var(--accent);
                   font-size: .7rem; font-weight: 800; letter-spacing: .12em;
                   text-transform: uppercase; }
  .studio-title h1 { margin: 0; font-size: clamp(1.1rem, 2.2vw, 1.6rem); }
  .studio-title p { margin: .2rem 0 0; color: var(--muted); font-size: .82rem; }
  .studio-actions { display: flex; gap: .5rem; flex-wrap: wrap;
                    justify-content: flex-end; pointer-events: auto; }
  .studio-actions a, .studio-actions button { border: 1px solid var(--line);
      background: var(--panel); color: var(--ink); border-radius: 10px;
      padding: .55rem .8rem; text-decoration: none; font: inherit;
      font-weight: 700; cursor: pointer; backdrop-filter: blur(10px); }
  .studio-actions a:hover, .studio-actions button:hover { border-color: #64748b; }
  .studio-panel { position: fixed; z-index: 5; left: 1rem; right: 1rem;
                  bottom: 1rem; background: var(--panel);
                  border: 1px solid var(--line); border-radius: 16px;
                  padding: .85rem 1rem; backdrop-filter: blur(12px); }
  .studio-controls { display: flex; align-items: center; gap: .65rem;
                     flex-wrap: wrap; }
  .studio-controls button, .studio-controls select { border: 1px solid var(--line);
      background: rgba(15, 23, 42, .9); color: var(--ink); border-radius: 9px;
      padding: .45rem .7rem; font: inherit; cursor: pointer; }
  .studio-controls button.primary { background: var(--accent);
      border-color: var(--accent); color: #111827; font-weight: 800; }
  .studio-controls input[type="range"] { flex: 1 1 280px; accent-color: var(--accent); }
  .studio-hud { display: flex; gap: 1rem; flex-wrap: wrap; margin-top: .55rem;
                color: var(--muted); font-size: .8rem; }
  .studio-hud strong { color: var(--ink); }
  .studio-legend { position: fixed; z-index: 4; right: 1rem; bottom: 8.2rem;
                   background: var(--panel); border: 1px solid var(--line);
                   border-radius: 12px; padding: .65rem .8rem;
                   backdrop-filter: blur(10px); font-size: .76rem; }
  .studio-legend div { display: flex; align-items: center; gap: .4rem;
                       margin: .25rem 0; }
  .swatch { width: .7rem; height: .7rem; border-radius: 2px; display: inline-block; }
  .machine-marker { min-width: 28px; height: 24px; border-radius: 12px;
      color: #08111f; font-weight: 900; font-size: .7rem;
      display: flex; align-items: center; justify-content: center;
      border: 2px solid #f8fafc;
      box-shadow: 0 0 14px rgba(249, 115, 22, .75); }
  .studio-note { margin: .45rem 0 0; color: var(--muted); font-size: .7rem; }
  .maplibregl-ctrl { background: var(--panel) !important; border-radius: 8px; }
  .maplibregl-ctrl button { background: transparent !important; }
  .maplibregl-ctrl-icon { filter: invert(1); }
  .maplibregl-popup-content { background: #0f172a; color: var(--ink);
      border: 1px solid var(--line); border-radius: 10px; font-size: .8rem; }
  .maplibregl-popup-tip { border-top-color: #0f172a !important; }
  @media (max-width: 700px) {
    .studio-head { flex-direction: column; }
    .studio-actions { justify-content: flex-start; }
    .studio-legend { display: none; }
    .studio-hud { font-size: .72rem; }
  }
</style>"""

STUDIO_JS = """<script>
const SLUG = '__SLUG__';
const $ = (id) => document.getElementById(id);
let map = null;
let blocks = null;
let timeline = null;
let day = 1;
let makespan = 1;
let timer = null;
let orbit = null;
let follow = false;
let lastActiveKey = '';
let lastYear = 0;
let byLabel = {};
let eventsByDay = new Map();
let blockYears = new Map();
let machineMarkers = {};
let heightScale = 1.4;
const machineColors = { H1: '#fb923c', H2: '#22d3ee', H3: '#a78bfa', H4: '#f43f5e' };

function blockBounds(data) {
  const bounds = new maplibregl.LngLatBounds();
  for (const feature of data.features) {
    const coords = feature.geometry.coordinates;
    const walk = (value) => {
      if (typeof value[0] === 'number') {
        bounds.extend(value);
      } else {
        value.forEach(walk);
      }
    };
    walk(coords);
  }
  return bounds;
}

function dayFilter(kind) {
  if (kind === 'future') return ['>', ['get', 'first_day'], day];
  if (kind === 'active') {
    return ['all', ['<=', ['get', 'first_day'], day],
            ['>=', ['get', 'last_day'], day]];
  }
  return ['<', ['get', 'last_day'], day];
}

function updateMachines() {
  const events = eventsByDay.get(day) || [];
  const latest = {};
  for (const event of events) {
    if (!latest[event.machine]) latest[event.machine] = event;
  }
  for (const [machine, marker] of Object.entries(machineMarkers)) {
    const event = latest[machine];
    if (!event) {
      marker.getElement().style.display = 'none';
      continue;
    }
    const block = byLabel[event.block];
    if (!block) {
      marker.getElement().style.display = 'none';
      continue;
    }
    marker.setLngLat([
      Number(block.properties.centroid_lon),
      Number(block.properties.centroid_lat),
    ]);
    marker.getElement().style.display = '';
  }
  return Object.keys(latest).length;
}

function fitActive(force = false) {
  if (!map || !blocks || !follow) return;
  const active = blocks.features.filter(
    (feature) => feature.properties.active
  );
  if (!active.length) return;
  const target = active[0];
  const key = target.properties.label;
  if (!force && key === lastActiveKey) return;
  lastActiveKey = key;
  map.fitBounds(blockBounds({ features: [target] }), {
    padding: 120, pitch: 62, bearing: -20, duration: 1000, maxZoom: 16,
  });
}

function fitYear(force = false) {
  if (!map || !blocks) return;
  const year = Math.min(10, Math.ceil(day / 365));
  if (!force && year === lastYear) return;
  lastYear = year;
  const start = (year - 1) * 365 + 1;
  const end = year * 365;
  const labels = new Set();
  for (const event of timeline.events) {
    if (event.day >= start && event.day <= end) labels.add(event.block);
  }
  const targets = blocks.features.filter(
    (feature) => labels.has(feature.properties.label)
  );
  if (!targets.length) return;
  const active = (eventsByDay.get(day) || [])[0];
  const focus = targets.find(
    (feature) => feature.properties.label === active?.block
  ) || targets[0];
  map.fitBounds(blockBounds({ features: [focus] }), {
    padding: 120, pitch: 60, bearing: -24, duration: 900, maxZoom: 15,
  });
}

function updateTracks() {
  const sequences = {};
  for (const event of timeline.events) {
    if (event.day > day) continue;
    const block = byLabel[event.block];
    if (!block) continue;
    const point = [Number(block.properties.centroid_lon),
                   Number(block.properties.centroid_lat)];
    const sequence = sequences[event.machine] || [];
    const last = sequence[sequence.length - 1];
    if (!last || last[0] !== point[0] || last[1] !== point[1]) {
      sequence.push(point);
    }
    sequences[event.machine] = sequence;
  }
  const features = Object.entries(sequences)
    .filter(([, coords]) => coords.length > 1)
    .map(([machine, coordinates]) => ({
      type: 'Feature', properties: { machine },
      geometry: { type: 'LineString', coordinates },
    }));
  const source = map.getSource('tracks');
  if (source) source.setData({ type: 'FeatureCollection', features });
}

function updateDay(next) {
  if (!map || !blocks) return;
  makespan = Math.max(1, Number(timeline.makespan_day) || 1);
  day = Math.max(1, Math.min(makespan, Number(next) || 1));
  const input = $('day-range');
  if (input) input.value = day;
  const activeEvents = eventsByDay.get(day) || [];
  const activeLabels = new Set(activeEvents.map((event) => event.block));
  const first = activeEvents[0];
  $('follow-label').textContent = follow
    ? (first ? 'Following ' + first.block : 'Following —')
    : 'Year ' + Math.min(10, Math.ceil(day / 365)) + ' overview';
  for (const feature of blocks.features) {
    feature.properties.active = activeLabels.has(feature.properties.label);
    const featureYear = Math.min(10, Math.ceil(day / 365));
    feature.properties.year_active = Boolean(
      blockYears.get(feature.properties.label)?.has(featureYear)
    );
    feature.properties.finished = (
      Number(feature.properties.last_event_day || 0) < day
    );
  }
  const source = map.getSource('blocks');
  if (source) source.setData(blocks);
  updateTracks();
  map.setFilter('blocks-future', ['==', ['get', 'year_active'], true]);
  map.setFilter('blocks-active', ['==', ['get', 'active'], true]);
  map.setFilter('blocks-done', ['all', ['==', ['get', 'finished'], true],
    ['==', ['get', 'year_active'], true]]);
  const active = updateMachines();
  let done = 0;
  let doneVolume = 0;
  for (const feature of blocks.features) {
    if (feature.properties.finished) {
      done += 1;
      doneVolume += Number(feature.properties.volume_m3) || 0;
    }
  }
  const year = makespan > 1000 ? ' · Year ' + Math.min(10, Math.ceil(day / 365)) : '';
  $('day-label').textContent = 'Day ' + day + ' / ' + makespan + year;
  const yearValue = (Math.min(10, Math.ceil(day / 365)) - 1) * 365 + 1;
  const yearSelect = $('year-select');
  if (yearSelect && yearSelect.value !== String(yearValue)) {
    yearSelect.value = String(yearValue);
  }
  $('active-label').textContent = active + ' machines active';
  $('done-label').textContent = done + ' blocks harvested';
  $('volume-label').textContent =
    Math.round(doneVolume).toLocaleString() + ' m³ harvested';
  if (follow) fitActive();
  else fitYear();
}

function stopPlay() {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
  const button = $('play-button');
  if (button) button.textContent = '▶ Play';
}

function startPlay() {
  stopPlay();
  if (day >= makespan) updateDay(1);
  const speed = Number($('speed-select').value) || 90;
  timer = setInterval(() => {
    if (day >= makespan) {
      stopPlay();
      return;
    }
    updateDay(day + 1);
  }, speed);
  $('play-button').textContent = '❚❚ Pause';
}

function togglePlay() {
  if (timer) stopPlay();
  else startPlay();
}

function toggleOrbit() {
  if (orbit) {
    clearInterval(orbit);
    orbit = null;
    $('orbit-button').textContent = 'Orbit';
    return;
  }
  $('orbit-button').textContent = 'Stop orbit';
  orbit = setInterval(() => {
    map.easeTo({ bearing: map.getBearing() + 0.8, duration: 800 });
  }, 900);
}

function resetView() {
  stopPlay();
  follow = false;
  lastActiveKey = '';
  lastYear = 0;
  $('follow-button').textContent = 'Follow off';
  updateDay(1);
  fitYear(true);
}

function toggleFollow() {
  follow = !follow;
  const button = $('follow-button');
  if (button) button.textContent = follow ? 'Follow on' : 'Follow off';
  if (follow) {
    lastActiveKey = '';
    $('follow-label').textContent = 'Following —';
    fitActive(true);
  } else {
    lastYear = 0;
    fitYear(true);
  }
}

function fallbackStyle() {
  return {
    version: 8,
    sources: {
      basemap: {
        type: 'raster',
        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
        tileSize: 256,
        attribution: '&copy; OpenStreetMap contributors',
      },
    },
    layers: [
      { id: 'bg', type: 'background',
        paint: { 'background-color': '#050b12' } },
      { id: 'basemap', type: 'raster', source: 'basemap',
        paint: { 'raster-opacity': 0.52, 'raster-saturation': -0.25 } },
    ],
  };
}

function studioLayers() {
  return [
    { id: 'tracks', type: 'line', source: 'tracks',
      paint: { 'line-color': ['match', ['get', 'machine'],
                 'H1', '#fb923c', 'H2', '#22d3ee', 'H3', '#a78bfa',
                 'H4', '#f43f5e', '#94a3b8'],
               'line-width': 2, 'line-opacity': 0.45,
               'line-dasharray': [2, 2] } },
    { id: 'blocks-future', type: 'fill-extrusion', source: 'blocks',
      filter: ['==', ['get', 'year_active'], true],
      paint: { 'fill-extrusion-color': '#5f8f78',
               'fill-extrusion-opacity': 0.7,
               'fill-extrusion-height': ['*', ['get', 'height'], 0.16] } },
    { id: 'blocks-progress', type: 'fill-extrusion', source: 'blocks',
      filter: ['==', ['get', 'never'], true],
      paint: { 'fill-extrusion-color': '#b45309',
               'fill-extrusion-opacity': 0.0,
               'fill-extrusion-height': ['*', ['get', 'height'], 0.5] } },
    { id: 'blocks-done', type: 'fill-extrusion', source: 'blocks',
      filter: ['all', ['==', ['get', 'finished'], true],
               ['==', ['get', 'year_active'], true]],
      paint: { 'fill-extrusion-color': '#14b8a6',
               'fill-extrusion-opacity': 0.8,
               'fill-extrusion-height': ['*', ['get', 'height'], 0.7] } },
    { id: 'blocks-active', type: 'fill-extrusion', source: 'blocks',
      filter: ['==', ['get', 'active'], true],
      paint: { 'fill-extrusion-color': '#f97316',
               'fill-extrusion-opacity': 1,
               'fill-extrusion-height': ['get', 'height'] } },
    { id: 'blocks-active-line', type: 'line', source: 'blocks',
      filter: ['==', ['get', 'active'], true],
      paint: { 'line-color': '#fb923c', 'line-width': 2.5,
               'line-opacity': 0.9 } },
  ];
}

function buildStyle(base) {
  const style = base ? JSON.parse(JSON.stringify(base)) : fallbackStyle();
  style.sources = style.sources || {};
  style.sources.blocks = { type: 'geojson', data: blocks };
  style.sources.tracks = {
    type: 'geojson', data: { type: 'FeatureCollection', features: [] },
  };
  style.layers = (style.layers || []).concat(studioLayers());
  return style;
}

function applyHeight() {
  if (!map) return;
  map.setPaintProperty('blocks-active', 'fill-extrusion-height',
    ['*', ['get', 'height'], heightScale]);
  map.setPaintProperty('blocks-progress', 'fill-extrusion-height',
    ['*', ['get', 'height'], heightScale * 0.5]);
  map.setPaintProperty('blocks-done', 'fill-extrusion-height',
    ['*', ['get', 'height'], heightScale * 0.7]);
  map.setPaintProperty('blocks-future', 'fill-extrusion-height',
    ['*', ['get', 'height'], heightScale * 0.28]);
}

function init(data) {
  blocks = data.blocks;
  timeline = data.timeline;
  const volumes = blocks.features.map(
    (feature) => Number(feature.properties.volume_m3) || 1
  );
  const maxVolume = Math.max(...volumes, 1);
  for (const feature of blocks.features) {
    const volume = Number(feature.properties.volume_m3) || 1;
    feature.properties.height = 8 + 120 * (volume / maxVolume);
    byLabel[feature.properties.label] = feature;
  }
  for (const event of timeline.events) {
    if (!eventsByDay.has(event.day)) eventsByDay.set(event.day, []);
    eventsByDay.get(event.day).push(event);
    const eventYear = Math.min(10, Math.ceil(event.day / 365));
    if (!blockYears.has(event.block)) blockYears.set(event.block, new Set());
    blockYears.get(event.block).add(eventYear);
    const previous = byLabel[event.block]?.properties.last_event_day || 0;
    if (byLabel[event.block]) {
      byLabel[event.block].properties.last_event_day = Math.max(previous, event.day);
    }
  }
  makespan = Math.max(1, Number(timeline.makespan_day) || 1);
  $('day-range').max = makespan;
  const yearSelect = $('year-select');
  yearSelect.replaceChildren();
  for (let year = 1; year <= Math.min(10, Math.ceil(makespan / 365)); year += 1) {
    const option = document.createElement('option');
    option.value = String((year - 1) * 365 + 1);
    option.textContent = String(year);
    yearSelect.appendChild(option);
  }
  if (makespan > 1000) $('speed-select').value = '15';
  const style = buildStyle(data.baseStyle);
  map = new maplibregl.Map({
    container: 'studio-map',
    style,
    center: [-124.5, 54.5],
    zoom: 5,
    pitch: 58,
    bearing: -24,
    maxPitch: 80,
    attributionControl: true,
  });
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }),
                 'top-right');
  map.on('load', () => {
    for (const machine of Object.keys(machineColors)) {
      const element = document.createElement('div');
      element.className = 'machine-marker';
      element.textContent = machine;
      element.style.background = machineColors[machine];
      element.style.display = 'none';
      machineMarkers[machine] = new maplibregl.Marker({
        element, anchor: 'bottom',
      }).setLngLat([0, 0]).addTo(map);
    }
    applyHeight();
    updateDay(1);
  });
  map.on('click', 'blocks-active', (event) => {
    const feature = event.features && event.features[0];
    if (!feature) return;
    const p = feature.properties || {};
    new maplibregl.Popup({ closeButton: true, maxWidth: '280px' })
      .setLngLat(event.lngLat)
      .setHTML('<strong>' + (p.label || p.block_id) + '</strong><br>' +
        'Volume: ' + Math.round(Number(p.volume_m3) || 0).toLocaleString() +
        ' m³<br>Operating days: ' + (p.operating_days ?? '—') +
        '<br>Calendar window: days ' + p.first_day + '–' + p.last_day +
        '<br>Machines: ' + (p.machines || '—'))
      .addTo(map);
  });
  map.on('mouseenter', 'blocks-active', () => {
    map.getCanvas().style.cursor = 'pointer';
  });
  map.on('mouseleave', 'blocks-active', () => {
    map.getCanvas().style.cursor = '';
  });
  $('day-range').addEventListener('input', (event) => {
    stopPlay();
    updateDay(Number(event.target.value));
  });
  $('year-select').addEventListener('change', (event) => {
    stopPlay();
    updateDay(Number(event.target.value));
  });
  $('play-button').addEventListener('click', togglePlay);
  $('reset-button').addEventListener('click', resetView);
  $('follow-button').addEventListener('click', toggleFollow);
  $('orbit-button').addEventListener('click', toggleOrbit);
  $('speed-select').addEventListener('change', () => {
    if (timer) startPlay();
  });
  $('height-range').addEventListener('input', (event) => {
    heightScale = Number(event.target.value) || 1.4;
    applyHeight();
  });
}

Promise.all([
  fetch('/fhops/' + SLUG + '/scheduled.geojson').then((r) => r.json()),
  fetch('/fhops/' + SLUG + '/timeline.json').then((r) => r.json()),
  fetch('https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json')
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null),
]).then(([blocksData, timelineData, baseStyle]) => {
  init({ blocks: blocksData, timeline: timelineData, baseStyle });
}).catch(() => {
  const target = $('studio-map');
  if (target) target.textContent = '3D studio data unavailable';
});
</script>"""


def render_studio(
    *,
    slug: str,
    label: str,
    file_id: str,
    subtitle: str,
    summary: dict[str, Any],
    aac_m3: float | None,
) -> str:
    """Return the full-screen 3D studio page for one FHOPS scenario."""
    safe_slug = html.escape(slug)
    safe_label = html.escape(label)
    safe_file_id = html.escape(file_id)
    safe_subtitle = html.escape(subtitle)
    horizon = summary.get("horizon_days") or 0
    volume = summary.get("total_production_m3") or 0
    plan_kind = summary.get("plan_kind")
    if plan_kind in ("rolling10", "multiyear", "tactical_operational"):
        if plan_kind == "tactical_operational":
            plan_text = (
                f"ten-year tactical–operational MILP · "
                f"{horizon:,.0f}-day horizon"
            )
            note = (
                "Prototype animation of a ten-year tactical–operational FHOPS "
                "plan. The tactical MILP selects block areas and annual product "
                "volumes; ten annual operational seasons then schedule the "
                "machine days. It is not a production schedule. Drag to orbit, "
                "scroll to zoom."
            )
        else:
            plan_text = f"ten-year multi-year plan · {horizon:,.0f}-day horizon"
            note = (
                "Prototype animation of a ten-year multi-year FHOPS plan. Each "
                "year is an optimized 180-day annual season; the active blocks "
                "change by year. It is not a production schedule. Drag to orbit, "
                "scroll to zoom."
            )
        volume_label = "10-year harvested"
    else:
        plan_text = f"first-period pilot, compressed into a {horizon:,.0f}-day horizon"
        volume_label = "10-year period volume"
        note = (
            f"Prototype animation of the first-period FHOPS plan. The pilot "
            f"compresses ten years of AAC volume into a {horizon:,.0f}-day "
            "horizon; it is not a production schedule. Drag to orbit, scroll "
            "to zoom."
        )
    script = STUDIO_JS.replace("__SLUG__", safe_slug)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>3D harvest studio · {safe_label}</title>
  <link rel="stylesheet"
        href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css">
  {STUDIO_CSS}
</head>
<body>
  <div id="studio-map"></div>
  <header class="studio-head">
    <div class="studio-title">
      <p class="studio-kicker">FHOPS · 3D harvest studio</p>
      <h1>{safe_label}</h1>
      <p>{safe_file_id} · {safe_subtitle} · {plan_text}</p>
    </div>
    <div class="studio-actions">
      <a href="/fhops/{safe_slug}/theatre">Tree-scale theatre</a>
      <a href="/fhops/{safe_slug}">FHOPS summary</a>
      <a href="/instance/{safe_slug}/">WS4 model</a>
      <a href="/">All woodlots</a>
    </div>
  </header>
  <aside class="studio-legend">
    <div><span class="swatch" style="background:#334155"></span> Future block</div>
    <div><span class="swatch" style="background:#f97316"></span> Harvesting now</div>
    <div><span class="swatch" style="background:#14b8a6"></span> Harvested</div>
    <div><span class="swatch" style="background:#f8fafc;border-radius:50%"></span>
      Machine</div>
  </aside>
  <section class="studio-panel">
    <div class="studio-controls">
      <button id="play-button" class="primary" type="button">▶ Play</button>
      <button id="reset-button" type="button">Reset view</button>
      <button id="follow-button" type="button">Follow off</button>
      <button id="orbit-button" type="button">Orbit</button>
      <label for="height-range">Height</label>
      <input id="height-range" type="range" min="0.6" max="3" step="0.2"
             value="1.4" aria-label="3D height exaggeration">
      <label for="speed-select">Speed</label>
      <select id="speed-select">
        <option value="180">1×</option>
        <option value="90" selected>2×</option>
        <option value="35">5×</option>
        <option value="15">10×</option>
        <option value="6">25×</option>
      </select>
      <label for="year-select">Year</label>
      <select id="year-select" aria-label="Plan year"></select>
      <input id="day-range" type="range" min="1" max="1" value="1"
             aria-label="Harvest day">
      <span id="day-label">Day 1</span>
    </div>
    <div class="studio-hud">
      <span><strong id="follow-label">Following —</strong></span>
      <span><strong id="active-label">0 machines active</strong></span>
      <span><strong id="done-label">0 blocks harvested</strong></span>
      <span><strong id="volume-label">0 m³ harvested</strong></span>
      <span><strong>{aac_m3 or 0:,.0f} m³/yr</strong> annual AAC</span>
      <span><strong>{volume:,.0f} m³</strong> {volume_label}</span>
    </div>
    <p class="studio-note">{note}</p>
  </section>
  <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
  {script}
</body>
</html>"""
