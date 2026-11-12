# Release notes

## v0.9.0-rc11 — 2026-11-12

The landing-page **+ Ask** button now opens the portal-native assistant panel
in place; it no longer navigates to a WS4 instance. The panel calls the W0026
chat endpoint and keeps the conversation on the landing page.

## v0.9.0-rc10 — 2026-11-12

Added a **+ Ask** button to the portal landing page. It opens a portal-native
assistant panel without leaving the landing page or opening a WS4 instance.
The assistant remains Access-gated and is the only non-GET exception to the
read-only guard.

## v0.9.0-rc9 — 2026-11-12

- Removed the chaotic dotted machine tracks from the 3D harvest studio.
- Enabled the WS4 **Ask** LLM assistant behind Cloudflare Access.
- Chat is the only non-GET exception to the portal read-only guard; all other
  writes remain blocked.
- The assistant runs the OpenCode CLI as the service user with the selected
  instance directory as its working directory.

## v0.9.0-rc8 — 2026-11-12

Rebuilt the remaining 64 FHOPS area-check cases with all compiled WS4 blocks.
All 798 instances now pass the selected-area audit (0 check, 0 extreme, 0
missing). Median volume per selected hectare is 413.9 m³/ha; maximum is
999.7 m³/ha.

## v0.9.0-rc7 — 2026-11-12

Rebuilt the six FHOPS cases above 2,000 m³ per selected hectare (W0312, W1552,
W1590, W1841, W1877, W1903) with all compiled WS4 blocks. All six cleared the
area check. The remaining 64 check cases are in the 1,000–2,000 m³/ha range.

## v0.9.0-rc6 — 2026-11-12

Rebuilt the five extreme FHOPS area-check cases (W0307, W1591, W1601,
W1612, W2027) with all compiled WS4 blocks. All five cleared the area check
and retained zero sequencing violations. The audit now has 70 check cases,
0 extreme cases, and 0 missing-area cases.

## v0.9.0-rc5 — 2026-11-12

Added the FHOPS selected-area audit. The portal now labels compressed pilots
with high period volume per selected hectare as **⚠ area check**. The audit
found 70 check cases, 0 extreme cases, and no missing-area cases after the
extreme-case rebuild.

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
