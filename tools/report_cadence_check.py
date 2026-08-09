#!/usr/bin/env python3
"""Task 116. Off-By-One counts the one row nobody had counted yet.

STRATEGY.md's metrics table names five leading signals and one lagging
one. Two of the five leading rows are already instrumented: Ogun's
`AUDIT.md` true-positive tally (`seam_engine/audit.py`, folded into the
Wall) and the Wall's own live n-1 counter. The FIRST row in that table
has my own name on it: "Daily Fencepost Report shipped (town dogfood) |
leading | 1/day, 30 of 30 days | off-by-one." Nothing has ever computed
it. `check_report_freshness` (task 61) answers a narrower question --
does TODAY's or YESTERDAY's tablet exist, current/pending/stale -- never
the actual running streak the target names.

`fencepost/REPORTS/` holds real dated tablets: 2026-07-12, 13, 15, 16,
17. 2026-07-14 is missing. That is not a mystery I had to go dig for --
BUILDLOG.md's own 2026-07-14 13:14 and 14:10 ritual notes already
recorded `seam-scan.yml`'s 12:00 UTC run failing that day on a rate
limit, fixed the next day by task 63. The gap is real, already
explained, and has sat completely uncounted since -- the exact shape of
gap this town's own product exists to catch, sitting in its own
dogfood cadence.

This module closes exactly that: a read-only, local-filesystem-only
scan (no network, mirrors `petition_cadence_check.py`'s own boundary --
my own prior tool, same office) of every `YYYY-MM-DD.md` file directly
inside `fencepost/REPORTS/`, computing the real total shipped, the
current trailing streak (walking backward from the most recent tablet,
stopping at the first missing calendar day), and every missing date in
the recorded history -- not a violation scanner flipping a law, a
metric renderer proving what STRATEGY.md's own row claims.

Usage:
    python3 tools/report_cadence_check.py check
"""
from __future__ import annotations

import os
import sys
from datetime import date
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import date_cadence  # noqa: E402
import text_patterns  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REPORTS_DIR = os.path.join(ROOT, "fencepost", "REPORTS")
TARGET_STREAK_DAYS = 30  # STRATEGY.md: "1/day, 30 of 30 days"

_DATE_NAME = text_patterns.DATE_NAME_MD


def _shipped_dates(reports_dir: str) -> list[date]:
    """Every real calendar date with a validly-named `YYYY-MM-DD.md`
    tablet directly inside `reports_dir`, sorted ascending. A name that
    doesn't match the pattern (README.md, a stray suffix, a malformed
    date) is silently skipped -- the same "ignore what doesn't conform,
    never crash the scan over it" discipline `petition_cadence_check.py`
    already holds for a malformed filename, applied here to a name that
    was never a claim about a UTC day at all."""
    if not os.path.isdir(reports_dir):
        return []
    dates = []
    for name in sorted(os.listdir(reports_dir)):
        full = os.path.join(reports_dir, name)
        if not os.path.isfile(full):
            continue
        m = _DATE_NAME.match(name)
        if not m:
            continue
        year, month, day = (int(g) for g in m.groups())
        try:
            dates.append(date(year, month, day))
        except ValueError:
            continue
    return sorted(set(dates))


def compute_cadence(reports_dir: str | None = None, target: int = TARGET_STREAK_DAYS) -> dict[str, Any]:
    """The real numbers behind STRATEGY.md's "1/day, 30 of 30 days" row.

    - total_shipped: count of validly-named dated tablets found.
    - first_date / most_recent_date: the earliest and latest shipped date,
      or None if nothing has shipped yet.
    - current_streak: consecutive calendar days ending at most_recent_date,
      walking backward day by day, stopping at the first day with no
      tablet. 0 if nothing has shipped.
    - missing_dates: every calendar date strictly between first_date and
      most_recent_date that has no tablet -- the real, historical gaps,
      named not hidden. Never includes today or any date after
      most_recent_date; a cron window that simply hasn't fired yet is
      `check_report_freshness`'s job (pending, not a gap).
    """
    reports_dir = reports_dir or DEFAULT_REPORTS_DIR
    dates = _shipped_dates(reports_dir)
    return date_cadence.compute_date_streak_and_gaps(dates, target)


def format_cadence(result: dict[str, Any]) -> str:
    if result["total_shipped"] == 0:
        return "report cadence: no Fencepost Report has ever shipped -- nothing to count yet"
    lines = [
        f"report cadence: {result['current_streak']}-day streak "
        f"(target {result['target']}/{result['target']}, STRATEGY.md's off-by-one metric) -- "
        f"{result['total_shipped']} shipped total, most recent {result['most_recent_date']}"
    ]
    if result["missing_dates"]:
        joined = ", ".join(result["missing_dates"])
        lines.append(f"  {len(result['missing_dates'])} historical gap day(s), already on record: {joined}")
    else:
        lines.append("  no gap day between first and most recent shipped tablet")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    out = compute_cadence()
    print(format_cadence(out))
    sys.exit(0)
