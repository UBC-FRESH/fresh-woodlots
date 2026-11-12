# Cloudflare Access handoff

Status: **blocked outside the container**  
Target hostname: `https://fresh-woodlots.01101.dev`

The container is ready:

```text
127.0.0.1:8795
PUBLIC_READ_ONLY=1
DEMO_MODE=0
non-GET/HEAD/OPTIONS -> 403
```

The remaining work is on the root host and in Cloudflare. The container does
not have root-host SSH access or a Cloudflare API token.

## 1. Root-host ingress

The BCCFA portal already provides the reference topology:

```text
browser
  └─ Cloudflare Access
       └─ Cloudflare Tunnel
            └─ root host nginx
                 └─ LXD container 10.232.253.210
                      └─ 127.0.0.1:8795
```

Add `fresh-woodlots.01101.dev` to the root-host ingress, pointing at the
container's **8795** port. The existing `fresh-bccfa.01101.dev` route is the
template; do not change its upstream.

Two equivalent deployment points are possible:

- add an ingress rule to the existing root-host Cloudflare Tunnel and route
  through nginx to the container; or
- add an LXD proxy / host forward from the container IP to `127.0.0.1:8795`.

The upstream must be **8795** for Woodlots BC. Do not reuse 8796 (BCCFA) or
8799 (Nemora).

Verify the origin before enabling Access:

```bash
# on the root host
curl -sS http://10.232.253.210:8795/health
# expected: read_only=true, demo_mode=false, ready=798
```

If the container IP is not reachable from the root host, use the existing LXD
proxy pattern used by BCCFA.

## 2. Cloudflare Access application

Create a Zero Trust Access application for:

```text
fresh-woodlots.01101.dev
```

Recommended first policy:

- allow a named Woodlots BC email allowlist, or the agreed `@woodlotsbc.ca`
  domain;
- keep UBC CWL / Globus or the existing identity providers if that is the
  agreed login method;
- add the existing One-time PIN provider if external reviewers need it;
- session duration: 24 hours or the agreed shorter period;
- do not create a public bypass during the first phase.

Use the same account and Access organization as `fresh-bccfa.01101.dev`. The
Cloudflare API workflow in the BCCFA handoff can be reused with the domain
changed:

```text
/srv/shared-data/gep/ws4/fresh-community-forests/docs/handoff-cloudflare-otp.md
```

Do not commit the API token. Store it on the root host mode `600`.

## 3. Verify the public path

Unauthenticated:

```bash
curl -sS -D - -o /dev/null https://fresh-woodlots.01101.dev/ | head
```

Expected: **302** to `ubc-fresh.cloudflareaccess.com`, not the portal.

Authenticated service-token check:

```bash
CF_ACCESS_CLIENT_ID=... \
CF_ACCESS_CLIENT_SECRET=... \
scripts/healthcheck.sh https://fresh-woodlots.01101.dev
```

Expected:

```json
{
  "status": "ok",
  "instances": 845,
  "ready": 798,
  "buildable": 798,
  "pending_aac": 47,
  "read_only": true,
  "demo_mode": false
}
```

Then check:

- `/` landing page;
- `/instance/wl-w0026/`;
- `/fhops/wl-w0026`;
- `/treelab/?case=w0026-61&run=demo-1`;
- `POST /instance/wl-w0026/api/runs` returns **403** (read-only guard).

## 4. After the Access-protected review

If Woodlots BC approves a public launch:

1. Remove the Access application or add the approved public policy.
2. Add a Cloudflare WAF/rate limit for `/api/` and `/instance/`.
3. Keep the portal read-only permanently for public traffic.
4. Re-run `scripts/qa_portal_population.py` and `scripts/healthcheck.sh`.
5. Record the change in `RELEASE-READINESS.md`.

Do not remove Access before the public review is signed off.

## 5. What the container cannot do

- edit the root-host tunnel or nginx configuration;
- create the Cloudflare Access application without an API token;
- add DNS for `fresh-woodlots.01101.dev` without the root host or Cloudflare
  account access.

Those steps require the root-host operator or a scoped Cloudflare API token.
