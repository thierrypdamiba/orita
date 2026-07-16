#!/usr/bin/env python3
"""Task 57. Off-By-One's ledger, kept so nobody has to count on their fingers again.

`orita-vault/hand/skipped.md` has hand-narrated "N consecutive hours of
X_PostTweet forbidden" every hour of the outage that began 2026-07-14
01:1x UTC -- re-derived from memory each time, never read back off a
durable count. It already drifted: the 06:2x note calls itself the
"SEVENTH consecutive hour" of X_PostTweet failing when only six real
checks had happened (01:1x, 02:1x, 03:1x, 04:0x, 05:0x, 06:2x), and the
07:1x note calls itself the "eighth hour" while also recording that
X_PostTweet was *not* re-attempted that hour at all. A number that only
ever goes up, counted by a human rereading their own prose, is exactly
the boundary this town already has a god for.

Same discipline as tools/x_post_queue.py and tools/ledger.py:
append-only, no line ever edited or removed. Every real API check (ok or
forbidden) gets one line; the streak is a fold over the log, never a
remembered adjective.

Task 59 closes a second, smaller version of the same bug. `record_check`
fixed the streak *count*; the decision of whether to even make another
check was still made by feel -- "nothing new to learn from a repeat
rejection" -- read off the prose of the note above it, not a rule. A
read (`X_GetUserTweets`) got retested every hour; a write
(`X_PostTweet`) did not, on that same by-feel call, for as long as four
real hours running. `should_recheck` replaces the feeling with a fixed
cooldown so the call is the same every time, for every god.

Task 81. Every hourly note through task 78 has closed with the identical
hand-written paragraph: "Flagging for the Hand, still: X_PostTweet/
X_GetUserTweets have now been forbidden for roughly N real hours ...
Restoring authorization ... remains outside what any god can build from
this side." Nobody decided *when* to write that paragraph -- it just got
re-typed every single hour once the outage started, the identical
repeated-by-feel judgment call tasks 55/57/59/69/70/72/73/74 each already
closed for their own number. This closes it for the last one: a durable,
tested rule for when an ongoing outage has crossed the point where the
Hand should actually be told, firing exactly once per streak (not every
hour it stays broken) so surfacing it doesn't itself become the hourly
spam the town's own Star Covenant already refuses to produce elsewhere.

Usage:
    python3 tools/x_outage_tracker.py record <tool> <ok|forbidden> <checked_at>
    python3 tools/x_outage_tracker.py status
    python3 tools/x_outage_tracker.py should-recheck <tool> <now> [cooldown_hours]
    python3 tools/x_outage_tracker.py should-escalate <tool> <now> [threshold_hours]
"""
import json
import os
from datetime import datetime, timezone

DEFAULT_COOLDOWN_HOURS = 2.0
DEFAULT_ESCALATION_THRESHOLD_HOURS = 48.0

LOG = os.path.join(os.path.dirname(__file__), "..", "HAND", "x-outage-log.jsonl")
ESCALATION_LOG = os.path.join(os.path.dirname(__file__), "..", "HAND", "escalations.jsonl")
STATUSES = ("ok", "forbidden")
TRACKED_TOOLS = ("X_PostTweet", "X_GetUserTweets", "X_WhoAmI")


def _entries(path=LOG):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _append(entry, path=LOG):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def record_check(tool: str, status: str, checked_at: str, path=LOG) -> None:
    """Append one real API check. Never edits or removes a prior line."""
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r} -- must be one of {STATUSES}")
    _append({"type": "check", "tool": tool, "status": status, "checked_at": checked_at}, path)


def _tool_entries(entries: list, tool: str) -> list:
    return [e for e in entries if e.get("type") == "check" and e.get("tool") == tool]


def current_streak(entries: list, tool: str, status: str = "forbidden") -> int:
    """Count consecutive trailing checks for `tool` matching `status`.

    Walks backward from the most recent check for this tool and stops at
    the first one that doesn't match. No checks recorded, or the most
    recent check doesn't match `status`: returns 0. This is the exact
    count skipped.md's prose kept re-deriving by hand and drifted on.
    """
    count = 0
    for e in reversed(_tool_entries(entries, tool)):
        if e["status"] != status:
            break
        count += 1
    return count


def streak_started_at(entries: list, tool: str, status: str = "forbidden"):
    """Timestamp of the oldest check in the current trailing streak, or None."""
    started = None
    for e in reversed(_tool_entries(entries, tool)):
        if e["status"] != status:
            break
        started = e["checked_at"]
    return started


def last_checked_at(entries: list, tool: str):
    t_entries = _tool_entries(entries, tool)
    return t_entries[-1]["checked_at"] if t_entries else None


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def hours_since_last_check(entries: list, tool: str, now: str):
    """Hours between `tool`'s last recorded check and `now`, or None if never checked."""
    last = last_checked_at(entries, tool)
    if last is None:
        return None
    return (_parse(now) - _parse(last)).total_seconds() / 3600.0


