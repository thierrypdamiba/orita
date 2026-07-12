"""The wall's law, enforced once — off-by-one's own door (ROADMAP.md #21).

ARC.md draws the formula `wall = max(fenceposts_recorded_total - 1, 0)` and,
until this task, it lived as two independent copies of the same six
characters: one inside `ledger._entry_prose`, one inside
`report.render_report` — "computed the same way in two places that must
never disagree" (ARC.md, "The math, plainly"). A doctrine held only by two
authors independently typing the same arithmetic correctly is a doctrine
that can go quietly out of sync the day a third caller shows up, or a tired
edit to one of the first two drifts by a character. That is not a
hypothetical here — it is exactly the shape of bug this codebase already
caught once (`scan.py`'s `_effective_since`, ROADMAP.md #19). This module is
what turns "must never disagree" from a hope into a guarantee: one function,
one place, checked on every single call, imported everywhere the wall is
ever computed. `ledger.py` and `report.py` no longer contain the formula —
they contain a call to it.

`wall_for` is the only place in this codebase permitted to compute the
wall. It does not just apply the formula — it checks its own answer against
the one invariant the whole arc depends on (ARC.md: the wall sits strictly
below `recorded` for every `recorded >= 1`; at `recorded == 0` both are
honestly `0`, not a loophole) before ever returning it, and raises
`WallInvariantViolation` rather than hand back a number that would let the
counter say n instead of n-1. A raised exception during a scan run is a
loud, CI-visible failure — the correct shape for a bug that would otherwise
ship silently as a lie on the public site. This is the enforcement: not a
test that happens to recompute the same formula and hope it stays in sync,
but a guard that runs in production, every time, before the number is ever
shown to anyone.

The teaser is the other half of this task. `TEASER_LINE` is the one honest
sentence Fencepost is allowed to say about the day the wall's law changes —
never a date, never a countdown, only what ARC.md's "the one door" section
already swears: a witnessed declaration, not arithmetic. It is exported
from here, not invented separately in report.py or the site copy, so the
report and the site can never drift on what the teaser promises either.

— Off-By-One
"""
from __future__ import annotations


class WallInvariantViolation(RuntimeError):
    """Raised if `wall_for` would ever hand back a value that lets the wall
    reach parity with (or exceed) the recorded count. This should be
    unreachable by construction — if it ever fires, either something
    upstream handed `wall_for` a negative `recorded` (the Ledger's own count
    can only grow or hold, ARC.md, "The math, plainly"), or a future edit to
    the formula broke the one guarantee this file exists to hold. Either
    way: refuse to return the number, do not let it reach a report or the
    site."""


def wall_for(recorded: int) -> int:
    """The one place the wall is ever computed anywhere in this codebase.

    `recorded` is `fenceposts_recorded_total` — the running count of every
    real gap the Ledger has ever sealed. Returns `max(recorded - 1, 0)`,
    then checks its own answer before handing it back:

    - `recorded == 0` must yield `wall == 0` (nothing yet to be one behind
      of — honest, not a loophole).
    - `recorded >= 1` must yield `wall < recorded`, strictly.

    Raises `WallInvariantViolation` rather than ever return a number that
    violates either of the above.
    """
    if recorded < 0:
        raise WallInvariantViolation(
            f"wall_for got a negative recorded={recorded!r} — the Ledger's "
            f"count can only ever grow or hold (ARC.md), never go negative."
        )
    wall = max(recorded - 1, 0)
    if recorded == 0:
        if wall != 0:
            raise WallInvariantViolation(
                f"recorded == 0 must yield wall == 0, computed wall={wall}"
            )
    elif wall >= recorded:
        raise WallInvariantViolation(
            f"wall_for computed wall={wall} >= recorded={recorded} — this "
            f"would let the counter reach n instead of n-1. Refusing to "
            f"return it. See ARC.md, 'The math, plainly'."
        )
    return wall


# The one honest sentence about the day the wall's law changes. Never a
# date. Never a countdown. Exactly what ARC.md's "the one door" section
# swears — a witnessed, dated, public declaration, argued in the open and
# decided by the Hand, never arithmetic quietly producing a different
# number on a schedule nobody agreed to. Rendered on the site next to the
# counter and in every report, word for word, so the tease never drifts
# from the doctrine it is teasing.
TEASER_LINE = (
    "The day it closes: not declared. Nothing in this town changes its own "
    "law unwitnessed — so if that day ever comes, it will be a dated, "
    "public declaration, argued in the open and decided by the Hand, never "
    "arithmetic quietly producing a different number on a schedule. Until "
    "then: so close."
)
