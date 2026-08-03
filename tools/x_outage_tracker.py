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

Task 92. Task 81's "exactly once per streak" discipline has a real gap
live on the town's own current outage: `X_PostTweet` crossed the 48h
threshold on 2026-07-16T07:05:00Z, fired its one escalation, and every
hour since has correctly read "already escalated for the streak" --
which is right at 50 hours, and will still say the identical thing at
500 hours, because the suppression key was ever only (tool,
streak_started_at), with no notion that a week-old outage is a
materially different severity than a two-day-old one. `already_
escalated_for_streak`/`record_escalation` now key on (tool,
streak_started_at, threshold_hours) instead, so a fresh, higher tier
can still fire even after a lower one already has -- an entry recorded
before this task (no `threshold_hours` field) reads back as the 48.0h
tier, its only tier, so the real live escalation task 81 already sent
keeps suppressing exactly the 48h tier it always did. `next_escalation_
tier` walks `ESCALATION_TIERS` from most to least severe and returns
the single worst crossed-and-unfired tier, so a long-stuck outage gets
told once more at each real severity step instead of going silent
forever after its first notice.

Task 422. `next_escalation_tier`'s own docstring already named the shape
this closes: "a long-stuck outage gets told once more at each real
severity step instead of going silent forever after its first notice" --
true only while the outage stays under `ESCALATION_TIERS`' own highest
value. `hand/skipped.md`'s 2026-07-27 entry named the real gap directly:
both defined tiers (48h, 168h) had long since fired on the town's own
live `X_PostTweet`/`X_GetUserTweets` outage (started 2026-07-14) and
"nothing higher will ever fire on its own no matter how long this runs"
-- and forty-plus BUILDLOG.md hours since have each correctly logged "no
new escalation tier" and moved on, which reads identically whether the
outage is one week old or one year old. `ESCALATION_TIERS` is a finite
tuple; `next_escalation_tier` only ever walked it. `RECURRING_ESCALATION_
INTERVAL_HOURS` and `_extended_tiers` fix the actual top: once an outage
runs past the highest named tier, one new tier is generated every
`RECURRING_ESCALATION_INTERVAL_HOURS` (the same one-week cadence the
168h tier already set) for as long as the outage keeps running, so a
months-long outage still earns a fresh, real, never-before-fired
escalation on a fixed weekly cadence instead of going silent forever
after its second notice. `already_escalated_for_streak`'s existing
(tool, streak_started_at, threshold_hours) key needs no change -- a
generated tier is just one more real number in that same space.

Usage:
    python3 tools/x_outage_tracker.py record <tool> <ok|forbidden> <checked_at>
    python3 tools/x_outage_tracker.py status
    python3 tools/x_outage_tracker.py should-recheck <tool> <now> [cooldown_hours]
    python3 tools/x_outage_tracker.py should-escalate <tool> <now> [threshold_hours]
    python3 tools/x_outage_tracker.py next-tier <tool> <now>
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iso_time  # noqa: E402
import jsonl_append  # noqa: E402

DEFAULT_COOLDOWN_HOURS = 2.0
DEFAULT_ESCALATION_THRESHOLD_HOURS = 48.0
ESCALATION_TIERS = (48.0, 168.0)
RECURRING_ESCALATION_INTERVAL_HOURS = 168.0

LOG = os.path.join(os.path.dirname(__file__), "..", "HAND", "x-outage-log.jsonl")
ESCALATION_LOG = os.path.join(os.path.dirname(__file__), "..", "HAND", "escalations.jsonl")
STATUSES = ("ok", "forbidden")
TRACKED_TOOLS = ("X_PostTweet", "X_GetUserTweets", "X_WhoAmI")


