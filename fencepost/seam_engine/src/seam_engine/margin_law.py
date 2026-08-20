"""Ogun's margin law, extracted to one dependency-light module.

`ranking.rank` and `audit._audit_primary` both need to answer the exact
same yes/no question: does a candidate's confidence lead the runner-up by
at least the recorded separation margin? Until task 902 each module
answered it with its own independent copy -- `ranking.py`'s own copy
already carried task 895's fix (round the EXACT lead to 10 decimal places,
enough to erase IEEE-754 dust, far too fine to round across a real 2-dp
confidence boundary; a display-rounded 4-place decision is off-by-one's
own class of miscount -- a true lead of 0.14996 rounds UP to 0.1500 and
would wrongly clear a 0.15 margin, crying wolf, the fatal direction Ogun's
law forbids). `audit.py`'s copy was still the pre-fix 4-place shape and
never inherited the correction -- the self-audit that exists to catch a
false PRIMARY could itself rubber-stamp CONFIRMED one.

This module exists as its own file, separate from `ranking.py`, on
purpose: `ranking.py` imports `seam_engine.scan` for `GapCandidate`'s type,
and `scan.py` imports `httpx` -- a real dependency `ranking.py` carries for
a type only, but one `audit.py`'s callers must not inherit just to check
one float comparison. `tools/ritual_check.py` loads `seam_engine.audit`
under plain `python3` (no `httpx` installed there; only the `uv`-managed
fencepost venv carries it) via `strategy_audit_target.py` -- if `audit.py`
imported `ranking` directly, that plain-python3 path would break importing
`httpx` transitively to check a float boundary. This module carries the
law and nothing else, so both callers can share it without either
inheriting a dependency it doesn't need.

Sworn on iron, same law, in one place.
"""
from __future__ import annotations

# Fine enough to erase float noise (~1e-16), coarse enough to never round
# across a real boundary at the 2-dp precision confidences carry today.
MARGIN_DECISION_PLACES = 10


def clears_margin(exact_lead: float, margin: float) -> bool:
    """True iff `exact_lead` is at least `margin`, with IEEE-754 dust
    cleaned but no rounding across the real margin boundary. See the
    module docstring for the full derivation (task 895, task 902)."""
    return round(exact_lead, MARGIN_DECISION_PLACES) >= margin
