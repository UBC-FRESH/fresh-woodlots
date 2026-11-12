# Release notes

## v0.9.0-rc4 — 2026-11-12

Added a tactical validation set for W1674 and W0007, widened the candidate
block pool to all WS4 blocks, and added the `/benchmarks` portal page. This
fixed the W1548 compressed-block volume/area issue.

## v0.9.0-rc3 — 2026-11-12

Status: read-only release candidate behind Cloudflare Access  
Host: `https://fresh-woodlotsbc.01101.dev`

### Added

- formal FHOPS tactical–operational MILP for W0026, W1548, and W2023;
- ten annual operational seasons per featured pilot;
- annual harvested, processed, staged, blocks-treated, and 10-year totals;
- tactical labels and caveats on FHOPS pages and cards;
- year-aware 3D studio focused on the active block;
- operating-days field in studio block popups;
- Tree Lab cases for all three featured pilots;
- pilot brief, demo script, how-to-read guide, and release notes;
- tactical validation runs for W1674 and W0007, plus a public `/benchmarks` page.

### Verified

```text
845 catalogued
798 built
798 FHOPS summaries/maps/theatre
798 W4W v1 calibrations
3 tactical ten-year plans
3 Tree Lab cases
0 portal QA failures
```

Read-only mode:

```text
PUBLIC_READ_ONLY=1
DEMO_MODE=0
non-GET/HEAD/OPTIONS -> 403
```

### Known limitations

- 47 licences await a public AAC.
- 157 / 798 v1 calibrations are outside the 0.4–2.0 method-check range.
- v2 partial-cut calibration exists only for W0026 and W1832.
- Featured Tree Lab cases use synthetic tree lists; no ALS terrain is
  materialized yet.
- FHOPS does not model roads, silviculture, landing geometry, or full costs.
- Cloudflare Access One-time PIN email allowlist is awaiting a Woodlots BC
  test user.

### Rollback

```bash
sudo systemctl stop freshwl-portal
git -C /srv/shared-data/gep/ws4/fresh-woodlots checkout v0.9.0-rc2
sudo systemctl start freshwl-portal
```

The write-enabled demo unit is backed up as
`/etc/systemd/system/freshwl-portal.service.bak-demo`.