class XOutageTrackerTamperedError(RuntimeError):
    """Raised when a tool-filtered read (current_streak/streak_started_at/
    last_checked_at/hours_since_last_check/should_recheck), or an
    escalation-history read (already_escalated_for_streak/should_escalate/
    next_escalation_tier), finds a malformed line anywhere in its log.
    Mirrors tools/ci_watch.py's CIWatchTamperedError and
    tools/voice_window_check.py's VoiceWindowTamperedError (task 246): a
    malformed check-log line has lost its "type"/"tool" fields, so
    _tool_entries' filter would silently drop it from EVERY tool's view
    rather than just the one it really belonged to -- guessing which tool's
    streak it was could stitch two real entries together that shouldn't be
    adjacent, silently shortening or lengthening a reported outage streak
    (and, downstream, should_escalate's threshold math). A malformed
    escalation-log line loses its "tool"/"streak_started_at"/
    "threshold_hours" fields the same way, so already_escalated_for_streak
    would silently treat it as a non-match instead of an unreadable prior
    escalation it can't rule out -- risking a duplicate notification for a
    tier that already fired. Refuse rather than guess, the same discipline
    tasks 238-245 already applied to their own logs. Run this tool's
    `status` command by hand to see the break, then repair the log before
    the next real check/record."""


def _entries(path=LOG):
    """Every line in the X-outage check log, parsed.

    A line that is not even valid JSON any more (a bad hand-edit, a stray
    merge-conflict marker, a truncated write) is not allowed to crash the
    caller with an uncaught json.JSONDecodeError -- it comes back marked
    {"_malformed": True, "_error": ...} instead, the same convention
    tools/ledger.py's _entries() uses (mirrored since in change_gate.py,
    x_post_queue.py, word_watch.py, consent_grant_log.py, ci_watch.py,
    scribe_growth_check.py, voice_window_check.py, square_check.py). A
    line that parses cleanly but isn't a JSON object (a bare number, null,
    list, or stray string) gets the same treatment -- otherwise it comes
    back as e.g. a bare int, and _tool_entries()'s e.get("_malformed")
    crashes with an uncaught AttributeError instead of the named
    XOutageTrackerTamperedError this module already promises.
    """
    if not os.path.exists(path):
        return []
    entries = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as exc:
                entries.append({"_malformed": True, "_error": str(exc)})
                continue
            if not isinstance(parsed, dict):
                entries.append(
                    {"_malformed": True, "_error": f"not a JSON object: {parsed!r}"}
                )
                continue
            entries.append(parsed)
    return entries


# Task 510: consolidated into tools/jsonl_append.py -- ten sibling checks
# each carried a byte-identical copy of this helper. This name now points
# at the shared function object, not a local copy; tests/test_jsonl_
# append.py asserts this name IS that shared function.
_append = jsonl_append.append_jsonl


def last_check(entries: list, tool: str):
    """The most recently recorded real check for `tool`, or None."""
    t_entries = _tool_entries(entries, tool)
    return t_entries[-1] if t_entries else None


def record_check(tool: str, status: str, checked_at: str, path=LOG) -> bool:
    """Append one real API check. Never edits or removes a prior line.

    Task 503: the one `record_*` sibling task 501 named live and explicitly
    left unfixed ("no demonstrated bug there") -- but `HAND/x-outage-log.jsonl`
    grew the same way `HAND/ci-watch-log.jsonl` did before task 501: two
    `ritual_check.py` invocations feeding this function the exact same
    already-recorded observation a second time (a retry, an addendum call
    re-reading the same live state) produce byte-identical lines. This is
    `ci_watch.record_check`'s narrower guard (task 501), not
    `record_square_check`/`record_scribe_check`/`record_word_check`'s
    "skip if the durable STATE is unchanged" dedup (tasks 487/497/498):
    `current_streak` REQUIRES that two genuinely separate real checks
    landing on the same status at two different real moments both count
    (a five-hour outage streak is five recorded lines, not one) -- so this
    only refuses the exact resubmission of an already-recorded moment
    (`checked_at` matching too, not just tool/status), never a real new
    observation that merely repeats the same status. Returns True if a
    line was written, False if this exact entry was already the last one
    recorded for this tool -- the one real caller (a god on duty running a
    due recheck) does not depend on the return value today, so this is not
    a breaking change to anything that calls it live.
    """
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r} -- must be one of {STATUSES}")
    entry = {"type": "check", "tool": tool, "status": status, "checked_at": checked_at}
    # A malformed line ANYWHERE in the log is "cannot confirm a duplicate,"
    # not a reason to refuse writing -- recording must still be able to
    # repair a corrupted log by appending a fresh valid line, the identical
    # discipline record_square_check/ci_watch.record_check's own write
    # paths hold: only *reading* refuses to guess past a bad line.
    try:
        last = last_check(_entries(path), tool)
    except XOutageTrackerTamperedError:
        last = None
    if last is not None and last == entry:
        return False
    _append(entry, path)
    return True


