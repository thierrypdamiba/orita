#!/usr/bin/env python3
"""Task 62. Off-By-One's fix for the ritual's other hand-eyeballed number.

Every hour, whoever's on duty checks whether `seam-scan.yml`/
`oracle-cadence.yml` have run today by squinting at a run list and doing
the arithmetic in their head: "last run was 2026-07-13T14:30Z, it's now
2026-07-14T13:0xZ, is that today's window late, or did I just read
yesterday's run and think it was today's?" That is precisely the shape of
mistake I exist to catch -- a remembered date compared to a felt "recent
enough," not a rule anyone could point at. `x_outage_tracker.py` already
turned one such hand-judgment (is a retest due?) into a fixed cooldown;
this does the same for "is a scheduled workflow actually late, or just
running inside GitHub's own documented scheduling delay?"

This module does not call the GitHub API itself -- same boundary
`x_outage_tracker.py` draws around `record_check()`: the god on duty
already fetches the real last-run timestamp via `mcp__github__actions_list`
(or `gh`) as part of the hourly ritual; this just turns that timestamp,
plus the workflow's own declared cron, into a rule-based verdict instead
of a felt one.

Task 82 folds this module into `tools/ritual_check.py`'s one structured
status block via `check_cron(cron_checks, now_iso)`, mirroring how task 73
already folded `ci_watch.py` in despite both taking the identical
live-API-input-but-no-network-call shape. Calling `cron_health.py`
directly, as below, still works standalone -- the fold is additive.

Usage:
    python3 tools/cron_health.py <cron_expr> <last_run_iso|-> <now_iso> [grace_hours]
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iso_time  # noqa: E402

DEFAULT_GRACE_HOURS = 2.0
STATUSES = ("on_time", "pending", "overdue")

# Task 509: consolidated into tools/iso_time.py -- three sibling checks
# (cron_health.py, voice_window_check.py, x_outage_tracker.py) each
# carried a byte-identical copy of this parser. This name now points at
# the shared function object, not a local copy; tests/test_iso_time.py
# asserts this name IS that shared function.
_parse = iso_time.parse_iso_utc


def parse_daily_cron(cron_expr: str) -> tuple:
    """Parse a fixed-hour daily cron ('MINUTE HOUR * * *') into (hour, minute).

    Every scheduled workflow in this repo (`seam-scan`, `oracle-cadence`)
    uses exactly this shape. Broader cron support (weekly, multi-hour,
    step values) is deliberately out of scope -- there is nothing in this
    repo that would exercise it, and a parser for crons nobody writes is
    just an untested surface waiting to be wrong.
    """
    parts = cron_expr.split()
    if len(parts) != 5 or parts[2:] != ["*", "*", "*"]:
        raise ValueError(f"only fixed-hour daily crons ('M H * * *') are supported, got {cron_expr!r}")
    minute, hour = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"invalid hour/minute in cron {cron_expr!r}")
    return hour, minute


def most_recent_scheduled_fire(cron_expr: str, now: datetime) -> datetime:
    """The most recent time <= `now` this daily cron was due to fire."""
    hour, minute = parse_daily_cron(cron_expr)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate > now:
        candidate -= timedelta(days=1)
    return candidate


def schedule_status(cron_expr: str, last_run_at, now: str, grace_hours: float = DEFAULT_GRACE_HOURS) -> dict:
    """Where a scheduled workflow stands against its own declared cron.

    - on_time: a run landed at or after today's scheduled fire time. A run
      from a prior day never counts, no matter how close in prose "one
      total run" reads to "ran today".
    - pending: today's window opened `grace_hours` ago or less and nothing
      has landed since -- GitHub's own documented scheduled-workflow
      delay, not a bug worth flagging.
    - overdue: today's window opened more than `grace_hours` ago and
      nothing has landed since -- worth a human's attention.
    """
    now_dt = _parse(now)
    due_at = most_recent_scheduled_fire(cron_expr, now_dt)
    last_dt = _parse(last_run_at) if last_run_at else None
    if last_dt is not None and last_dt >= due_at:
        return {
            "status": "on_time",
            "due_at": due_at.isoformat(),
            "last_run_at": last_run_at,
            "hours_late": None,
        }
    elapsed_hours = (now_dt - due_at).total_seconds() / 3600.0
    status = "pending" if elapsed_hours <= grace_hours else "overdue"
    return {
        "status": status,
        "due_at": due_at.isoformat(),
        "last_run_at": last_run_at,
        "hours_late": round(elapsed_hours, 2),
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("usage: cron_health.py <cron_expr> <last_run_iso|-> <now_iso> [grace_hours]")
        sys.exit(2)
    _cron_expr, _last_run, _now = sys.argv[1], sys.argv[2], sys.argv[3]
    _grace = float(sys.argv[4]) if len(sys.argv) > 4 else DEFAULT_GRACE_HOURS
    _result = schedule_status(_cron_expr, None if _last_run == "-" else _last_run, _now, _grace)
    print(json.dumps(_result, ensure_ascii=False))
    sys.exit(1 if _result["status"] == "overdue" else 0)
