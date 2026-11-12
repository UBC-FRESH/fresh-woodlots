# Tree Lab

The portal mounts the experimental FHOPS **Tree Lab** sandbox at `/treelab/`.
It replays one FHOPS block at tree scale: synthetic trees, feller, skidder,
processor, loader, decks, and trucking.

The three featured woodlots have precomputed demo cases:

| Woodlot | Case | Block | Trees | Direct link |
| --- | --- | --- | ---: | --- |
| W0026 Chinook Woodlots | `w0026-61` | W0026-61 | 648 | `/treelab/?case=w0026-61&run=demo-1` |
| W1548 Fibre Farms | `w1548-24` | W1548-24 | 120 | `/treelab/?case=w1548-24&run=demo-1` |
| W2023 Boomer Enterprises | `w2023-94` | W2023-94 | 187 | `/treelab/?case=w2023-94&run=demo-1` |

The FHOPS page for each featured pilot links directly into its Tree Lab run.

## What is real and what is synthetic

- The **block footprint** is the FHOPS scheduled-block polygon.
- The **tree list** is a deterministic synthetic visual sample, not a surveyed
  inventory or an ITD/ITC product.
- The **machine choreography** is illustrative. It is not a FHOPS solve, a
  production plan, or a cost model.
- There is **no LiDAR DEM or step map** in these cases.

## Runtime

Tree Lab is an optional mount. It requires the external
`fhops-ground-support` package and a FHOPS installation that provides the
`fhops tree system` and `fhops tree scene` commands.

The systemd unit adds the support package to `PYTHONPATH`:

```text
/srv/shared-data/gep/ws4/fhops-ground-support
/srv/shared-data/gep/ws4/fhops-ground-support/src
```

If the package is missing, the portal stays up and simply omits Tree Lab.

The agent console is disabled (`allow_agent=False`). The Tree Lab page is a
demo surface, not a login-protected planning tool.

## Generate or refresh a case

```bash
export PYTHONPATH=/srv/shared-data/gep/ws4/fhops-ground-support:/srv/shared-data/gep/ws4/fhops-ground-support/src
python scripts/prepare_treelab_demo.py --slug wl-w0026 --block W0026-61
python scripts/prepare_treelab_demo.py --slug wl-w1548 --block W1548-24
python scripts/prepare_treelab_demo.py --slug wl-w2023 --block W2023-94
```

The script reads the block polygon and synthetic theatre trees, writes the case
under `treelab_cases/<case-id>/`, runs the tree system, and stores the replay
under `treelab_runs/<case-id>/demo-1/`.

Use `--skip-run` to create the case without running the simulator.

## Files

```text
treelab_cases/<case-id>/case.json
treelab_cases/<case-id>/scenario/
treelab_cases/<case-id>/tree_inventory/
treelab_runs/<case-id>/demo-1/run.json
treelab_runs/<case-id>/demo-1/system/
treelab_runs/<case-id>/demo-1/scene/
```

Cases are committed; generated runs are ignored by Git and must be rebuilt on a
fresh checkout. The FHOPS page appends `run=demo-1` only when the run exists.

## Add another woodlot

Pick a block label from:

```text
instances/<slug>/fhops/out/theatre.json
instances/<slug>/fhops/out/scheduled_blocks.geojson
```

Then run `prepare_treelab_demo.py` with that slug and block, add the case ID to
`TREELAB_CASES` in `portal/fhops_page.py`, and restart
`freshwl-portal.service`.
