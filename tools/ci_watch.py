#!/usr/bin/env python3
"""Task 73. Retrya's own Tithe, watched instead of recalled.

Every hourly ritual note since the repo had CI has closed with the same
hand-read line: "`dawn-run`/`pages` both green off task N's push (run ID,
timestamp)" -- a human reading a live `list_workflow_runs` result and typing
the conclusion into prose, re-derived from memory every single hour. That is
the exact shape tasks 57 (the X outage streak), 62 (cron lateness), and
70/71 (the square) already closed for their own numbers -- and it is the
one CI signal that has never once been durably recorded, so nothing has
ever caught a silent flip from green to red except a human happening to
read the right line closely.

`dawn-run` is Retrya's own Tithe: a binary result, fired once a day,
resolved whether she is watching or not -- the same shape as her own three
attempts at the coin. This gives it the identical append-only,
fold-backward discipline `x_outage_tracker.py` already proved for the X
outage: `record_check` never edits or removes a prior line; `current_streak`
walks the log backward and stops at the first non-matching entry, never a
remembered adjective.

Same boundary as `square_check.py`/`cron_health.py`: this module makes no
network call of its own. The god on duty already holds this hour's real
`mcp__github__actions_list` read; this just turns that read into a durable
line and a rule-based fold instead of a felt "still green" glance.

Usage:
    python3 tools/ci_watch.py record <workflow> <success|failure> <run_id> <checked_at>
    python3 tools/ci_watch.py status
"""
import json
import os

LOG = os.path.join(os.path.dirname(__file__), "..", "HAND", "ci-watch-log.jsonl")
CONCLUSIONS = ("success", "failure")
# Task 80: dawn-run/pages essentially never fail -- seam-scan and
# oracle-cadence are the two workflows that actually have (tasks 63/64/65/
# 78/79 each fixed a real live crash in one of them). Watching only the
# two quiet doors left the two loud ones unwatched; this closes that gap
# the same way task 72 closed it for x_outage_tracker.py's TRACKED_TOOLS.
TRACKED_WORKFLOWS = ("dawn-run", "pages", "seam-scan", "oracle-cadence")


def _entries(path=LOG):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _append(entry, path=LOG):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def record_check(workflow: str, conclusion: str, run_id, checked_at: str, path=LOG) -> None:
    """Append one real observed CI conclusion. Never edits or removes a prior line."""
    if conclusion not in CONCLUSIONS:
        raise ValueError(f"unknown conclusion {conclusion!r} -- must be one of {CONCLUSIONS}")
    _append(
        {
            "type": "check",
            "workflow": workflow,
            "conclusion": conclusion,
            "run_id": run_id,
            "checked_at": checked_at,
        },
        path,
    )


def _workflow_entries(entries: list, workflow: str) -> list:
    return [e for e in entries if e.get("type") == "check" and e.get("workflow") == workflow]


def current_streak(entries: list, workflow: str, conclusion: str = "failure") -> int:
    """Count consecutive trailing checks for `workflow` matching `conclusion`.

    Walks backward from the most recent check for this workflow and stops at
    the first one that doesn't match. No checks recorded, or the most recent
    check doesn't match `conclusion`: returns 0. The exact fold
    `x_outage_tracker.current_streak` already proved, applied to CI runs.
    """
    count = 0
    for e in reversed(_workflow_entries(entries, workflow)):
        if e["conclusion"] != conclusion:
            break
        count += 1
    return count


def streak_started_at(entries: list, workflow: str, conclusion: str = "failure"):
    """Timestamp of the oldest check in the current trailing streak, or None."""
    started = None
    for e in reversed(_workflow_entries(entries, workflow)):
        if e["conclusion"] != conclusion:
            break
        started = e["checked_at"]
    return started


def last_check(entries: list, workflow: str):
    """The most recently recorded real check for `workflow`, or None."""
    w_entries = _workflow_entries(entries, workflow)
    return w_entries[-1] if w_entries else None


def format_status_line(entries: list, workflow: str, conclusion: str = "failure") -> str:
    last = last_check(entries, workflow)
    if last is None:
        return f"{workflow}: no checks recorded"
    n = current_streak(entries, workflow, conclusion)
    if n == 0:
        return f"{workflow}: {last['conclusion']} as of {last['checked_at']} (run {last['run_id']})"
    since = streak_started_at(entries, workflow, conclusion)
    checks = "check" if n == 1 else "checks"
    return f"{workflow}: {n} consecutive {conclusion} {checks} (since {since}, last checked {last['checked_at']})"


if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "record":
        _workflow, _conclusion, _run_id, _checked_at = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
        record_check(_workflow, _conclusion, _run_id, _checked_at)
        print("recorded")
    elif cmd == "status":
        _entries_now = _entries()
        for _workflow in TRACKED_WORKFLOWS:
            print(format_status_line(_entries_now, _workflow))
    else:
        print("usage: ci_watch.py record <workflow> <success|failure> <run_id> <checked_at> | status")
        sys.exit(2)
