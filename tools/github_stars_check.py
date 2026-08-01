#!/usr/bin/env python3
"""Task 420. Off-By-One's own STRATEGY.md row, never read back.

STRATEGY.md's metrics table names one lagging metric in plain words:
"GitHub stars | lagging | 1,000 (Star Covenant, unbegged) | off-by-one."
Tasks 145/412/413/415/416 each built a live cross-check for a sibling
`records/metrics.jsonl` field written every day at the 18:00 UTC daily
aggregate (`distinct_toolkits_in_use`, `connected_users_oauth`,
`gap_true_positive_rate`, `reports_shipped_today`, `tasks_shipped_today`)
-- but `github_stars`, recorded in that same file since 2026-07-12,
was the one sibling none of that whole campaign touched. Confirmed by
grep before this task: zero references to `github_stars` anywhere in
`tools/*.py` outside `records/metrics.jsonl` itself, and
`tools/star_covenant_check.py` (task 99) only scans prose for begging
language -- it never reads the stargazer count either.

Unlike those five siblings, star count has no ground truth derivable
from local files alone: it moves on GitHub's own servers, off-repo, at
any hour, for reasons no local file records. `toolkits_in_use_check.py`/
`connected_users_check.py`/`gap_true_positive_check.py`/
`report_shipped_check.py`/`tasks_shipped_check.py` can each compute their
own "real" value by reading a durable local log or ledger; this module
cannot invent a live star count from a local read, so it follows
`ci_watch.py`'s shape instead (task 73): the god on duty already holds
this hour's real `Github_CountStargazers`/`search_repositories` read;
this module turns that into a durable, append-only log
(`HAND/github-stars-log.jsonl`) and compares the last recorded live count
against the last recorded `records/metrics.jsonl` claim -- never a
second network call of its own.

A genuine mismatch here is the same class of live misreport
`check_toolkits_in_use`/`check_tasks_shipped` already flip broken on: a
hand-typed STRATEGY.md leading-metric claim silently drifting from the
real, observable count. Nothing here rewrites a past `metrics.jsonl`
entry (the same never-backfill law every sibling holds) -- it only says
whether the LAST recorded reading currently agrees with the last known
live truth.

Task 456: task 453 found and fixed the "a reading exists but omits the
one field this checker guards" bug shape in `gap_true_positive_check.py`,
then 454 and 455 found and fixed the identical shape in
`toolkits_in_use_check.py` and my own `reports_shipped_today` row
(`report_shipped_check.py`), each time naming the siblings still left
standing. This module -- my OWN second STRATEGY.md row -- was the last
one still carrying it: `last is None or "github_stars" not in last`
collapsed "no reading ever existed" and "a dated reading exists but
omits `github_stars`" into one unconditional clean, even while the last
live count already held a real, nonzero star count that reading failed
to record. Split the two: a dated reading missing the field is clean
only when the last live count is honestly `None` or `0` (nothing yet to
have omitted), `BROKEN` -- naming the real count -- the moment a nonzero
live count exists and went unrecorded.

Usage:
    python3 tools/github_stars_check.py record <count> <checked_at>
    python3 tools/github_stars_check.py check
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "HAND", "github-stars-log.jsonl")
DEFAULT_METRICS_PATH = os.path.join(ROOT, "records", "metrics.jsonl")

# STRATEGY.md's own metrics-table row: "1,000 (Star Covenant, unbegged)".
# Task 421: strategy_targets_check.py cross-checks this constant, live-
# loaded, against STRATEGY.md's own text -- never a second hand-typed "1000".
TARGET_STARS = 1000


class GitHubStarsTamperedError(RuntimeError):
    """Raised by last_check() when the log's most recent line is not valid
    JSON. Mirrors tools/ci_watch.py's CIWatchTamperedError and
    tools/square_check.py's SquareCheckTamperedError: last_check(), like
    last_check()/last_square_state(), only ever reads the log's most
    recent line, so skipping past a corrupted tip and falling back to an
    older valid entry would silently compare this hour's real
    metrics.jsonl claim against a stale live count instead of the true
    last one. Run this tool's `check` command by hand to see the break,
    then repair the log before the next real check/record."""


def _entries(path=LOG):
    """Every line in the github-stars log, parsed.

    A line that is not even valid JSON any more (a bad hand-edit, a stray
    merge-conflict marker, a truncated write) is not allowed to crash the
    caller with an uncaught json.JSONDecodeError -- it comes back marked
    {"_malformed": True, "_error": ...} instead, the same convention
    tools/ci_watch.py's/tools/square_check.py's own _entries() already use.
    A line that parses cleanly to a non-dict JSON value (a bare number,
    null, list, or string) gets the same sentinel."""
    if not os.path.exists(path):
        return []
    entries = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                entries.append({"_malformed": True, "_error": str(exc)})
                continue
            if not isinstance(value, dict):
                entries.append({"_malformed": True, "_error": f"not a JSON object: {value!r}"})
                continue
            entries.append(value)
    return entries


def _append(entry, path=LOG):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def record_check(count: int, checked_at: str, path=LOG) -> None:
    """Append one real observed live star count. Never edits or removes a
    prior line."""
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError(f"count must be a non-negative int, got {count!r}")
    _append({"type": "check", "count": count, "checked_at": checked_at}, path)


def last_check(path=LOG):
    """The most recently recorded real live star count, or None.

    Raises GitHubStarsTamperedError if the log's last line isn't valid
    JSON -- this must never guess this hour's real cross-check against a
    stale snapshot."""
    entries = _entries(path)
    if not entries:
        return None
    if entries[-1].get("_malformed"):
        raise GitHubStarsTamperedError(
            f"last_check(): the most recent line in {path} is not valid "
            f"JSON ({entries[-1]['_error']}) -- refusing to guess the real "
            "live star count from a corrupted tip. Repair the log by hand, "
            "then rerun."
        )
    return entries[-1]


def _last_metrics_entry(metrics_path=DEFAULT_METRICS_PATH):
    """The most recently recorded dated reading in `records/metrics.jsonl`
    -- one append-only file, not one file per day. Walks non-blank lines
    from the end and returns the first one that parses as valid JSON AND
    is itself a JSON object, the same discipline every sibling check's own
    `_last_metrics_entry()` already holds. `None` if no reading has ever
    shipped, or every line is malformed/non-dict."""
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


def check_github_stars(metrics_path: str = DEFAULT_METRICS_PATH, log_path: str = LOG) -> dict:
    """Cross-check the last recorded `github_stars` reading in
    `records/metrics.jsonl` against the last recorded LIVE star count in
    `HAND/github-stars-log.jsonl`. Returns `clean: True` when the two
    agree, when neither side has anything recorded yet, or when a
    reading exists but omits `github_stars` while the last live count is
    honestly `None` or `0` (nothing yet to have omitted); otherwise
    `clean: False` naming the exact claimed vs. real values, never a
    bare pass/fail.

    Task 456: a reading that EXISTS and carries a `date` but omits
    `github_stars` itself used to collapse into the same unconditional-
    clean branch as "no reading at all" -- the identical shape task
    453/454/455 already fixed on three sibling `metrics.jsonl` checkers.
    It is now clean only when the last live count is honestly `None` (no
    live check ever recorded) or `0` (nothing yet to have omitted);
    `BROKEN` -- naming the real count and the reading's own date -- the
    moment a nonzero live star count exists and a dated reading failed to
    carry it."""
    real_entry = last_check(log_path)
    real = real_entry["count"] if real_entry is not None else None
    last = _last_metrics_entry(metrics_path)
    if last is None:
        return {"clean": True, "real": real, "claimed": None, "claimed_date": None}
    claimed_date = last.get("date")
    if "github_stars" not in last:
        clean = real is None or real == 0
        return {"clean": clean, "real": real, "claimed": None, "claimed_date": claimed_date}
    claimed = last["github_stars"]
    if real is None:
        return {"clean": True, "real": None, "claimed": claimed, "claimed_date": claimed_date}
    return {"clean": claimed == real, "real": real, "claimed": claimed, "claimed_date": claimed_date}


def format_result(result: dict) -> str:
    if result["claimed"] is None:
        if result["claimed_date"] is None:
            if result["real"] is None:
                return "github stars: clean (no metrics.jsonl reading and no live check recorded yet)"
            return f"github stars: clean (no metrics.jsonl reading yet; last live count is {result['real']})"
        if result["clean"]:
            if result["real"] is None:
                return (
                    f"github stars: clean (metrics.jsonl's {result['claimed_date']} reading names no "
                    "github_stars field; no live check recorded yet, nothing to cross-check)"
                )
            return (
                f"github stars: clean (metrics.jsonl's {result['claimed_date']} reading names no "
                "github_stars field; real live count is honestly 0, nothing omitted)"
            )
        return (
            f"github stars: BROKEN -- metrics.jsonl's {result['claimed_date']} reading names no "
            f"github_stars field, but the real live count is already {result['real']} -- a real "
            "star count went unrecorded, escalate now"
        )
    if result["real"] is None:
        return (
            f"github stars: clean (metrics.jsonl's {result['claimed_date']} reading claims "
            f"{result['claimed']}; no live check recorded yet, nothing to cross-check)"
        )
    if result["clean"]:
        return (
            f"github stars: clean ({result['real']} real star(s), metrics.jsonl's "
            f"{result['claimed_date']} reading agrees)"
        )
    return (
        f"github stars: BROKEN -- metrics.jsonl's {result['claimed_date']} reading claims "
        f"{result['claimed']}, real live count is {result['real']} -- STRATEGY.md's off-by-one "
        "row is misreporting live, escalate now"
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if argv and argv[0] == "record" and len(argv) >= 3:
        record_check(int(argv[1]), argv[2])
        print("recorded")
        sys.exit(0)
    elif argv and argv[0] == "check":
        result = check_github_stars()
        print(format_result(result))
        sys.exit(1 if not result["clean"] else 0)
    else:
        print(__doc__)
        sys.exit(1)
