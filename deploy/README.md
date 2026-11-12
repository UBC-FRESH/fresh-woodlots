# Deployment templates

These are templates for the Woodlots BC portal. The live container service is
`freshwl-portal.service` on **127.0.0.1:8795**.

## Files

| File | Purpose |
| --- | --- |
| `freshwl-portal.container.service` | systemd unit for this LXD container |
| `nginx-limits.conf` | nginx rate-limit zones |
| `nginx-community-forests.conf.example` | site template; rename and point at 8795 for woodlots |

## Installed in this container

```bash
sudo cp deploy/freshwl-portal.container.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now freshwl-portal
sudo systemctl status freshwl-portal
journalctl -u freshwl-portal -f
```

The unit uses the newer WS4 UI:

```text
PYTHONPATH=/srv/shared-data/gep/ws4/ws4-public-demo:/srv/shared-data/gep/ws4/fresh-woodlots:/srv/shared-data/gep/ws4/fhops-ground-support:/srv/shared-data/gep/ws4/fhops-ground-support/src
PUBLIC_READ_ONLY=0
DEMO_MODE=1
WS4_OVERVIEW_ZOOM=0
```

For public read-only hosting:

```text
PUBLIC_READ_ONLY=1
DEMO_MODE=0
```

and re-add a read-only bind for the instance tree.

## Verify

```bash
scripts/healthcheck.sh http://127.0.0.1:8795
```

## Rollback

```bash
sudo systemctl stop freshwl-portal
git -C /srv/shared-data/gep/ws4/fresh-woodlots checkout <previous-tag>
sudo systemctl start freshwl-portal
```
