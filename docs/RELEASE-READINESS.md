# Release readiness

Date: 2026-11-12  
Status: **release candidate, live read-only behind Cloudflare Access; OTP allowlist test pending**  
Tag: `v0.9.0-rc8`

## What passed

| Check | Result |
|---|---|
| Active woodlots catalogued | **845** |
| Buildable with public AAC | **798** |
| Built WS4 instances | **798 / 798** |
| FHOPS summaries | **798 / 798** |
| FHOPS maps, timelines, theatre data | **798 / 798** |
| Featured ten-year tactical–operational plans | **3 / 3** |
| Tactical validation plans (W1674, W0007) | **2 / 2** |
| W4W v1 calibrations | **798 / 798** |
| Portal population QA | **0 failures** |
| Tree Lab demo cases | **3 / 3** |
| Portal healthcheck | passed |
| Read-only smoke test | passed; write endpoints return **403** |
| Public hostname | `fresh-woodlotsbc.01101.dev`, Access **302** unauthenticated |
| Authenticated origin | confirmed by operator |
| OTP email allowlist | **pending a real Woodlots BC user** |
| BCCFA portal | **62 / 62**, untouched |
| Sphinx docs | published |

The full QA report is [`QA-POPULATION.md`](QA-POPULATION.md). It checks
six portal routes and five required artifacts for every built instance.

A separate read-only smoke test used `PUBLIC_READ_ONLY=1`, `DEMO_MODE=0` on a
temporary port. The landing page, a WS4 model, FHOPS, and Tree Lab all returned
**200**; `POST /api/runs` and `POST /api/search/portfolio` returned **403**.
The live service was not changed.

## Calibration status

The v1 clearcut calibration remains the population default. It is the only
method that can be applied consistently without a silviculture assumption for
every licence.

The audit found:

- median factor: **0.7554**;
- 10th–90th percentile: **0.3582–1.5891**;
- **216 / 798** within 80–120% of Proxy THLB;
- **157 / 798** outside the 0.4–2.0 method-check range;
- **50 / 798** extreme (<0.25 or >4.0).

Those cases are flagged in the portal as **⚠ method check**. They are a data
and method limitation, not a land-base result.

v2 is available only where a plan documents partial cutting:

| Licence | v1 factor | v2 factor | Benchmark |
|---|---:|---:|---|
| W0026 | 0.9022 | 3.9313 | v2 implausible; v1 retained |
| W1832 | 0.2156 | 0.8509 | v2 within +4.3% of published THLB |

Decision: **do not mass-switch to v2**. Select v2 per plan when the management
plan or WLP documents partial cutting or commercial thinning.

See [`aac/CALIBRATION-AUDIT.md`](aac/CALIBRATION-AUDIT.md) and
[`aac/CALIBRATION-V2.md`](aac/CALIBRATION-V2.md).

## Open release decisions

1. **Access mode.** The container now runs:
   ```text
   PUBLIC_READ_ONLY=1
   DEMO_MODE=0
   ```
   The hostname and Cloudflare Access application exist, and the operator has
   confirmed the authenticated origin is the Woodlots BC portal. The One-time
   PIN email allowlist still needs a real Woodlots BC user. See
   [`CLOUDFLARE-ACCESS.md`](CLOUDFLARE-ACCESS.md).

2. **Public hostname.** `https://fresh-woodlotsbc.01101.dev` resolves and
   returns a **302** to `ubc-fresh.cloudflareaccess.com` when unauthenticated.
   The container-local URL is `http://127.0.0.1:8795/`.

3. **Calibration presentation.** Decide whether method-check cards remain
   visible with warnings, or whether extreme cases are hidden from summary
   statistics. Current choice: keep them visible and flagged.

4. **AAC-pending licences.** **47** licences have no public AAC yet. They are
   catalogued and mapped but not built. Refresh when the next public AAC report
   lands.

5. **Non-public documents.** W0026's management plan and W4W project file are
   still unavailable. Do not block release on them; keep the caveat visible.

## Release gate

- [x] all built instances have FHOPS pages and artifacts;
- [x] population HTTP/artifact QA has zero failures;
- [x] Tree Lab cases render;
- [x] docs published;
- [x] calibration method decision documented;
- [x] portal switched to read-only and write guard verified;
- [x] hostname resolves and Cloudflare Access returns 302;
- [x] authenticated origin verified by operator;
- [ ] OTP allowlist login tested with a Woodlots BC user;
- [ ] non-allowlisted address rejected;
- [ ] Access removed after public review (if approved);
- [ ] release tag updated after the access decision.

## Rollback

```bash
sudo systemctl stop freshwl-portal
git -C /srv/shared-data/gep/ws4/fresh-woodlots checkout <previous-tag>
sudo systemctl start freshwl-portal
```
