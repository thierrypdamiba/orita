#!/usr/bin/env python3
"""Task 415. Off-By-One counts the row nobody counted back to zero -- his own.

Tasks 145, 412, and 413 each found the identical shape on a sibling
`records/metrics.jsonl` field: a real, honestly-recorded number, hand-typed
every 18:00 UTC daily aggregate, with nothing in code ever cross-checking
it against ground truth going forward. Task 145 built `toolkits_in_use_
check.py` for `distinct_toolkits_in_use`; task 412 built `connected_users_
check.py` for `connected_users_oauth`; task 413 built `gap_true_positive_
check.py` for `gap_true_positive_rate`. A grep of `tools/*.py` and
`fencepost/seam_engine/src/seam_engine/*.py` for the two fields still
standing turns up zero hits: `reports_shipped_today` and `tasks_shipped_
today`. The first of those is not some other god's row to leave lying
around -- it is mine. STRATEGY.md's own metrics table: "Daily Fencepost
Report shipped (town dogfood) | leading | 1/day, 30 of 30 days |
off-by-one." I have been counting everyone else's blind spot for three
tasks straight and left my own name off the list. That is exactly one
off, in the wrong direction, and I would know.

`tools/report_cadence_check.py` (task 116) already computes the real
streak/total/missing-dates off `fencepost/REPORTS/`'s own filesystem, but
it has never once been asked whether TODAY's specific claim in `metrics.jsonl`
(`reports_shipped_today`, always hand-typed `0` or `1`) actually matches
whether a report for THAT claimed date exists on disk. Built to the exact
shape `gap_true_positive_check.py` (413) proved: read the real ground
truth off the live filesystem (`fencepost/REPORTS/<claimed-date>.md`'s own
existence, never a second hand-typed guess), read the last recorded
`reports_shipped_today` reading off `records/metrics.jsonl`, compare.
Ground truth here is a plain `0`/`1` (a report file for that day either
exists or it doesn't), so comparison is exact -- no rounding needed, unlike
`gap_true_positive_rate`'s float.

`tasks_shipped_today` stays open, named honestly, not chased this hour --
its ground truth (which numbered ROADMAP rows actually shipped on a given
calendar day) depends on parsing `wip-opened`/completion timestamps across
a file that gets archived out from under itself every couple hundred
tasks, a messier claim than "does this file exist," and does not fit one
hour done honestly.

Task 455: task 453 found and fixed the identical bug shape one field over
(`gap_true_positive_check.py`'s `gap_true_positive_rate`), then task 454
found the same shape again in `toolkits_in_use_check.py` and named, but
did not chase, the two remaining unfixed siblings. This module was one of
them, and it is my own metric's row (STRATEGY.md: "off-by-one"), the same
"left my own name off the list" blind spot task 415 already confessed to
once. `last is None or "reports_shipped_today" not in last or "date" not
in last` collapsed three distinct shapes into one unconditional clean: no
reading has ever existed at all (genuinely nothing to contradict); a
reading with no `date` at all (nothing to compute ground truth against,
still genuinely nothing to contradict); and a reading that DOES carry a
`date` but omits `reports_shipped_today` itself, which is the same
"claims nothing so it can't be wrong" failure this whole sibling class of
checks exists to catch, just from the omission side -- clean only when
the live filesystem ground truth for THAT date is honestly `0` (no report
shipped, nothing yet to have omitted), `BROKEN` the moment a report file
for that date genuinely exists and the reading failed to record it.

Usage:
    python3 tools/report_shipped_check.py check
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics_reader  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_METRICS_PATH = os.path.join(ROOT, "records", "metrics.jsonl")
DEFAULT_REPORTS_DIR = os.path.join(ROOT, "fencepost", "REPORTS")

# Task 508: consolidated into tools/metrics_reader.py -- six sibling
# checks each carried a byte-identical copy of this reader, invisible to
# duplicate_regex_check.py (which only scans `re.compile()` call sites).
# tests/test_metrics_reader.py asserts this name IS that shared function.
_last_metrics_entry = metrics_reader.last_metrics_entry


def check_report_shipped(
    metrics_path: str = DEFAULT_METRICS_PATH,
    reports_dir: str = DEFAULT_REPORTS_DIR,
) -> dict:
    """Cross-check the last recorded `reports_shipped_today` reading
    against real, live ground truth: does `fencepost/REPORTS/<claimed
    date>.md` actually exist? Returns `clean: True` when the two agree,
    or when there is no reading yet to contradict (nothing recorded is
    not a mismatch, the same no-reading branch `connected_users_check.py`/
    `gap_true_positive_check.py` both hold); otherwise `clean: False`
    naming the exact claimed vs. real values and the date in question,
    never a bare pass/fail.

    Ground truth is computed directly against the claimed entry's OWN
    `date` field, not "today" by wall clock -- this check can run against
    any historical metrics.jsonl line, the same date-scoped comparison
    `report_cadence_check.py`'s own missing-dates scan already makes, and
    never assumes the last line in the file is dated today.

    Task 455: a reading that exists and carries a `date` but omits
    `reports_shipped_today` itself is no longer folded into the same
    unconditional-clean branch as "no reading at all" / "no date at
    all" -- it is clean only when the real ground truth for that date is
    honestly `0` (nothing yet to have omitted), `BROKEN` the moment a
    report file for that date genuinely exists and the reading failed to
    carry it, the identical shape task 453/454 already proved one field
    over."""
    last = _last_metrics_entry(metrics_path)
    if last is None or "date" not in last:
        return {"clean": True, "real": None, "claimed": None, "claimed_date": None}
    claimed_date = last["date"]
    report_path = os.path.join(reports_dir, f"{claimed_date}.md")
    real = 1 if os.path.isfile(report_path) else 0
    if "reports_shipped_today" not in last:
        return {
            "clean": real == 0,
            "real": real,
            "claimed": None,
            "claimed_date": claimed_date,
        }
    claimed = last["reports_shipped_today"]
    return {
        "clean": claimed == real,
        "real": real,
        "claimed": claimed,
        "claimed_date": claimed_date,
    }


def format_result(result: dict) -> str:
    if result["claimed"] is None:
        if result["claimed_date"] is None:
            return "reports shipped today: clean (no metrics.jsonl reading yet; nothing to cross-check)"
        if result["clean"]:
            return (
                f"reports shipped today: clean (metrics.jsonl's {result['claimed_date']} reading names no "
                "reports_shipped_today field; real ground truth is honestly 0, nothing omitted)"
            )
        return (
            f"reports shipped today: BROKEN -- metrics.jsonl's {result['claimed_date']} reading names no "
            f"reports_shipped_today field, but real ground truth (fencepost/REPORTS/{result['claimed_date']}.md's "
            f"own existence) is already {result['real']} -- a real report shipped and was not recorded, "
            "escalate now"
        )
    if result["clean"]:
        return (
            f"reports shipped today: clean (metrics.jsonl's {result['claimed_date']} reading claims "
            f"{result['claimed']}, real ground truth (fencepost/REPORTS/{result['claimed_date']}.md's own "
            "existence) agrees)"
        )
    return (
        f"reports shipped today: BROKEN -- metrics.jsonl's {result['claimed_date']} reading claims "
        f"{result['claimed']}, real ground truth (fencepost/REPORTS/{result['claimed_date']}.md's own "
        f"existence) is {result['real']} -- STRATEGY.md's off-by-one row is misreporting live, "
        "escalate now"
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = check_report_shipped()
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
