# 10-minute demo script

Host: `https://fresh-woodlotsbc.01101.dev`  
Featured demo: W0026 Chinook Woodlots

## 0:00–1:00 — Set the frame

Say:

> Every active woodlot licence in BC is in the catalogue. 798 have a public
> AAC and a built strategic model. The same chain is used for every licence;
> the three featured pilots get a deeper operational demonstration.

Show the landing page:

- 845 catalogued;
- 798 built;
- 47 AAC-pending;
- three featured pilots.

## 1:00–2:30 — Province and card

Search for a local woodlot and open its card. Point out:

- file ID and licence name;
- licence area and AAC;
- Proxy THLB;
- W4W net area/factor;
- FHOPS line.

If the W4W line says **⚠ method check**, explain that the factor is outside
the 0.4–2.0 calibration range and is not a published THLB.

## 2:30–4:00 — WS4 strategic model

Open W0026.

Show:

- province/woodlot map;
- AAC baseline;
- land-base and yield assumptions;
- Plan tab and saved scenarios;
- the caveat that this is a prototype, not a statutory analysis.

## 4:00–6:00 — Ten-year FHOPS plan

Open `/fhops/wl-w0026`.

Show:

- annual AAC;
- annual harvested, processed, and staged;
- blocks treated;
- ten-year volume;
- tactical–operational MILP explanation;
- downloadable scenario and solution files.

Emphasize:

> The tactical layer chooses block areas and annual product volumes. Ten
> annual operational seasons then schedule machine days. It is not one giant
> production plan.

## 6:00–7:30 — 3D block studio

Open `/fhops/wl-w0026/studio`.

- Choose Year 1, then Year 5.
- Press play.
- Show future / harvesting / harvested blocks.
- Show machine markers and operating days vs calendar window.

## 7:30–8:30 — Tree Lab

Open `/treelab/?case=w0026-61&run=demo-1`.

- Play the feller/skidder/processor sequence.
- Show the unprocessed deck and processed log pile.
- State clearly: trees are synthetic, terrain is not surveyed, choreography
  is illustrative.

## 8:30–9:30 — Evidence and caveats

Open `/about` and `/guide`.

Point out:

- public data sources;
- FEMIC → WS4 → FHOPS chain;
- 157 method-check calibrations;
- 47 AAC-pending licences;
- no roads, silviculture, or real costs in FHOPS;
- W0026 management plan/W4W project not public.

## 9:30–10:00 — Close

Say:

> The portal is free to Woodlots BC members, read-only for the pilot, and
> every model is reproducible from public data. The next step is member
> validation, starting with a small set of woodlots and their management
> plans.

## If asked for a write-enabled demo

The live service is read-only. A temporary demo mode can be restored behind
Cloudflare Access by an operator; do not expose write mode publicly.
