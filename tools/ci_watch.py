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

Task 2694. A sustained CI failure streak (oracle-cadence, seam-scan) sat
watched (`current_streak`/`format_status_line`) but never escalated --
`x_outage_tracker.py` grew the identical shape for the X outage at task 81
(`should_escalate`/`record_escalation`) specifically because a watched-but-
never-surfaced streak is indistinguishable from an unwatched one to the god
on duty unless something names the moment it crosses a real threshold. This
closes that same gap here: a single fixed tier (`DEFAULT_ESCALATION_
THRESHOLD_HOURS`), not yet the `x_outage_tracker`-style extended/recurring
tier ladder (task 422 added that one LATER, after the X outage had already
lived past its first tier for weeks -- no CI streak here has yet, so there
is nothing real to generalize for yet). A real escalation is still only
ever recorded when the god on duty actually calls `record_escalation`;
`should_escalate` itself makes no write.

Usage:
    python3 tools/ci_watch.py record <workflow> <success|failure> <run_id> <checked_at>
    python3 tools/ci_watch.py status
    python3 tools/ci_watch.py should-escalate <workflow> <now> [threshold_hours]
"""
import json
import os
import sys
from typing import cast

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iso_time  # noqa: E402
import jsonl_append  # noqa: E402
import jsonl_read  # noqa: E402

LOG = os.path.join(os.path.dirname(__file__), "..", "HAND", "ci-watch-log.jsonl")
ESCALATION_LOG = os.path.join(os.path.dirname(__file__), "..", "HAND", "ci-watch-escalation-log.jsonl")
# CI failures are a faster-moving signal than the X outage (checked once
# per real hourly session either way, but a broken `dawn-run`/`oracle-cadence`
# blocks the loop's own forward progress within the same day it breaks,
# where the X outage has sat broken for months without blocking anything).
# 6h -- roughly one daytime-rotation quarter-cycle -- names a streak that has
# survived more than one god's own hourly recheck, not a single transient
# blip one retry would clear.
DEFAULT_ESCALATION_THRESHOLD_HOURS = 6.0
_parse = iso_time.parse_iso_utc


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
CONCLUSIONS = (
    "success",
    "failure",
    # Task 580: this tuple used to be a bare binary ("success", "failure"),
    # and record_check refuses (ValueError) anything outside it. GitHub
    # Actions' own documented conclusion vocabulary is wider than that --
    # confirmed live this hour on this repo's own real incident: pages run
    # 31119308176 completed with conclusion "cancelled" (a genuinely
    # different outcome from "failure": the run never ran to a red result,
    # it was called off). Task 577's own BUILDLOG entry had already hit this
    # exact wall and worked around it by recording a stuck-queued run AS
    # "failure" -- the only two labels this tuple allowed -- which is a
    # small honesty leak in a tool whose whole reason to exist is not
    # trusting a human's felt "still green" glance (see this module's own
    # header docstring). The remaining five are GitHub's real terminal
    # conclusion values (a run still in progress or queued has conclusion
    # `null`, not one of these, and correctly is not recorded here at all --
    # only completed runs have a conclusion to record).
    "cancelled",
    "skipped",
    "timed_out",
    "action_required",
    "neutral",
    "stale",
)
# Task 80: dawn-run/pages essentially never fail -- seam-scan and
# oracle-cadence are the two workflows that actually have (tasks 63/64/65/
# 78/79 each fixed a real live crash in one of them). Watching only the
# two quiet doors left the two loud ones unwatched; this closes that gap
# the same way task 72 closed it for x_outage_tracker.py's TRACKED_TOOLS.
TRACKED_WORKFLOWS = ("dawn-run", "pages", "seam-scan", "oracle-cadence")


def _entries(path: str = LOG) -> list[dict[str, object]]:
    """Delegates to jsonl_read.read_jsonl_entries (task 540) -- see
    that module's own docstring for the fourteen-copy history this
    replaced."""
    return jsonl_read.read_jsonl_entries(path)

# Task 510: consolidated into tools/jsonl_append.py -- ten sibling checks
# each carried a byte-identical copy of this helper. This name now points
# at the shared function object, not a local copy; tests/test_jsonl_
# append.py asserts this name IS that shared function.
_append = jsonl_append.append_jsonl


def record_check(workflow: str, conclusion: str, run_id: int | str, checked_at: str, path: str = LOG) -> bool:
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
    entry: dict[str, object] = {
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
    if last is not None and _same_observation(last, entry):
        return False
    _append(entry, path)
    return True


def _same_observation(a: dict[str, object], b: dict[str, object]) -> bool:
    """True if two recorded check entries name the identical real moment.

    Task 541: `record_check`'s dedup used to compare entry dicts with a bare
    `==`. `ritual_check.py`'s `check_ci` feeds `run_id` straight off a
    JSON-decoded `--ci-checks` file (a bare number parses as a Python int),
    while the standalone `ci_watch.py record` CLI always hands `run_id`
    through as a `str` (every `sys.argv` element is one). The same real
    GitHub run recorded once via each entry point in the same hour -- exactly
    what happened live in `HAND/ci-watch-log.jsonl` this hour -- produced two
    `run_id` values that are equal in value but unequal in type, so
    `{"run_id": 111} == {"run_id": "111"}` reads False and task 501's dedup
    silently missed it. Every other field is compared as-is; only `run_id`
    is compared by its string form, since it is an identifier, never
    arithmetic.
    """
    if a.keys() != b.keys():
        return False
    for key, a_val in a.items():
        b_val = b[key]
        if key == "run_id":
            if str(a_val) != str(b_val):
                return False
        elif a_val != b_val:
            return False
    return True


def _workflow_entries(entries: list[dict[str, object]], workflow: str) -> list[dict[str, object]]:
    for e in entries:
        if e.get("_malformed"):
            raise CIWatchTamperedError(
                f"_workflow_entries({workflow!r}): the log holds a line that "
                f"is not valid JSON ({e.get('_error')}) -- refusing to guess "
                "which workflow it belonged to. Repair the log by hand, "
                "then rerun."
            )
    return [e for e in entries if e.get("type") == "check" and e.get("workflow") == workflow]


def current_streak(entries: list[dict[str, object]], workflow: str, conclusion: str = "failure") -> int:
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


def streak_started_at(entries: list[dict[str, object]], workflow: str, conclusion: str = "failure") -> str | None:
    """Timestamp of the oldest check in the current trailing streak, or None."""
    started = None
    for e in reversed(_workflow_entries(entries, workflow)):
        if e["conclusion"] != conclusion:
            break
        started = e["checked_at"]
    return cast("str | None", started)


def last_check(entries: list[dict[str, object]], workflow: str) -> dict[str, object] | None:
    """The most recently recorded real check for `workflow`, or None."""
    w_entries = _workflow_entries(entries, workflow)
    return w_entries[-1] if w_entries else None


def format_status_line(entries: list[dict[str, object]], workflow: str, conclusion: str = "failure") -> str:
    last = last_check(entries, workflow)
    if last is None:
        return f"{workflow}: no checks recorded"
    n = current_streak(entries, workflow, conclusion)
    if n == 0:
        return f"{workflow}: {last['conclusion']} as of {last['checked_at']} (run {last['run_id']})"
    since = streak_started_at(entries, workflow, conclusion)
    checks = "check" if n == 1 else "checks"
    return f"{workflow}: {n} consecutive {conclusion} {checks} (since {since}, last checked {last['checked_at']})"


def _escalation_entries(path: str = ESCALATION_LOG) -> list[dict[str, object]]:
    """Every line in the escalation log, parsed. Mirrors
    `x_outage_tracker._escalation_entries` -- a malformed line comes back
    marked `{"_malformed": True, "_error": ...}` instead of raising or
    crashing `already_escalated_for_streak`'s own `.get("_malformed")` read
    on a bare non-dict value."""
    return jsonl_read.read_jsonl_entries(path)


def record_escalation(
    workflow: str,
    streak_started_at_: str,
    escalated_at: str,
    hours: float,
    threshold_hours: float = DEFAULT_ESCALATION_THRESHOLD_HOURS,
    path: str = ESCALATION_LOG,
) -> None:
    """Append one real escalation event. Never edits or removes a prior line.

    `streak_started_at_` is named with a trailing underscore only to avoid
    shadowing this module's own `streak_started_at` function in the same
    namespace -- the logged field itself is still plain `streak_started_at`."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    entry = {
        "type": "escalation",
        "workflow": workflow,
        "streak_started_at": streak_started_at_,
        "escalated_at": escalated_at,
        "hours": hours,
        "threshold_hours": threshold_hours,
    }
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def already_escalated_for_streak(
    escalation_entries: list[dict[str, object]],
    workflow: str,
    streak_started_at_: str,
    threshold_hours: float = DEFAULT_ESCALATION_THRESHOLD_HOURS,
) -> bool:
    """Whether this exact streak already fired an escalation AT THIS TIER.

    Keyed on (workflow, streak_started_at, threshold_hours), the identical
    discipline `x_outage_tracker.already_escalated_for_streak` holds (task
    92's generalization there) -- a streak is identified by when it
    started, not just its length, so a recovered-then-broken-again
    workflow gets its own fresh escalation rather than staying silently
    suppressed by a prior, already-resolved one."""
    for e in escalation_entries:
        if e.get("_malformed"):
            raise CIWatchTamperedError(
                f"already_escalated_for_streak({workflow!r}): the escalation "
                f"log holds a line that is not valid JSON ({e.get('_error')}) "
                "-- refusing to guess whether this tier already fired. Repair "
                "the log by hand, then rerun."
            )
    return any(
        e.get("type") == "escalation"
        and e.get("workflow") == workflow
        and e.get("streak_started_at") == streak_started_at_
        and e.get("threshold_hours", DEFAULT_ESCALATION_THRESHOLD_HOURS) == threshold_hours
        for e in escalation_entries
    )


