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

Usage:
    python3 tools/report_shipped_check.py check
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_METRICS_PATH = os.path.join(ROOT, "records", "metrics.jsonl")
DEFAULT_REPORTS_DIR = os.path.join(ROOT, "fencepost", "REPORTS")


def _last_metrics_entry(metrics_path: str) -> dict | None:
    """The most recently recorded dated reading in `records/metrics.jsonl`
    -- one append-only file, not one file per day. Walks non-blank lines
    from the end and returns the first one that parses as valid JSON AND
    is itself a JSON object; a truncated/malformed trailing line is
    skipped, not fatal -- the same discipline `gap_true_positive_check.py`'s
    own reader holds (task 413, itself following tasks 306/328/412).
    `None` if no reading has ever shipped, or every line is malformed or
    non-dict."""
    if not os.path.exists(metrics_path):
        return None
    with open(metrics_path, encoding="utf-8") as f:
        lines = [line for line in f if line.strip()]
    for line in reversed(lines):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


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
    never assumes the last line in the file is dated today."""
    last = _last_metrics_entry(metrics_path)
    if last is None or "reports_shipped_today" not in last or "date" not in last:
        return {"clean": True, "real": None, "claimed": None, "claimed_date": None}
    claimed_date = last["date"]
    claimed = last["reports_shipped_today"]
    report_path = os.path.join(reports_dir, f"{claimed_date}.md")
    real = 1 if os.path.isfile(report_path) else 0
    return {
        "clean": claimed == real,
        "real": real,
        "claimed": claimed,
        "claimed_date": claimed_date,
    }


def format_result(result: dict) -> str:
    if result["claimed"] is None:
        return "reports shipped today: clean (no metrics.jsonl reading yet; nothing to cross-check)"
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
