# How to read this portal

The portal is a **pilot**, not a statutory timber supply analysis. Each page
mixes public data, a strategic model, and an operational demonstration. Read
the labels before treating a number as a land-base fact.

## Landing page

Each card shows:

- **File ID and licensee** — the public woodlot licence identity.
- **Area** — licence/AOI area from the public tenure layer.
- **AAC** — the published allowable annual cut, when available.
- **Proxy THLB** — the provincial strategic timber-harvesting land base.
- **W4W** — the simplified Woodlot-for-Windows calibration result.
- **FHOPS** — the operational pilot status.

**47 licences** are catalogued but not built because their public AAC is still
pending. That is a data status, not a failure.

## W4W calibration line

The line looks like:

```text
W4W: 660 ha net, factor 0.9022, 99% of Proxy THLB
```

- **Net area** is the area implied by reproducing the published AAC.
- **Factor** is a calibration device, not a measured THLB.
- **% of Proxy THLB** compares the calibrated area with the provincial layer.

If the card says **⚠ method check**, the factor is outside the 0.4–2.0 range.
Those cases need the local management plan or WLP before interpretation.
Do not treat a method-check factor as a THLB estimate.

The v1 model is a clearcut/oldest-first replica. v2 is used only where a plan
documents partial cutting or commercial thinning.

## WS4 model page

The model page is a strategic, long-horizon view:

- AAC baseline and saved scenarios;
- land-base and yield assumptions;
- block map and provenance;
- scenario comparison tools.

The model is built from public VRI, Proxy THLB, VDYP, TIPSY, and FEMIC curves.
It is not a replacement for the licence's management plan.

## Ask assistant

The portal landing page has a **+ Ask** button; it opens a portal-native
assistant panel without leaving the page. The WS4 model page also has an
**Ask** control. It is an LLM assistant with access
to the selected instance and the OpenCode tools. Treat it as an authenticated
pilot assistant, not an authoritative interpreter of the model.

The assistant is the only write-like exception in the otherwise read-only
portal. Access to the portal is therefore the security boundary.

## FHOPS page

Most woodlots have a **first-period, rate-fixed pilot**. The volume is often
ten years of AAC compressed into a short operating horizon. It is not annual
production and not a production plan.

The three featured pilots have a **ten-year tactical–operational MILP**:

- the tactical layer chooses block areas and annual product volumes;
- ten annual 180-day operational seasons schedule machine days;
- blocks are real FHOPS polygons;
- product yields use a transparent 70/30 sawlog/pulp split.

The page shows annual harvested, processed, staged, blocks treated, and
ten-year totals. FHOPS does not model road-building, silviculture, landing
geometry, or full real costs.

## 3D block studio

The studio animates the scheduled blocks by day:

- **Future block** — not yet worked;
- **Harvesting now** — active in the current day;
- **Harvested** — completed;
- **Operating days** — days with an assignment, not the full calendar window.

Machine movement is a straight-line marker between block centroids. It is not
a road route or a terrain-sensitive machine path.

## Tree Lab

Tree Lab is an experimental tree-scale replay:

- the block footprint is real;
- the tree list is a synthetic visual sample;
- the machine choreography is illustrative;
- there is no surveyed LiDAR terrain in the featured cases.

Use it for communication and intuition, not for inventory, costing, or
operational planning.

## Sources and caveats

Open **Sources & methods** for the data sources and model chain.

Key caveats:

- Proxy THLB is a strategic layer, not the statutory THLB.
- Some TIPSY species lack a BC code and use a documented surrogate.
- VDYP runs the Windows console under Wine; TIPSY does not.
- Calibration factors outside 0.4–2.0 are flagged.
- 47 licences await a public AAC.
- W0026's management plan and W4W project file are not public.
- The portal is a prototype; use professional judgment.

## Access

The pilot is read-only and behind Cloudflare Access at
`https://fresh-woodlotsbc.01101.dev`. The portal rejects writes; scenario
editing and Solve are available only in a temporary operator-managed demo
mode behind Access.
