# BCCFA handoff

This is a demo runbook for the BC Community Forest Association.

## What it is

A free, public-data planning portal with one WS4 strategic model and one
FHOPS operational pilot for each of the 62 active community forest agreements
in British Columbia.

- Portal: `http://127.0.0.1:8796/`
- Sources & methods: `http://127.0.0.1:8796/about`
- Data: public BC datasets only
- Cost to a community forest: none

## Ten-minute demo

1. Open the portal. Point out the province map, the 62 CFA cards, and the
   search box.
2. Search for a familiar community forest and open it.
3. In the WS4 app:
   - show the block map at high zoom (polygons, not circles)
   - show the accounts and the AAC target band
   - open the `aac_baseline` run
   - point out the harvest and area accounts
4. Back on the portal card, show the FHOPS line:
   - blocks completed, volume, makespan
5. Open **Sources & methods** and show that every data source, the model
   chain, and the caveats are visible.

## What to say

- “One instance per community forest, built from public data.”
- “WS4 answers the long-term landscape question; FHOPS answers the
  block-and-machine question.”
- “The AAC baseline is a 1.2× band, not a statutory determination.”
- “Every number can be traced to a public source and a build manifest.”
- “The whole set is reproducible and free to the association.”

## What not to say

- Do not call the AAC baseline a statutory timber supply analysis.
- Do not present the FHOPS pilot as a production operating plan.
- Do not hide the surrogate species mappings.
- Do not imply the Proxy THLB is the official TSR THLB.

## Current limits

- Proxy THLB, not the statutory TSR land base.
- Surrogate species curves where TIPSY has no BC code.
- VDYP still runs under Wine; TIPSY does not.
- FHOPS is first-period, ground-based, rate-fixed, and has no roads or costs.
- K1E cannot hold its AAC at the 1.2× band in every period.

## Refresh or extend

```bash
python scripts/fetch_cfa_catalog.py      # catalog + AAC + queue
python scripts/fetch_thlb.py             # Proxy THLB
python scripts/prepare_pilot.py --pilots config/pilots_batch.yaml
python scripts/batch_build.py --jobs 8
python scripts/batch_fhops.py --jobs 8
./run_portal.sh
```

The build is resumable; completed instances are skipped.

## Next for BCCFA

1. Pick 5–10 member community forests for a guided pilot.
2. Review the land-base and species assumptions with each manager.
3. Add local TSR/FSP or RESULTS/SPAR evidence where available.
4. Decide the public hosting and support model.
