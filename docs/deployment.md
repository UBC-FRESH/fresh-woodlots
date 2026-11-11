# Deployment

## Container service

The portal runs as `freshwl-portal.service` in the shared LXD container:

```bash
sudo systemctl status freshwl-portal
sudo systemctl restart freshwl-portal
journalctl -u freshwl-portal -f
```

It listens on `127.0.0.1:8795`. The BCCFA portal remains on `8796` and Nemora on
`8799`.

## Demo vs read-only

The current unit uses:

```text
PUBLIC_READ_ONLY=0
DEMO_MODE=1
WS4_OVERVIEW_ZOOM=0
```

For public read-only hosting, set `PUBLIC_READ_ONLY=1`, `DEMO_MODE=0`, and
re-add a read-only bind for the instance tree. See
`PUBLIC-HOSTING-PLAN.md` and `WOODLOTS-HANDOFF.md`.

## GitHub Pages

The Sphinx source is in `docs/`. The workflow at
`.github/workflows/docs.yml` builds it and deploys it with GitHub Pages when
the repository is pushed to GitHub.

1. Push the repository to GitHub.
2. In **Settings → Pages**, set **Source** to **GitHub Actions**.
3. Set `DOCS_BASEURL` if the site is not under the default
   `https://ubc-fresh.github.io/fresh-woodlots/`.
4. Push to `main` or run the workflow manually.

Local build:

```bash
/home/gep/.venv/bin/pip install -r docs/requirements.txt
cd docs && make html
# open docs/_build/html/index.html
```
