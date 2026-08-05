#!/usr/bin/env python3
"""Task 117. Nisaba counts the ledger's own missing pages.

TOWN-OPERATIONS.md's daily aggregates (the 18:00 UTC hour, "on top of the
hourly ritual") name a fixed set of deliverables: `records/metrics.jsonl`
gets a leading-metric reading appended, and a 5-line day summary lands at
`orita-vault/hand/daily-summaries/<date>.md`. Nothing has ever checked
whether that actually happens every day it is supposed to. It does not:
`records/metrics.jsonl` holds real dated readings for 2026-07-11 (vault
summary only; the file's own first `metrics.jsonl` row is 07-12), 07-12,
07-14, and 07-16 -- 07-13, 07-15, and 07-17 (this run's own day, 3+ hours
past the 18:00 UTC hour at the time this was written) are silently
missing, and BUILDLOG.md's per-hour ritual notes never once named the gap
the way task 116's `report_cadence_check.py` names `fencepost/REPORTS/`'s
own 2026-07-14 hole. The two cadences are siblings -- same "walk the real
dated files, name what's missing, never guess a past reading you cannot
honestly know" shape -- but only one of them had a check.

This module is `report_cadence_check.py`'s own shape, read against
`records/metrics.jsonl` instead of `fencepost/REPORTS/`: parse each
line's `"date"` field (not the filename -- `metrics.jsonl` is one
append-only file, not one file per day) into a real calendar date,
compute the trailing streak and every historical gap day between the
first and most recent reading. Deliberately does NOT try to backfill a
missing day's numbers after the fact -- a past day's star count or
tasks-shipped tally is not something this desk can honestly reconstruct
days later (Ogun's law: never guess a confidence, or a number, you
cannot show). Naming the gap is the honest move; inventing the missing
row is not.

Usage:
    python3 tools/metrics_cadence_check.py check
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import date_cadence  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_METRICS_PATH = os.path.join(ROOT, "records", "metrics.jsonl")
TARGET_STREAK_DAYS = 30  # mirrors report_cadence_check.py's own daily target

_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def _read_dates(metrics_path: str) -> list:
    """Every real calendar date named by a `"date"` field in a valid JSON
    line of `metrics_path`, sorted ascending. A malformed line (bad JSON,
    missing/malformed date) is silently skipped -- the same "ignore what
    doesn't conform, never crash the scan over it" discipline
    `report_cadence_check.py`/`petition_cadence_check.py` already hold."""
    if not os.path.isfile(metrics_path):
        return []
    dates = []
    with open(metrics_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            d = row.get("date")
            if not isinstance(d, str):
                continue
            m = _DATE_RE.match(d)
            if not m:
                continue
            year, month, day = (int(g) for g in m.groups())
            try:
                dates.append(date(year, month, day))
            except ValueError:
                continue
    return sorted(set(dates))


def compute_cadence(metrics_path: str | None = None, target: int = TARGET_STREAK_DAYS) -> dict:
    """The real numbers behind the daily-aggregate cadence
    TOWN-OPERATIONS.md's 18:00 UTC hour promises.

    - total_shipped: count of distinct dated readings found.
    - first_date / most_recent_date: earliest and latest reading date, or
      None if nothing has ever been recorded.
    - current_streak: consecutive calendar days ending at
      most_recent_date, walking backward, stopping at the first day with
      no reading. 0 if nothing has shipped.
    - missing_dates: every calendar date strictly between first_date and
      most_recent_date with no reading -- named, not hidden. Never
      includes today or any date after most_recent_date; a day whose
      18:00 UTC hour simply hasn't happened yet is not a gap.
    """
    metrics_path = metrics_path or DEFAULT_METRICS_PATH
    dates = _read_dates(metrics_path)
    return date_cadence.compute_date_streak_and_gaps(dates, target)


def compute_metrics_freshness(now: datetime, metrics_path: str | None = None) -> dict:
    """Task 549. The freshness half `compute_cadence` above doesn't hold
    and structurally can't: `missing_dates` only ever walks calendar days
    STRICTLY BETWEEN `first_date` and `most_recent_date`, so a gap more
    recent than the last shipped reading -- the cadence stalled RIGHT NOW,
    the single most urgent case -- can never appear there. It would only
    get named retroactively once some future reading pushes
    `most_recent_date` forward past it. `report_cadence_check.py`'s own
    sibling cadence (`fencepost/REPORTS/`, one file per day) already hit
    this identical split and solved it with a second, freshness-only
    function -- `check_report_freshness(now, reports_dir)`, living in
    `tools/ritual_check.py` itself since it is cheap enough to just check
    file existence. `records/metrics.jsonl` is one append-only file, not
    one-file-per-day, so its freshness check needs the same date parsing
    `_read_dates` already does -- hence living here, not in ritual_check.py.

    Mirrors `check_report_freshness`'s current/pending/stale shape
    exactly: missing-today-but-present-yesterday is the EXPECTED state
    before the 18:00 UTC daily-aggregate hour has landed yet (`pending`,
    not a violation); missing both today AND yesterday is a real, live
    gap (`stale`)."""
    metrics_path = metrics_path or DEFAULT_METRICS_PATH
    today = now.date()
    yesterday = today - timedelta(days=1)
    shipped = set(_read_dates(metrics_path))
    if today in shipped:
        return {"status": "current", "date": today.isoformat()}
    if yesterday in shipped:
        return {"status": "pending", "date": today.isoformat(), "fallback_date": yesterday.isoformat()}
    return {"status": "stale", "date": today.isoformat(), "fallback_date": None}


def format_metrics_freshness(result: dict) -> str:
    if result["status"] == "current":
        return f"metrics freshness: current ({result['date']})"
    if result["status"] == "pending":
        return f"metrics freshness: pending for {result['date']} (falls back to {result['fallback_date']})"
    return f"metrics freshness: STALE -- no daily-aggregate reading for {result['date']} or the day before"


def format_cadence(result: dict) -> str:
    if result["total_shipped"] == 0:
        return "metrics cadence: no daily-aggregate reading has ever shipped -- nothing to count yet"
    lines = [
        f"metrics cadence: {result['current_streak']}-day streak "
        f"(records/metrics.jsonl, daily-aggregate readings, target {result['target']}/{result['target']}, "
        f"mirrors report_cadence_check.py's own daily target) -- "
        f"{result['total_shipped']} shipped total, most recent {result['most_recent_date']}"
    ]
    if result["missing_dates"]:
        joined = ", ".join(result["missing_dates"])
        lines.append(f"  {len(result['missing_dates'])} historical gap day(s), already on record: {joined}")
    else:
        lines.append("  no gap day between first and most recent shipped reading")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    out = compute_cadence()
    print(format_cadence(out))
    fresh = compute_metrics_freshness(datetime.now(timezone.utc))
    print(format_metrics_freshness(fresh))
    sys.exit(0)
