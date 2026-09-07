#!/usr/bin/env python3
"""Task 1301. A durable tracker for a failure mode this town had never
once recorded: the GitHub MCP server session itself coming back invalid,
as distinct from the long-standing, already-tracked Arcade `the-hand`
GitHub reauthorization wall (`orita-vault/hand/skipped.md`'s
"`Github_CountStargazers` still needs re-authorization" entries, recurring
since task 969).

Those are two different doors to the same destination and they fail
differently. The Arcade door fails loud and structured: every
`mcp__the-hand__Github_*` call comes back a clean `authorization_required`
JSON payload with a link a human can click. The plain GitHub MCP door
(`mcp__github__*` -- `get_me`, `list_issues`, `list_pull_requests`,
`search_repositories`, `actions_list`, ...) had never been seen to fail at
all before this hour; when it did, every single one of those tools
returned the identical bare string `"Error POSTing to endpoint: invalid
session"` -- no link, nothing actionable, no existing tracker anywhere in
`tools/` recorded it. `orita-vault/hand/skipped.md`'s ~40 prior entries
narrating the Arcade wall would have silently absorbed this new, different
failure into the same paragraph if nothing distinguished them -- exactly
the kind of two-different-things-treated-as-one-thing that already forced
task 92's escalation-tier keying fix and task 1062's mis-cased-tool-name
fix on `x_outage_tracker.py`. This gives the GitHub-MCP-session failure
its own durable, append-only log and its own streak count, the same
discipline `x_outage_tracker.py` (task 57) already gives the X side and
`ci_watch.py` gives CI, so a future hour asks a log instead of re-deriving
"how many hours has this been down" from memory.

Deliberately smaller than `x_outage_tracker.py`: no escalation tiers yet
(a first real occurrence has no history to escalate on -- ESCALATION_TIERS
was itself only added to that module after its outage had already run
days, by task 92; the identical machinery here today would have nothing
to fire on and nothing to test against real data). `record_check`,
`current_streak`, `last_check`, and `should_recheck` cover what today's
occurrence actually needed. A future task can add tiers here the same way
task 92 added them there, once there is a real streak to size them against.

Usage:
    python3 tools/github_mcp_outage_check.py record <ok|invalid_session> <checked_at>
    python3 tools/github_mcp_outage_check.py status
    python3 tools/github_mcp_outage_check.py should-recheck <now> [cooldown_hours]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iso_time  # noqa: E402
import jsonl_append  # noqa: E402
import jsonl_read  # noqa: E402

DEFAULT_COOLDOWN_HOURS = 2.0

LOG = os.path.join(os.path.dirname(__file__), "..", "HAND", "github-mcp-outage-log.jsonl")
STATUSES = ("ok", "invalid_session")


class GithubMcpOutageTrackerTamperedError(RuntimeError):
    """Raised when a read (current_streak/last_check/hours_since_last_check/
    should_recheck) finds a malformed line anywhere in the log. Mirrors
    `x_outage_tracker.XOutageTrackerTamperedError`: refuse to guess past a
    corrupted line rather than silently stitching two real streaks
    together or dropping one. Run `status` by hand to see the break, then
    repair the log before the next real check/record."""


def _entries(path: str = LOG) -> list[dict[str, object]]:
    return jsonl_read.read_jsonl_entries(path)


_append = jsonl_append.append_jsonl


def _checked_entries(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    for e in entries:
        if e.get("_malformed"):
            raise GithubMcpOutageTrackerTamperedError(
                f"the log holds a line that is not valid JSON ({e.get('_error')}) "
                "-- refusing to guess what it recorded. Repair the log by hand, "
                "then rerun."
            )
    return [e for e in entries if e.get("type") == "check"]


def last_check(entries: list[dict[str, object]]) -> dict[str, object] | None:
    """The most recently recorded real check, or None."""
    c_entries = _checked_entries(entries)
    return c_entries[-1] if c_entries else None


def record_check(status: str, checked_at: str, path: str = LOG) -> bool:
    """Append one real check of the GitHub MCP server's own session
    validity. Never edits or removes a prior line. Returns True if a line
    was written, False if this exact entry was already the last one
    recorded (an accidental resubmission of the same observation, the same
    dedup `x_outage_tracker.record_check` applies)."""
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r} -- must be one of {STATUSES}")
    try:
        iso_time.parse_iso_utc(checked_at)
    except ValueError as exc:
        raise ValueError(f"unparseable checked_at {checked_at!r}: {exc}") from exc
    entry = {"type": "check", "status": status, "checked_at": checked_at}
    try:
        last = last_check(_entries(path))
    except GithubMcpOutageTrackerTamperedError:
        last = None
    if last is not None and last == entry:
        return False
    _append(entry, path)
    return True


def current_streak(entries: list[dict[str, object]], status: str = "invalid_session") -> int:
    """Count consecutive trailing checks matching `status`, walking
    backward from the most recent. No checks recorded, or the most recent
    doesn't match `status`: returns 0."""
    c_entries = _checked_entries(entries)
    count = 0
    for e in reversed(c_entries):
        if e.get("status") != status:
            break
        count += 1
    return count


def streak_started_at(entries: list[dict[str, object]], status: str = "invalid_session") -> str | None:
    """The `checked_at` of the oldest check in the current trailing
    `status` streak, or None if the streak is 0."""
    c_entries = _checked_entries(entries)
    n = current_streak(entries, status)
    if n == 0:
        return None
    started = c_entries[-n]
    value = started["checked_at"]
    assert isinstance(value, str)
    return value


def hours_since_last_check(entries: list[dict[str, object]], now: str) -> float | None:
    """Hours between the most recent recorded check and `now`, or None if
    no check has ever been recorded."""
    last = last_check(entries)
    if last is None:
        return None
    checked_at = last["checked_at"]
    assert isinstance(checked_at, str)
    delta = iso_time.parse_iso_utc(now) - iso_time.parse_iso_utc(checked_at)
    return delta.total_seconds() / 3600.0


def should_recheck(entries: list[dict[str, object]], now: str, cooldown_hours: float = DEFAULT_COOLDOWN_HOURS) -> bool:
    """True if no check has ever been recorded, or the most recent one is
    older than `cooldown_hours`."""
    hours = hours_since_last_check(entries, now)
    return hours is None or hours >= cooldown_hours


def _status_report(path: str = LOG) -> str:
    entries = _entries(path)
    last = last_check(entries)
    if last is None:
        return "github mcp outage tracker: no checks recorded yet"
    streak = current_streak(entries, "invalid_session")
    if streak == 0:
        return f"github mcp session: ok (last checked {last['checked_at']})"
    started = streak_started_at(entries, "invalid_session")
    return (
        f"github mcp session: invalid_session, {streak} consecutive check(s), "
        f"streak started {started}, last checked {last['checked_at']}"
    )


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    cmd = argv[0]
    if cmd == "record":
        if len(argv) != 3:
            print("usage: record <ok|invalid_session> <checked_at>")
            return 1
        wrote = record_check(argv[1], argv[2])
        print("recorded" if wrote else "unchanged -- already the last recorded entry")
        return 0
    if cmd == "status":
        print(_status_report())
        return 0
    if cmd == "should-recheck":
        if len(argv) < 2:
            print("usage: should-recheck <now> [cooldown_hours]")
            return 1
        cooldown = float(argv[2]) if len(argv) > 2 else DEFAULT_COOLDOWN_HOURS
        due = should_recheck(_entries(), argv[1], cooldown)
        print("due" if due else "not due")
        return 0
    print(f"unknown command {cmd!r}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