def _tool_entries(entries: list, tool: str) -> list:
    for e in entries:
        if e.get("_malformed"):
            raise XOutageTrackerTamperedError(
                f"_tool_entries({tool!r}): the log holds a line that is not "
                f"valid JSON ({e.get('_error')}) -- refusing to guess which "
                "tool it belonged to. Repair the log by hand, then rerun."
            )
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


# Task 509: consolidated into tools/iso_time.py -- three sibling checks
# (cron_health.py, voice_window_check.py, x_outage_tracker.py) each
# carried a byte-identical copy of this parser. This name now points at
# the shared function object, not a local copy; tests/test_iso_time.py
# asserts this name IS that shared function.
_parse = iso_time.parse_iso_utc


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
    """Every line in the escalation log, parsed.

    Same convention as _entries() above: an unparseable line, or one that
    parses cleanly but isn't a JSON object, comes back marked
    {"_malformed": True, "_error": ...} instead of raising or being handed
    to already_escalated_for_streak()'s e.get("_malformed") as a bare
    non-dict value (which would crash with an uncaught AttributeError).
    """
    if not os.path.exists(path):
        return []
    entries = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as exc:
                entries.append({"_malformed": True, "_error": str(exc)})
                continue
            if not isinstance(parsed, dict):
                entries.append(
                    {"_malformed": True, "_error": f"not a JSON object: {parsed!r}"}
                )
                continue
            entries.append(parsed)
    return entries


