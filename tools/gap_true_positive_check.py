#!/usr/bin/env python3
"""Task 413. Ògún's own metric never checks itself.

Tasks 145 and 412 each found the identical shape on a sibling
`records/metrics.jsonl` field: a real, honestly-recorded number with
nothing in code ever cross-checking it against ground truth going
forward. Task 145 built `toolkits_in_use_check.py` for `distinct_toolkits_in_use`;
task 412 built `connected_users_check.py` for `connected_users_oauth`.
Both docstrings, read closely, name the field they fixed and stop there --
neither ever mentions `gap_true_positive_rate`, and a repo-wide grep for
that field name (before this task) returns exactly zero hits outside
`records/metrics.jsonl` itself: it is written every day, read back by
nothing.

This is STRATEGY.md's own highest-stakes leading metric -- "Gap
true-positive rate (self-audited) | leading | >=90% | ogun" -- and Ògún's
own dissent names exactly why: "surface one junk gap in public and the
daily report becomes noise and the read-trust evaporates." Task 410/161's
`strategy_audit_target.py` already cross-checks STRATEGY.md's stated
">=90%" TARGET against the live `audit.audit_ledger()` tally, but that is
a different comparison -- a document's promise against reality. It never
once reads the actual `gap_true_positive_rate` number a god hand-recorded
into `records/metrics.jsonl` each day and asks whether THAT number still
agrees with the same live ledger. Every recorded value to date happens to
be `1.0`, honestly, but "honest so far" is a claim about the past, the
same gap task 145 closed for a flattering `2` that sat unnoticed for six
days -- nothing stops a future hand-copy of yesterday's `1.0` forward
after a real false-positive lands in `fencepost/AUDIT.md` and drops the
live rate.

Built to the identical shape `connected_users_check.py` (task 412) already
proved: read the real ground truth off the live source
(`seam_engine.audit.audit_ledger()`, never a second hand-typed guess),
read the last recorded `gap_true_positive_rate` off `records/metrics.jsonl`,
compare. Ground truth here is a `float | None` (a rate, not a count), so
comparison rounds both sides to 4 decimal places -- `strategy_audit_target.py`'s
own precision -- rather than a bare `==` that would false-flag an honestly
rounded hand-typed reading against a live rate carrying more binary float
noise (e.g. 16/17 truncated).

Usage:
    python3 tools/gap_true_positive_check.py check
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_METRICS_PATH = os.path.join(ROOT, "records", "metrics.jsonl")
DEFAULT_LEDGER_BASE = os.path.join(ROOT, "fencepost")

_SEAM_ENGINE_SRC = os.path.join(ROOT, "fencepost", "seam_engine", "src")
if _SEAM_ENGINE_SRC not in sys.path:
    sys.path.insert(0, _SEAM_ENGINE_SRC)
from seam_engine import audit  # noqa: E402

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)
import metrics_reader  # noqa: E402

# Task 508: consolidated into tools/metrics_reader.py -- six sibling
# checks each carried a byte-identical copy of this reader, invisible to
# duplicate_regex_check.py (which only scans `re.compile()` call sites).
# tests/test_metrics_reader.py asserts this name IS that shared function.
_last_metrics_entry = metrics_reader.last_metrics_entry


def check_gap_true_positive_rate(
    metrics_path: str = DEFAULT_METRICS_PATH,
    ledger_base: str | Path = DEFAULT_LEDGER_BASE,
) -> dict:
    """Cross-check the last recorded `gap_true_positive_rate` reading
    against the real, live `seam_engine.audit.audit_ledger()` tally.
    Returns `clean: True` when the two agree (rounded to 4 decimal
    places) or when there is nothing yet to contradict; otherwise
    `clean: False` naming the exact claimed vs. real numbers, never a
    bare pass/fail.

    Two distinct "nothing recorded" shapes, both clean, mirroring
    `connected_users_check.py`'s own no-reading-yet branch:
    - no metrics.jsonl reading has ever existed at all, or
    - the ledger itself has audited zero gaps (real rate is `None`) AND
      the last reading also names no rate (`null`/absent) -- an honest
      pair of unknowns, not a mismatch.

    A reading that DOES exist but names no rate (`null`/absent) while the
    live Ledger already has a real rate to report is not covered by
    either clean shape above -- it is the same "claims a number ground
    truth cannot back" failure in the other direction: a real rate exists
    and this reading fails to carry it. Flagged `clean: False` exactly
    like a recorded number that disagrees with reality.

    A recorded number against a `None` live rate (claiming a rate that
    cannot exist because nothing has been audited yet) is a real
    mismatch, not a free pass -- the same "claims a number ground truth
    cannot back" failure this whole sibling class of checks exists to
    catch."""
    real = audit.audit_ledger(Path(ledger_base)).rate
    last = _last_metrics_entry(metrics_path)

    if last is None:
        return {"clean": True, "real": real, "claimed": None, "claimed_date": None}

    claimed = last.get("gap_true_positive_rate")

    if claimed is None:
        return {
            "clean": real is None,
            "real": real,
            "claimed": None,
            "claimed_date": last.get("date"),
        }
    if real is None:
        return {
            "clean": False,
            "real": None,
            "claimed": claimed,
            "claimed_date": last.get("date"),
        }
    clean = round(real, 4) == round(claimed, 4)
    return {
        "clean": clean,
        "real": real,
        "claimed": claimed,
        "claimed_date": last.get("date"),
    }


def format_result(result: dict) -> str:
    if result["claimed"] is None:
        if result["clean"]:
            real = "none audited yet" if result["real"] is None else f"{round(result['real'] * 100, 4)}%"
            return f"gap true-positive rate: clean (no metrics.jsonl reading yet; real ground truth is {real})"
        return (
            f"gap true-positive rate: BROKEN -- metrics.jsonl's {result['claimed_date']} reading names "
            f"no rate (null/absent), but the real Ledger already has one to report "
            f"({round(result['real'] * 100, 4)}%) -- a real rate exists and was not recorded, escalate now"
        )
    if result["real"] is None:
        return (
            f"gap true-positive rate: BROKEN -- metrics.jsonl's {result['claimed_date']} reading claims "
            f"{result['claimed']}, but the real Ledger has audited zero gaps -- no rate exists to claim, "
            "escalate now"
        )
    if result["clean"]:
        return (
            f"gap true-positive rate: clean ({round(result['real'] * 100, 4)}% real, "
            f"metrics.jsonl's {result['claimed_date']} reading agrees)"
        )
    return (
        f"gap true-positive rate: BROKEN -- metrics.jsonl's {result['claimed_date']} reading claims "
        f"{round(result['claimed'] * 100, 4)}%, real ground truth (seam_engine.audit.audit_ledger(), "
        f"gate-verified) is {round(result['real'] * 100, 4)}% -- STRATEGY.md's own Ogun's-law metric is "
        "misreporting live"
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = check_gap_true_positive_rate()
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
