"""Env-gated FEMIC patch for partial community forest bundles.

When ``FEMIC_ALLOW_PARTIAL_BUNDLE=1``, missing AU/curve mappings are warnings
instead of fatal errors. This lets small custom AOIs complete with a partial
bundle instead of failing the whole build.
"""

from __future__ import annotations

import os


def _warn_curve(*, missing_df: object, top_n: int = 10) -> None:
    try:
        count = len(missing_df)  # type: ignore[arg-type]
    except TypeError:
        count = "unknown"
    print(
        f"warning: {count} VDYP curve combinations without AU mapping; "
        "continuing with a partial bundle"
    )


def _warn_au(*args: object, **kwargs: object) -> None:
    print("warning: residual AFLB rows unmapped; continuing with a partial bundle")


if os.environ.get("FEMIC_ALLOW_PARTIAL_BUNDLE") == "1":
    try:
        import femic.pipeline as _pipeline
        import femic.pipeline.bundle as _bundle
        import femic.pipeline.tsa as _tsa

        _bundle.validate_complete_au_curve_mappings = _warn_curve
        _pipeline.validate_complete_au_curve_mappings = _warn_curve
        _tsa.validate_complete_au_assignment = _warn_au
        if hasattr(_pipeline, "validate_complete_au_assignment"):
            _pipeline.validate_complete_au_assignment = _warn_au

        import femic.workflows.legacy as _legacy

        _legacy.validate_complete_au_curve_mappings = _warn_curve
        _legacy.validate_complete_au_assignment = _warn_au
    except Exception as exc:  # pragma: no cover - best-effort patch
        print(f"warning: partial-bundle patch failed: {exc}")
