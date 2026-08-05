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
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jsonl_append  # noqa: E402
import jsonl_read  # noqa: E402

LOG = os.path.join(os.path.dirname(__file__), "..", "HAND", "ci-watch-log.jsonl")


class CIWatchTamperedError(RuntimeError):
    """Raised when a workflow-filtered read (current_streak/streak_started_at/
    last_check/format_status_line) finds a malformed line anywhere in the log.
    Mirrors tools/x_post_queue.py's QueueTamperedError (task 240): a malformed
    line has lost its "type"/"workflow" fields, so _workflow_entries' filter
    would silently drop it from EVERY workflow's view rather than just the one
    it really belonged to -- guessing which workflow's streak it was could
    stitch two real entries together that shouldn't be adjacent, silently
    shortening or lengthening a reported failure streak. Refuse rather than
    guess, the same discipline tasks 238-242 already applied to their own
    logs. Run this tool's `status` command by hand to see the break, then
    repair the log before the next real check/record."""
CONCLUSIONS = ("success", "failure")
# Task 80: dawn-run/pages essentially never fail -- seam-scan and
# oracle-cadence are the two workflows that actually have (tasks 63/64/65/
# 78/79 each fixed a real live crash in one of them). Watching only the
# two quiet doors left the two loud ones unwatched; this closes that gap
# the same way task 72 closed it for x_outage_tracker.py's TRACKED_TOOLS.
TRACKED_WORKFLOWS = ("dawn-run", "pages", "seam-scan", "oracle-cadence")


def _entries(path=LOG):
    """Delegates to jsonl_read.read_jsonl_entries (task 540) -- see
    that module's own docstring for the fourteen-copy history this
    replaced."""
    return jsonl_read.read_jsonl_entries(path)

# Task 510: consolidated into tools/jsonl_append.py -- ten sibling checks
# each carried a byte-identical copy of this helper. This name now points
# at the shared function object, not a local copy; tests/test_jsonl_
# append.py asserts this name IS that shared function.
_append = jsonl_append.append_jsonl


def record_check(workflow: str, conclusion: str, run_id, checked_at: str, path=LOG) -> bool:
    """Append one real observed CI conclusion. Never edits or removes a prior line.

    Task 501: the one genuine gap task 495 found live and named but deferred
    ("left the underlying ci_watch.py dedup fix itself for a future task
    rather than scope-creep this hour's real, due Cluster Day work") -- the
    real `HAND/ci-watch-log.jsonl` carries 84 byte-for-byte-identical lines
    (same workflow/conclusion/run_id/checked_at, all four fields) out of 431
    total, produced whenever two `ritual_check.py` invocations fed this
    function the exact same already-recorded observation a second time (a
    retry, an addendum call re-reading the same live state, task 495's own
    self-caught example). This is a narrower criterion than `square_check.py`/
    `scribe_growth_check.py`/`word_watch.py`'s "skip if the durable STATE is
    unchanged" dedup (tasks 487/497/498): those are single-baseline logs
    where two calls with an unchanged state carry zero new information no
    matter when they land. `current_streak`'s whole design instead REQUIRES
    that two genuinely separate real checks landing on the same conclusion
    at two different real moments both count (a five-hour green streak is
    five recorded lines, not one) -- so this only refuses the exact
    resubmission of an already-recorded moment (`checked_at` matching too,
    not just workflow/conclusion/run_id), never a real new observation that
    merely repeats the same conclusion. Returns True if a line was written,
    False if this exact entry was already the last one recorded for this
    workflow (mirroring `record_square_check`/`record_app_check`/
    `record_toolset_check`'s bool-return shape) -- the one real caller
    (`ritual_check.py`'s `check_ci`) does not yet use the return value,
    so this is not a breaking change to anything that calls it live.
    """
    if conclusion not in CONCLUSIONS:
        raise ValueError(f"unknown conclusion {conclusion!r} -- must be one of {CONCLUSIONS}")
    entry = {
        "type": "check",
        "workflow": workflow,
        "conclusion": conclusion,
        "run_id": run_id,
        "checked_at": checked_at,
    }
    # A malformed line ANYWHERE in the log is "cannot confirm a duplicate",
    # not a reason to refuse writing -- recording must still be able to
    # repair a corrupted log by appending a fresh valid line, the identical
    # discipline record_square_check's own write path holds (task 497):
    # only *reading* (current_streak/last_check/format_status_line) refuses
    # to guess past a bad line, never writing.
    try:
        last = last_check(_entries(path), workflow)
    except CIWatchTamperedError:
        last = None
    if last is not None and last == entry:
        return False
    _append(entry, path)
    return True


def _workflow_entries(entries: list, workflow: str) -> list:
    for e in entries:
        if e.get("_malformed"):
            raise CIWatchTamperedError(
                f"_workflow_entries({workflow!r}): the log holds a line that "
                f"is not valid JSON ({e.get('_error')}) -- refusing to guess "
                "which workflow it belonged to. Repair the log by hand, "
                "then rerun."
            )
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