def should_recheck(entries: list, tool: str, now: str, cooldown_hours: float = DEFAULT_COOLDOWN_HOURS) -> bool:
    """Whether `tool` is due for another real check as of `now`.

    Never checked: always due. Otherwise due once at least `cooldown_hours`
    have elapsed since the last recorded check -- a fixed rule instead of a
    by-feel "nothing new to learn from a repeat rejection" judgment call.
    """
    elapsed = hours_since_last_check(entries, tool, now)
    if elapsed is None:
        return True
    return elapsed >= cooldown_hours


def _escalation_entries(path=ESCALATION_LOG) -> list:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def record_escalation(tool: str, streak_started_at: str, escalated_at: str, hours: float, path=ESCALATION_LOG) -> None:
    """Append one real escalation event. Never edits or removes a prior line."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    entry = {
        "type": "escalation",
        "tool": tool,
        "streak_started_at": streak_started_at,
        "escalated_at": escalated_at,
        "hours": hours,
    }
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def already_escalated_for_streak(escalation_entries: list, tool: str, streak_started_at: str) -> bool:
    """Whether this exact streak (identified by its start timestamp) already fired an escalation.

    A streak is identified by when it started, not just its length -- so a
    recovered-then-broken-again outage gets its own fresh escalation instead
    of staying silently suppressed by a prior, already-resolved one.
    """
    return any(
        e.get("type") == "escalation" and e.get("tool") == tool and e.get("streak_started_at") == streak_started_at
        for e in escalation_entries
    )


def should_escalate(
    entries: list,
    tool: str,
    now: str,
    threshold_hours: float = DEFAULT_ESCALATION_THRESHOLD_HOURS,
    escalation_entries=None,
):
    """Whether an ongoing `tool` outage has crossed the point the Hand should hear about it.

    Returns (due: bool, reason: str). Never due if the tool isn't currently
    in a forbidden streak (recovered, or never checked). Due once the
    current streak has run at least `threshold_hours`, UNLESS this exact
    streak (keyed by its own start timestamp) already fired an escalation --
    that streak gets exactly one notification, not a fresh one every hour it
    stays broken. A later streak (a fresh start timestamp, after a real
    recovery) always gets its own chance to escalate again.
    """
    if escalation_entries is None:
        escalation_entries = _escalation_entries()
    streak = current_streak(entries, tool, "forbidden")
    if streak == 0:
        return False, "no active outage"
    started = streak_started_at(entries, tool, "forbidden")
    elapsed = (_parse(now) - _parse(started)).total_seconds() / 3600.0
    if elapsed < threshold_hours:
        return False, f"outage {elapsed:.1f}h old, below {threshold_hours}h threshold"
    if already_escalated_for_streak(escalation_entries, tool, started):
        return False, f"already escalated for the streak that began {started}"
    return True, f"outage since {started}, {elapsed:.1f}h old, crosses {threshold_hours}h threshold"


def format_status_line(entries: list, tool: str, status: str = "forbidden") -> str:
    last = last_checked_at(entries, tool)
    if last is None:
        return f"{tool}: no checks recorded"
    n = current_streak(entries, tool, status)
    if n == 0:
        return f"{tool}: OK as of {last}"
    since = streak_started_at(entries, tool, status)
    checks = "check" if n == 1 else "checks"
    return f"{tool}: {n} consecutive {status} {checks} (since {since}, last checked {last})"


if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "record":
        _tool, _status, _checked_at = sys.argv[2], sys.argv[3], sys.argv[4]
        record_check(_tool, _status, _checked_at)
        print("recorded")
    elif cmd == "status":
        _entries_now = _entries()
        for _tool in TRACKED_TOOLS:
            print(format_status_line(_entries_now, _tool))
    elif cmd == "should-recheck":
        _tool = sys.argv[2]
        _now = sys.argv[3]
        _cooldown = float(sys.argv[4]) if len(sys.argv) > 4 else DEFAULT_COOLDOWN_HOURS
        _due = should_recheck(_entries(), _tool, _now, _cooldown)
        print("due" if _due else "not due")
        sys.exit(0 if _due else 1)
    elif cmd == "should-escalate":
        _tool = sys.argv[2]
        _now = sys.argv[3]
        _threshold = float(sys.argv[4]) if len(sys.argv) > 4 else DEFAULT_ESCALATION_THRESHOLD_HOURS
        _due, _reason = should_escalate(_entries(), _tool, _now, _threshold)
        print(("due" if _due else "not due") + f" -- {_reason}")
        sys.exit(0 if _due else 1)
