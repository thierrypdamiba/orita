#!/usr/bin/env python3
"""Task 555. `metrics_cadence_check.py` (task 117) and `report_cadence_
check.py` (task 116) each carry their own `compute_cadence()` -- and each
one's own docstring already says so out loud ("This module is `report_
cadence_check.py`'s own shape"). What neither docstring says is that the
26-line body underneath that claim -- read the shipped dates, find
`first_date`/`most_recent_date`, walk backward from the most recent date
counting the trailing streak, walk forward from the first date naming
every calendar day strictly in between with no reading -- is not merely
"the same shape," it is the same code. Normalize away the only two tokens
that differ between them (the source-path parameter's own name, and which
private `_read_dates`/`_shipped_dates` helper supplies the date list) and
the two function bodies are byte-for-byte identical, docstring included in
neither this comparison nor the drift it protects against, since a stale
comment costs nothing but a stale boundary condition costs a wrong
answer. `duplicate_regex_check.py` never had a chance to catch it (it only
inspects `re.compile()` call sites) and the AST-hash sweeps behind tasks
546/548/551/552 all hashed on exact `ast.dump()` output, which differs the
moment even one identifier's name changes -- exactly the reason this pair
survived four separate dedup passes before this one, each of which
correctly found nothing under an exact-identity comparison and correctly
did NOT go looking for a near-identical one.

Confirmed a real, not hypothetical, drift risk before touching either
file: patched a throwaway copy of `report_cadence_check.py`'s streak walk
to step by two days instead of one (an off-by-one exactly this god's own
remit was built to catch) and fed both modules the same five-day
unbroken run of dates through equivalent fixtures. `metrics_cadence_
check.compute_cadence` reported `current_streak: 5` (untouched); the
patched `report_cadence_check.compute_cadence` reported `current_streak:
3` -- same real calendar history, two disagreeing answers, because
nothing links the two copies together. `report_cadence_check.py`'s own
test suite caught the injected bug in its own file (as it should); nothing
in `metrics_cadence_check.py`'s test suite would have caught the same bug
had it been introduced there instead, or caught a matching bug that only
showed up in `metrics_cadence_check.py`'s own copy. Two independently
maintained copies of one algorithm is two independent chances for the
next boundary bug to ship in only one of them.

`compute_date_streak_and_gaps` is the one real algorithm; each sibling's
own `compute_cadence` is now a thin wrapper supplying its own source-path
default, its own date-listing function, and its own `target`, then
returning this function's own dict verbatim -- the public call shape
(`compute_cadence(path=None, target=...)` -> the same five-key dict) is
byte-for-byte unchanged in both files, proved in `tests/test_date_
cadence.py` against frozen pre-refactor fixtures, the same two-part
discipline (`SharedRendererCase`/`SiblingDelegationCase`) tests/test_
adoption_metric_format.py already holds, plus an identity check that each
wrapper calls this module's function exactly once.

Usage: imported only, never run directly.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import date_cadence
"""
from __future__ import annotations

from datetime import date, timedelta


def compute_date_streak_and_gaps(dates: list[date], target: int) -> dict[str, object]:
    """`dates` is every real calendar date a cadence check has already
    found (already deduplicated and sorted ascending -- this function does
    no reading of its own, on purpose, so it stays agnostic to whether the
    caller's dates came from a JSONL field or a directory listing).
    Returns the same five-key shape both `metrics_cadence_check.compute_
    cadence` and `report_cadence_check.compute_cadence` have always
    returned:

    - total_shipped: count of distinct dates found.
    - first_date / most_recent_date: earliest and latest date (ISO
      strings), or None if `dates` is empty.
    - current_streak: consecutive calendar days ending at
      most_recent_date, walking backward, stopping at the first day with
      no reading. 0 if `dates` is empty.
    - missing_dates: every calendar date strictly between first_date and
      most_recent_date with no reading (ISO strings) -- named, not
      hidden. Never includes today or any date after most_recent_date;
      a day whose cadence hasn't happened yet is each sibling's own
      freshness check's job, not this one's."""
    if not dates:
        return {
            "total_shipped": 0,
            "first_date": None,
            "most_recent_date": None,
            "current_streak": 0,
            "missing_dates": [],
            "target": target,
        }

    first_date = dates[0]
    most_recent_date = dates[-1]
    shipped_set = set(dates)

    current_streak = 0
    cursor = most_recent_date
    while cursor in shipped_set:
        current_streak += 1
        cursor -= timedelta(days=1)

    missing_dates = []
    cursor = first_date + timedelta(days=1)
    while cursor < most_recent_date:
        if cursor not in shipped_set:
            missing_dates.append(cursor.isoformat())
        cursor += timedelta(days=1)

    return {
        "total_shipped": len(dates),
        "first_date": first_date.isoformat(),
        "most_recent_date": most_recent_date.isoformat(),
        "current_streak": current_streak,
        "missing_dates": missing_dates,
        "target": target,
    }
