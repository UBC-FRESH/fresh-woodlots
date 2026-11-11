# P2 batch build

Date: 2026-11-10
Status: complete

## Final result

| State | Count |
|---|---:|
| Active CFAs in the catalog | 62 |
| Built and mounted | **62** |
| Full bundles | **62** |
| Partial bundles | **0** |
| Failed | **0** |

The batch ran with 8 concurrent builds and a memory-aware job limit. The first
parallel wave finished in **1h56m**; the retry and partial-bundle salve waves
finished the remainder.

## Runner

`scripts/batch_build.py`:

- reads `queue/cfa_build_queue.json`
- runs `scripts/build_instance.sh` with FHOPS skipped and a 2-minute greedy
  AAC search
- allows partial bundles by default (`FEMIC_ALLOW_PARTIAL_BUNDLE=1`)
- writes `batch/logs/<slug>.log` and `batch/logs/<slug>.time.log`
- updates queue status to `building`, `built`, or `failed`
- records elapsed time and peak RSS
- resumes with `--start-at`, `--only`, `--retry-failed`, `--reset-building`
- parallelizes with `--jobs` and a memory guard

## Bundle status

All 62 instances have complete post-TIPSY bundles. Earlier "partial" labels
came from the first salvage pass, before the remaining species mappings and the
VDYP zero-sample guard were applied. The final full reruns produced
`warning: 0 VDYP curve combinations without AU mapping` for every instance, so
the queue now records `bundle: full` for all 62.

## Species surrogates

The TIPSY database does not carry every BC species code. Missing codes are
mapped to the closest available table and recorded in each instance's
`config/species_overrides.yaml` and the fresh-tipsy sidecar:

| Raw code | Mapping |
| --- | --- |
| SB, SE, S, SN, SX, SXE, SXL, SXW | SW |
| SS | SS |
| P, PA, PJ, PL, PLC, PLI, PM, PW, PY | PLI |
| B, BA, BB, BG, BL, BM, BP | FDI interior / FDC coast |
| L, LA, LS, LT, LW | FDI interior / FDC coast |
| H, HM, HWI, HW | HWI interior / HWC coast |
| C, CW, YC | CW |
| F, FD, FDC, FDI | FDI interior / FDC coast |
| DR | FDI interior / FDC coast |
| AC, AT, EP, birch, willow, alder, cherry, maple | AT |
| NC | NC |

These are surrogates, not species-specific curves.

## Final fixes

1. **Species codes** `SE`, `PY`, and `H` were added to the mapping. K1D also
   had a stale override file from the first pass; regenerating all batch
   configs fixed it.
2. **VDYP zero-sample guard.** K2O and K4F hit
   `ZeroDivisionError: division by zero` when a stratum's bootstrap target was
   zero. A guard in `femic/src/femic/pipeline/vdyp_stage.py` returns the
   already-run curves when the target is zero.
3. **Partial-bundle patch.** Missing AU/curve mappings are warnings when
   `FEMIC_ALLOW_PARTIAL_BUNDLE=1`.

## Portal

All 62 instances are mounted at `http://127.0.0.1:8796/`. Blocks render as
full-detail polygons above zoom 7, with a 25 m overview below that.

## Next

1. Label partial instances in the portal and reports.
2. Add the AAC flow shape and FHOPS to the remaining instances.
3. Run the source-data and provenance hardening pass.
4. Prepare the BCCFA pilot handoff.