def record_escalation(
    tool: str,
    streak_started_at: str,
    escalated_at: str,
    hours: float,
    threshold_hours: float = DEFAULT_ESCALATION_THRESHOLD_HOURS,
    path=ESCALATION_LOG,
) -> None:
    """Append one real escalation event. Never edits or removes a prior line.

    `threshold_hours` names which tier this escalation fired at (task 92) --
    a caller that omits it (every call site before task 92) records the
    48.0h tier, matching the only tier that ever existed before this.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    entry = {
        "type": "escalation",
        "tool": tool,
        "streak_started_at": streak_started_at,
        "escalated_at": escalated_at,
        "hours": hours,
        "threshold_hours": threshold_hours,
    }
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def already_escalated_for_streak(
    escalation_entries: list,
    tool: str,
    streak_started_at: str,
    threshold_hours: float = DEFAULT_ESCALATION_THRESHOLD_HOURS,
) -> bool:
    """Whether this exact streak already fired an escalation AT THIS TIER.

    A streak is identified by when it started, not just its length -- so a
    recovered-then-broken-again outage gets its own fresh escalation instead
    of staying silently suppressed by a prior, already-resolved one. Task 92:
    keyed on (tool, streak_started_at, threshold_hours) rather than just
    (tool, streak_started_at), so a streak that already fired its 48h notice
    can still earn a fresh, more severe notice once it crosses a higher
    tier -- an entry recorded before this task (no `threshold_hours` field)
    reads back as the 48.0h tier, its only tier at the time.
    """
    for e in escalation_entries:
        if e.get("_malformed"):
            raise XOutageTrackerTamperedError(
                f"already_escalated_for_streak({tool!r}): the escalation log "
                f"holds a line that is not valid JSON ({e.get('_error')}) -- "
                "refusing to guess whether this tier already fired. Repair "
                "the log by hand, then rerun."
            )
    return any(
        e.get("type") == "escalation"
        and e.get("tool") == tool
        and e.get("streak_started_at") == streak_started_at
        and e.get("threshold_hours", DEFAULT_ESCALATION_THRESHOLD_HOURS) == threshold_hours
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
    streak already fired an escalation AT THIS TIER (task 92) -- each tier
    gets exactly one notification, not a fresh one every hour it stays
    broken, but a later, more severe tier still gets its own chance even
    after an earlier tier already fired. A later streak (a fresh start
    timestamp, after a real recovery) always gets every tier's own chance
    to escalate again.
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
    if already_escalated_for_streak(escalation_entries, tool, started, threshold_hours):
        return False, f"already escalated for the streak that began {started} at the {threshold_hours}h tier"
    return True, f"outage since {started}, {elapsed:.1f}h old, crosses {threshold_hours}h threshold"


def _extended_tiers(
    elapsed_hours: float,
    tiers=ESCALATION_TIERS,
    recurring_interval: float = RECURRING_ESCALATION_INTERVAL_HOURS,
) -> tuple:
    """`tiers` extended with recurring tiers beyond its own highest value.

    `tiers` names finitely many severities; an outage does not stop
    running just because it outlived the last one (task 422). Once
    `elapsed_hours` runs past `max(tiers)`, `recurring_interval` is added
    again and again -- each new tier only counted if it does not exceed
    `elapsed_hours` -- so a real, currently-running outage always has a
    real next tier available to fire, no matter how long it has run.
    `tiers=()` (no explicit tiers at all) returns unchanged: there is
    nothing to extend past.
    """
    if not tiers:
        return tiers
    extended = set(tiers)
    threshold_hours = max(tiers) + recurring_interval
    while threshold_hours <= elapsed_hours:
        extended.add(threshold_hours)
        threshold_hours += recurring_interval
    return tuple(sorted(extended))


def next_escalation_tier(
    entries: list,
    tool: str,
    now: str,
    escalation_entries=None,
    tiers=ESCALATION_TIERS,
    recurring_interval: float = RECURRING_ESCALATION_INTERVAL_HOURS,
):
    """The single worst crossed-and-unfired escalation tier for `tool`, or None.

    Walks `tiers` (extended past its own top by `_extended_tiers`, task
    422, using this outage's own real elapsed hours) from most to least
    severe so a long-stuck outage reports its highest real severity
    rather than re-surfacing a lower tier that already fired (task 92) --
    the gap task 81's single-threshold design left: an outage that fires
    its 48h notice and then just keeps running read "already escalated"
    forever after, with no way to tell the Hand it got materially worse.
    Task 92 fixed that up to `max(tiers)`; task 422 fixes it past that
    top too, so an outage that outlives every named tier still earns a
    fresh one every `recurring_interval` hours instead of going silent
    forever. Returns `(threshold_hours, reason)` for the tier that's due,
    or `None` if no tier is currently due (including: no active outage).
    """
    if escalation_entries is None:
        escalation_entries = _escalation_entries()
    effective_tiers = tiers
    streak = current_streak(entries, tool, "forbidden")
    if streak:
        started = streak_started_at(entries, tool, "forbidden")
        elapsed = (_parse(now) - _parse(started)).total_seconds() / 3600.0
        effective_tiers = _extended_tiers(elapsed, tiers, recurring_interval)
    for threshold_hours in sorted(effective_tiers, reverse=True):
        due, reason = should_escalate(entries, tool, now, threshold_hours, escalation_entries)
        if due:
            return threshold_hours, reason
    return None


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
    elif cmd == "next-tier":
        _tool = sys.argv[2]
        _now = sys.argv[3]
        _tier = next_escalation_tier(_entries(), _tool, _now)
        if _tier is None:
            print("not due")
            sys.exit(1)
        _threshold_hours, _reason = _tier
        print(f"due -- {_threshold_hours}h tier -- {_reason}")
        sys.exit(0)
