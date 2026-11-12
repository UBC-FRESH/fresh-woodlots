# Woodlots BC portal hosting plan

Date: 2026-11-11
Status: pilot / demo
Scope: all active BC woodlot licences; 845 catalogued, 798 with public AAC.

## 0. Release status

The build-pipeline and portal QA are complete; the service remains a
release candidate in demo mode. See
[`RELEASE-READINESS.md`](RELEASE-READINESS.md) for the passed checks and the
open access-mode decision.

## 1. Current deployment

The portal is installed in the shared LXD container as
`freshwl-portal.service`:

```text
http://127.0.0.1:8795/
/health
/about
/terms
/privacy
/instance/<slug>/
```

Facts:

- one uvicorn worker, user `gep`, `MemoryMax=8G`, `CPUQuota=400%`;
- portal code at `/srv/shared-data/gep/ws4/fresh-woodlots`;
- WS4 UI from `/srv/shared-data/gep/ws4/ws4-public-demo`;
- 845 queue entries, 798 buildable, 47 catalogued with AAC pending;
- WS4 sub-apps are lazy-mounted, so 798 builds do not all load at startup;
- service is in demo mode (`PUBLIC_READ_ONLY=0`, `DEMO_MODE=1`), which
  enables the Plan tab, saved scenarios, and `POST /api/runs`.

The BCCFA portal remains on **8796** and Nemora on **8799**. Do not reuse those
ports.

## 2. Public hostname

Proposed hostname: `https://fresh-woodlots.01101.dev`.

The root host mapping (nginx / LXD proxy / Cloudflare Tunnel) is outside this
container and must point to container port **8795**. Until that is changed, use
the container-local URL or a Cloudflare Access service token.

## 3. Read-only public mode

For a public, non-editable release:

```text
PUBLIC_READ_ONLY=1
DEMO_MODE=0
```

Then re-add a read-only bind for the instance tree, and block non-GET/HEAD
methods under `/instance/` at the proxy. The read-only mode still serves the
landing page, map, `/about`, `/terms`, `/privacy`, and every built model's
read-only WS4 UI.

## 4. Capacity

- 845 catalogued instances; 798 buildable; only ready instances are mounted.
- Lazy mount keeps portal memory low; each opened model builds a WS4 app on
  first request.
- A full rebuild of all 798 instances is the expensive operation, not serving.
- One worker is enough for a pilot; add workers only after measuring.

## 5. Security boundaries

- no public shell, no OpenCode agent, no uploads;
- no raw TIPSY tables or government model bundles redistributed;
- no claim of statutory timber supply analysis;
- demo mode only behind Cloudflare Access and with rate limits on `/api/runs`;
- health check: `scripts/healthcheck.sh http://127.0.0.1:8795`.

## 6. Rollback

```bash
sudo systemctl stop freshwl-portal
git -C /srv/shared-data/gep/ws4/fresh-woodlots checkout <previous-tag>
sudo systemctl start freshwl-portal
```
