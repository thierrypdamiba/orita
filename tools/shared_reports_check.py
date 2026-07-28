#!/usr/bin/env python3
"""Task 120. Kwaku-Ananse counts the row that was never anyone's to count.

STRATEGY.md's metrics table names six rows. Five of them now have a running
number behind them: `AUDIT.md`'s true-positive tally (Ogun), the Wall's live
n-1 counter (Kothar-wa-khasis), `records/metrics.jsonl`'s own
`connected_users_oauth`/`distinct_toolkits_in_use` fields (both real, both
honestly 0/2 since founding), and `report_cadence_check.py`'s shipped-report
streak (task 116, off-by-one). The sixth is mine by name: "Shared Fencepost
Reports in the wild | lagging | 50 organic links/screenshots |
kwaku-ananse." Grepped `tools/*.py` and `records/*.jsonl` for anything that
tracks it: zero hits. Not a mystery -- the town has zero stars and no
outside audience yet, so the honest count is zero -- but zero uncounted is
a different thing from zero recorded, and this row is the one metric this
desk could fabricate most easily (a screenshot is unfalsifiable from inside
the repo) and must not: Ogun's law is never guess a number you cannot show.

This module gives the row a real, append-only home instead of a guess:
`records/shared-in-the-wild.jsonl`, one line per REAL organic share a god
or the Hand actually finds (a link to a real tweet quoting a report, a
real screenshot posted somewhere the town does not control) -- never
manufactured, never backfilled after the fact. Mirrors
`metrics_cadence_check.py`'s exact JSONL-scanning shape (task 117, Nisaba's
own tool), except this is a cumulative lagging count against a fixed
target (50), not a daily streak -- there is no calendar cadence to a
mortal deciding to screenshot something.

Usage:
    python3 tools/shared_reports_check.py check
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SHARED_PATH = os.path.join(ROOT, "records", "shared-in-the-wild.jsonl")
TARGET_SHARES = 50  # STRATEGY.md: "50 organic links/screenshots"


def _parse_date(d: str) -> date:
    """Parse a `"date"` field into a real `date` object. Raises ValueError/
    TypeError on anything that isn't a real calendar date -- callers decide
    whether to skip or propagate. Deliberately tolerant of non-zero-padded
    input (`"2026-7-9"` parses the same as `"2026-07-09"`, both are July 9)
    -- `int()` doesn't care about padding, and neither should validation."""
    year, month, day = (int(x) for x in d.split("-"))
    return date(year, month, day)


def _read_entries(shared_path: str) -> list:
    """Every real, validly-shaped entry in `shared_path`: requires a
    `"date"` field parseable as a real calendar date and a non-empty
    `"url"` field naming where the share actually lives. A malformed line
    (bad JSON, valid JSON that isn't an object, missing/malformed date,
    missing/blank url) is silently skipped -- the same "ignore what doesn't
    conform, never crash the scan over it, never count it either"
    discipline `metrics_cadence_check.py`/`report_cadence_check.py` already
    hold, and the same valid-JSON-non-dict guard tasks 329-353 closed
    across every `oracle_engine/*_cadence.py` sibling. No de-duplication
    beyond exact-line identity: two real, distinct mortals sharing the same
    URL is two real shares, not one."""
    if not os.path.isfile(shared_path):
        return []
    entries = []
    with open(shared_path, encoding="utf-8") as f:
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
            url = row.get("url")
            if not isinstance(d, str) or not isinstance(url, str) or not url.strip():
                continue
            try:
                _parse_date(d)
            except (ValueError, TypeError):
                continue
            entries.append(row)
    return entries


def compute_shared_reports(shared_path: str | None = None, target: int = TARGET_SHARES) -> dict:
    """The real numbers behind STRATEGY.md's "Shared Fencepost Reports in
    the wild" row.

    - total_shared: count of validly-shaped real entries found.
    - most_recent_date: the latest `"date"` among them in real calendar
      order, or None if the log is empty -- expected today, not a
      violation. Compared as parsed `date` objects, never as raw strings:
      `_read_entries` validates a date field by constructing a real
      `date(year, month, day)`, which tolerates non-zero-padded input
      (`"2026-7-9"` is a valid July 9 just as `"2026-07-09"` is) -- but as
      a bare string `"2026-7-9"` sorts AFTER `"2026-12-25"` lexically
      (`'7' > '1'`), even though December is chronologically later. A
      string `max()` over entries would report the wrong date as most
      recent the moment one entry's date isn't zero-padded; comparing
      parsed `date` objects instead is the same discipline
      `metrics_cadence_check.py`/`report_cadence_check.py` already hold.
    - target: STRATEGY.md's own number (50), unchanged by how many are
      recorded.
    - remaining: max(target - total_shared, 0), never negative even past
      target.
    """
    shared_path = shared_path or DEFAULT_SHARED_PATH
    entries = _read_entries(shared_path)
    most_recent_dt = max((_parse_date(e["date"]) for e in entries), default=None)
    most_recent = most_recent_dt.isoformat() if most_recent_dt else None
    total = len(entries)
    return {
        "total_shared": total,
        "most_recent_date": most_recent,
        "target": target,
        "remaining": max(target - total, 0),
    }


def format_shared_reports(result: dict) -> str:
    if result["total_shared"] == 0:
        return (
            f"shared reports in the wild: 0/{result['target']} "
            "(kwaku-ananse's lagging metric) -- zero organic links/screenshots recorded yet"
        )
    return (
        f"shared reports in the wild: {result['total_shared']}/{result['target']} "
        f"(kwaku-ananse's lagging metric) -- most recent {result['most_recent_date']}, "
        f"{result['remaining']} to target"
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    out = compute_shared_reports()
    print(format_shared_reports(out))
    sys.exit(0)
