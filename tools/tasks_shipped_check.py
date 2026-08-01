#!/usr/bin/env python3
"""Task 416. Nisaba closes the last open door task 415 named honestly.

Tasks 145, 412, 413, and 415 each built a live cross-check for a sibling
`records/metrics.jsonl` field (`distinct_toolkits_in_use`,
`connected_users_oauth`, `gap_true_positive_rate`, `reports_shipped_today`)
against real, on-disk ground truth. `tasks_shipped_today` was the one field
left standing -- task 415's own note called its ground truth "messier ...
depends on parsing wip-opened/completion timestamps across a file that
gets archived out from under itself every couple hundred tasks" and left
it open rather than guess.

That framing looked at the wrong file. `ROADMAP.md` is exactly what
`tools/roadmap_archive.py` (task 169) periodically cuts out from under
itself -- but `BUILDLOG.md` never is (confirmed: zero references to
BUILDLOG.md anywhere in `roadmap_archive.py`). It is append-only, one line
per shipped task, `YYYY-MM-DD HH:MM UTC | <god> | <task#> | <one line>`
(its own header, line 3), and it is the SAME file task 117 and task 275
already hand-counted `tasks_shipped_today` from ("21 tasks shipped counted
off BUILDLOG's own dated lines"). The real ground truth was sitting in
plain, stable, never-archived text the whole time.

One real wrinkle task 415 didn't have to face: the daily-aggregate task
that WRITES a `tasks_shipped_today` reading always reports a "so far" count
that excludes itself and anything after it -- task 117's own reading
claimed 21 tasks (96-116) while task 117 itself was task 117, not counted;
task 414 (this desk's own 2026-07-30 reading) claimed 17 (397-413) while
414 itself, and every task after it (415, this one), are correctly left
out. So a plain "every BUILDLOG row dated today" count would be wrong (and
would grow more wrong every hour after 18:00, since numbered tasks keep
shipping past the aggregate). Ground truth instead: find that date's own
daily-aggregate row (BUILDLOG text containing "daily aggregate" -- the
phrase every ordinary 18:00 hour's own line already carries, task 414's
included), take ITS task number as the cutoff, count distinct numbered
task fields strictly below it. A handful of historical catch-up hours
(117, 275) phrased their aggregate line differently and carry no literal
"daily aggregate" match for their date; rather than guess a cutoff for
those, this check only ever looks at the MOST RECENT metrics.jsonl
reading (the same discipline `report_shipped_check.py`/
`gap_true_positive_check.py` already hold), and returns "clean, nothing to
cross-check" when no aggregate row is found for that reading's date --
never a fabricated verdict.

Multi-task rows (task 361's own BUILDLOG line, `360/361`, two tasks closed
in one hour) and rows tagged with a non-numeric task field (`ritual`,
`roadmap`, `daily`, `ledger` -- housekeeping markers, never counted in any
prior day's "N numbered ROADMAP tasks shipped" tally either) are both
handled: every run of digits in the task-field cell is pulled out and
counted as its own task number; a cell with no digits at all contributes
none.

Usage:
    python3 tools/tasks_shipped_check.py check
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_METRICS_PATH = os.path.join(ROOT, "records", "metrics.jsonl")
DEFAULT_BUILDLOG_PATH = os.path.join(ROOT, "BUILDLOG.md")

_ROW_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) [^|\n]*\|([^|\n]*)\|([^|\n]*)\|")
_NUM_RE = re.compile(r"\d+")
_AGGREGATE_RE = re.compile(r"daily aggregate", re.IGNORECASE)


def _last_metrics_entry(metrics_path: str) -> dict | None:
    """The most recently recorded dated reading in `records/metrics.jsonl`.
    Walks non-blank lines from the end and returns the first one that
    parses as valid JSON AND is itself a JSON object; a truncated/
    malformed trailing line is skipped, not fatal -- the same discipline
    `report_shipped_check.py`'s own reader holds (task 415, itself
    following tasks 306/328/412/413). `None` if no reading has ever
    shipped, or every line is malformed or non-dict."""
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


def _buildlog_task_rows(buildlog_path: str, date: str) -> list[tuple[set[int], str]]:
    """`(task_numbers, raw_line)` for every real dated BUILDLOG.md row
    matching `date`, in file order. `task_numbers` is every run of digits
    found in that row's task-field cell (handles both plain numbers and
    multi-task cells like `360/361`); non-numeric cells (`ritual`,
    `roadmap`, `<task#>` the header's own literal, etc.) yield an empty
    set and are skipped by callers that only want real numbered tasks."""
    if not os.path.exists(buildlog_path):
        return []
    rows = []
    with open(buildlog_path, encoding="utf-8") as f:
        for line in f:
            m = _ROW_RE.match(line)
            if not m or m.group(1) != date:
                continue
            nums = {int(n) for n in _NUM_RE.findall(m.group(3))}
            rows.append((nums, line))
    return rows


def _tasks_shipped_ground_truth(buildlog_path: str, date: str) -> int | None:
    """Distinct numbered ROADMAP tasks logged in BUILDLOG.md for `date`,
    strictly before that date's own daily-aggregate task (the aggregate
    task reports what shipped BEFORE it, never counting itself -- task
    117's and task 414's own precedent). Returns `None` if no
    daily-aggregate row is found for `date` at all -- nothing to honestly
    cross-check, not a guessed cutoff."""
    rows = _buildlog_task_rows(buildlog_path, date)
    cutoff = None
    for nums, line in rows:
        if nums and _AGGREGATE_RE.search(line):
            cutoff = min(nums)
            break
    if cutoff is None:
        return None
    counted = {n for nums, _line in rows for n in nums if n < cutoff}
    return len(counted)


def check_tasks_shipped(
    metrics_path: str = DEFAULT_METRICS_PATH,
    buildlog_path: str = DEFAULT_BUILDLOG_PATH,
) -> dict:
    """Cross-check the last recorded `tasks_shipped_today` reading against
    real, live BUILDLOG.md ground truth. Returns `clean: True` when the two
    agree, when there is no reading yet, or when no aggregate row exists
    for that reading's date (absence of ground truth is not a mismatch --
    the same no-reading branch every sibling check already holds);
    otherwise `clean: False` naming the exact claimed vs. real values and
    the date in question, never a bare pass/fail.

    Task 458: the identical `last is None or FIELD not in last` omitted-
    field bug tasks 453-457 already fixed on five sibling `metrics.jsonl`
    checkers (`gap_true_positive_check.py`, `toolkits_in_use_check.py`,
    `report_shipped_check.py`, `github_stars_check.py`,
    `connected_users_check.py`) -- built at task 416, one campaign before
    that fix existed, and never revisited by it. A reading that EXISTS (has
    a `date`) but omits `tasks_shipped_today` used to collapse into the
    same unconditional-clean branch as "no reading has ever existed at
    all", even when real ground truth for that date already names a
    nonzero count the reading failed to carry. Unlike the other five
    siblings, this file's ground truth can ALSO be honestly unknowable
    (`_tasks_shipped_ground_truth` returns `None` when no daily-aggregate
    BUILDLOG.md row exists for that date yet) -- that "real is None" case
    stays clean regardless of what was claimed, same as it always has,
    since there is nothing to contradict a claim with. Only when real
    ground truth is a definite number does an omitted field get judged:
    clean if that real count is honestly `0` (nothing yet to have
    omitted), BROKEN the moment real tasks shipped that day and the
    reading silently dropped the field meant to record it."""
    last = _last_metrics_entry(metrics_path)
    if last is None or "date" not in last:
        return {"clean": True, "real": None, "claimed": None, "claimed_date": None}
    claimed_date = last["date"]
    real = _tasks_shipped_ground_truth(buildlog_path, claimed_date)
    if "tasks_shipped_today" not in last:
        if real is None:
            return {"clean": True, "real": None, "claimed": None, "claimed_date": claimed_date}
        return {
            "clean": real == 0,
            "real": real,
            "claimed": None,
            "claimed_date": claimed_date,
        }
    claimed = last["tasks_shipped_today"]
    if real is None:
        return {"clean": True, "real": None, "claimed": claimed, "claimed_date": claimed_date}
    return {
        "clean": claimed == real,
        "real": real,
        "claimed": claimed,
        "claimed_date": claimed_date,
    }


def format_result(result: dict) -> str:
    if result["claimed_date"] is None:
        return "tasks shipped today: clean (no metrics.jsonl reading yet; nothing to cross-check)"
    if result["claimed"] is None:
        if result["real"] is None:
            return (
                f"tasks shipped today: clean (metrics.jsonl's {result['claimed_date']} reading names no "
                "tasks_shipped_today field; no daily-aggregate BUILDLOG.md row found for that date, "
                "nothing to cross-check)"
            )
        if result["clean"]:
            return (
                f"tasks shipped today: clean (metrics.jsonl's {result['claimed_date']} reading names no "
                "tasks_shipped_today field; real ground truth is honestly 0, nothing omitted)"
            )
        return (
            f"tasks shipped today: BROKEN -- metrics.jsonl's {result['claimed_date']} reading names no "
            f"tasks_shipped_today field, but real ground truth (BUILDLOG.md's own dated rows before "
            f"that day's aggregate task) is already {result['real']} -- a real count exists and was "
            "not recorded, escalate now"
        )
    if result["real"] is None:
        return (
            f"tasks shipped today: clean (metrics.jsonl's {result['claimed_date']} reading claims "
            f"{result['claimed']}; no daily-aggregate BUILDLOG.md row found for that date, "
            "nothing to cross-check)"
        )
    if result["clean"]:
        return (
            f"tasks shipped today: clean (metrics.jsonl's {result['claimed_date']} reading claims "
            f"{result['claimed']}, real ground truth (BUILDLOG.md's own dated rows before that "
            "day's aggregate task) agrees)"
        )
    return (
        f"tasks shipped today: BROKEN -- metrics.jsonl's {result['claimed_date']} reading claims "
        f"{result['claimed']}, real ground truth (BUILDLOG.md's own dated rows before that day's "
        f"aggregate task) is {result['real']} -- misreporting live, escalate now"
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = check_tasks_shipped()
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