def should_escalate(
    entries: list[dict[str, object]],
    workflow: str,
    now: str,
    threshold_hours: float = DEFAULT_ESCALATION_THRESHOLD_HOURS,
    escalation_entries: list[dict[str, object]] | None = None,
) -> tuple[bool, str]:
    """Whether an ongoing `workflow` failure streak has crossed the point
    the Hand should hear about it. Returns (due: bool, reason: str).

    Never due if the workflow isn't currently in a failure streak (green,
    or never checked). Due once the current streak has run at least
    `threshold_hours`, UNLESS this exact streak already fired an
    escalation at this tier -- mirrors `x_outage_tracker.should_escalate`
    exactly, one fixed tier instead of that module's later extended/
    recurring ladder (see this module's header docstring, task 2694)."""
    if escalation_entries is None:
        escalation_entries = _escalation_entries()
    streak = current_streak(entries, workflow, "failure")
    if streak == 0:
        return False, "no active failure streak"
    started = cast(str, streak_started_at(entries, workflow, "failure"))
    elapsed = (_parse(now) - _parse(started)).total_seconds() / 3600.0
    if elapsed < threshold_hours:
        return False, f"failure streak {elapsed:.1f}h old, below {threshold_hours}h threshold"
    if already_escalated_for_streak(escalation_entries, workflow, started, threshold_hours):
        return False, f"already escalated for the streak that began {started} at the {threshold_hours}h tier"
    return True, f"failing since {started}, {elapsed:.1f}h old, crosses {threshold_hours}h threshold"


if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "record":
        if len(sys.argv) < 6:
            print("usage: ci_watch.py record <workflow> <success|failure> <run_id> <checked_at>")
            sys.exit(2)
        _workflow, _conclusion, _run_id, _checked_at = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
        record_check(_workflow, _conclusion, _run_id, _checked_at)
        print("recorded")
    elif cmd == "status":
        _entries_now = _entries()
        for _workflow in TRACKED_WORKFLOWS:
            print(format_status_line(_entries_now, _workflow))
    elif cmd == "should-escalate":
        if len(sys.argv) < 4:
            print("usage: ci_watch.py should-escalate <workflow> <now> [threshold_hours]")
            sys.exit(2)
        _workflow, _now = sys.argv[2], sys.argv[3]
        _threshold = float(sys.argv[4]) if len(sys.argv) > 4 else DEFAULT_ESCALATION_THRESHOLD_HOURS
        _due, _reason = should_escalate(_entries(), _workflow, _now, _threshold)
        print(f"{'due' if _due else 'not due'} -- {_reason}")
    else:
        print(
            "usage: ci_watch.py record <workflow> <success|failure> <run_id> <checked_at> "
            "| status | should-escalate <workflow> <now> [threshold_hours]"
        )
        sys.exit(2)
