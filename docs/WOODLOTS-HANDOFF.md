# Woodlots BC demo runbook

## Before the demo

```bash
curl -s http://127.0.0.1:8795/health
# expected: instances=845, buildable=798, ready as built
cd /srv/shared-data/gep/ws4/fresh-woodlots
scripts/healthcheck.sh http://127.0.0.1:8795
```

Open `http://127.0.0.1:8795/`.

## Demo flow

1. **Landing page.** All 845 active woodlot licences, 798 with public AAC and
   47 catalogued with AAC pending. The three featured pilots are first:
   - W0026 Chinook Woodlots (Campbell River)
   - W2023 Boomer Enterprises (Okanagan)
   - W1548 Fibre Farms (Prince George)
2. **Province map.** The featured pilots are labelled; click one to open it.
3. **Open W0026.** Show the WS4 map, the `aac_baseline` run, and the
   block polygons at detail zoom.
4. **Plan tab.** Show the scenario selector:
   - AAC baseline (1.2×)
   - Conservative harvest (0.5–0.8×)
   - Higher harvest (1.5–2×)
   Switch scenarios, show the target matrix, penalty ledger, and chart.
5. **Solve.** The Solve panel is enabled in demo mode. Use a short run if
   demonstrating; do not leave a long run unattended.
6. **FHOPS.** On the card/page, show the first-period ground-based operational
   pilot summary.
7. **Sources & methods.** `/about` documents the public data, model chain,
   surrogates, Wine exception, and caveats. `/terms` and `/privacy` are linked
   in the footer.

## Talking points

- 845 public woodlot licences; 798 already have public AAC, 47 are catalogued
  and waiting for the next public report.
- Each model is built from public VRI, Proxy THLB, VDYP, and TIPSY data; no
  private licensee data is used.
- The Proxy THLB is factor-weighted: `pthlb_fact` is a partial contribution, so
  the WS4 managed area can be much smaller than the licence/AAC area. Per-hectare
  harvest on the managed area will therefore look higher than the licence-wide
  AAC MAI. That is a land-base effect, not a yield-curve error.
- The portal is a planning prototype, not a statutory AAC determination.
- The same chain that built the 62 community forests scales to the woodlot
  sector; the remaining work is batch compute and public hosting.

## If a model does not load

- Check `/health`; if `ready` dropped, restart `freshwl-portal`.
- If a new instance finished building after portal start, restart the portal
  to mount it.
- If a run is missing, open the Run selector and choose `aac_baseline`.
- If the map is slow on a large woodlot, zoom in; the portal uses a simplified
  low-zoom overview and full detail at zoom 7+.
