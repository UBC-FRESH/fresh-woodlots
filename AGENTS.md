# AGENTS.md

Working contract for coding agents in Fresh Woodlots. Keep it short.
Each rule either checks itself or points to the page that explains it.

## Session start

Read, in order:

1. This file.
2. `ROADMAP.md` — the active phase and its exit criteria.
3. `docs/project-brief.md` — vision, scope, decoded brief, risks.
4. `docs/data-sources.md` — public sources and provenance rules.
5. The tests and scripts that govern your task.

## Working principles

- **Public data only.** No private inventories, credentials, or client files.
- **Provenance or it did not happen.** Every derived artifact records source,
  retrieval date, query, and SHA256.
- **One bounded move at a time.** Stop and report after each move.
- **No guessed values.** A failed fetch or model run is a recorded failure.
- **Small, reproducible commands.** A fresh clone should regenerate the
  catalog with one script.
- **Preserve uncertainty.** Say what you did not verify, and why.
- **Sanitized output.** No secrets, raw transcripts, or personal paths in
  tracked files.

## Data rules

- The catalog source is the public FTEN managed licence layer, filtered to active W file IDs. Do not add a
  private source without an explicit decision.
- Large public inputs belong in DataLad or a cache, not Git.
- Woodlot boundaries are public; treat the model outputs as public
  too, with a visible disclaimer.
- Never commit raw BC government model bundles or TIPSY/VDYP tables.

## Code rules

- Python 3.11+.
- Type hints on public functions; numpy-style docstrings.
- Tests for every transform that can fail.
- No network in unit tests. Live-source tests are integration tests and skip
  cleanly when the source is unavailable.
- Keep the catalog transform (`src/fresh_wl/catalog.py`) separate from the
  fetch (`scripts/fetch_woodlot_catalog.py`) so the rules stay testable.

## Gates

Run before closing a task:

```bash
pytest
ruff check .
```

Record the result in the phase report. A red gate is fixed or reported with
evidence before moving on.

## Scope discipline

- Stay inside the active phase.
- Do not start a batch build before the three-CFA pilot is closed.
- Do not weaken provenance or the public-assistant boundary to make a demo
  easier.
