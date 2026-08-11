#!/usr/bin/env python3
"""Task 464. `fencepost/SCOPES.md`'s WIP note (task 122, corrected once
already at 2026-07-18T03:1x UTC) makes a live, checkable claim: "zero
Gmail/Calendar-capable tools exposed anywhere in the-hand's live MCP
toolset." That claim was true the hour it was written, but nothing has
ever recorded WHEN it was last actually re-verified, or checked whether it
had gone stale -- the exact recalled-not-recorded shape task 122's own
docstring already named as recurring (`x_outage_tracker.py`,
`square_check.py`, `word_watch.py`, the escalation-tier suppression key,
`arcade_app_watch.py` itself). `arcade_app_watch.py` durably tracks WHICH
apps are connected on the-hand gateway; it says nothing about which TOOLS
the gateway actually exposes for an already-connected app -- Google has
been connected since task 122 with Gmail/Calendar scopes granted upstream,
but SCOPES.md is explicit that a scope grant upstream is not the same as a
callable tool on the gateway a caller can reach. This module closes that
gap for the tool-exposure claim specifically: given this hour's live list
of the-hand's own tool names (the caller already holds it -- same
"caller-supplied state, no network call of its own" discipline
`square_check.py`/`arcade_app_watch.py` both hold), record whether any
Gmail/Calendar-capable tool is present, and report how long it's been
since the claim was last actually re-checked.

Usage:
    python3 tools/gateway_toolset_check.py check <tool_names.json>
    python3 tools/gateway_toolset_check.py record <tool_names.json> <checked_at>
    python3 tools/gateway_toolset_check.py freshness

`freshness` is task 669's own answer to this docstring's last sentence
above ("report how long it's been since the claim was last actually
re-checked") -- written at task 464's founding but never actually
implemented until this log itself sat stale for nine days, unnoticed,
before task 669 found it. Needs no <tool_names.json>: it reads only this
log's own last entry and reports elapsed time, never a live tool list.

<tool_names.json> shape: {"tool_names": ["Github_ListIssues", "X_PostTweet", ...]}
-- the caller's own live enumeration of the-hand's exposed tools (e.g. a
ToolSearch/tool-list read against the mcp__the-hand__ namespace), never a
second hand-typed belief about what's connected.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import TypedDict, cast

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jsonl_append  # noqa: E402
import jsonl_read  # noqa: E402

LOG = os.path.join(os.path.dirname(__file__), "..", "HAND", "gateway-toolset-check-log.jsonl")


class ToolsetState(TypedDict):
    """`compute_toolset_state()`'s own return shape: whether any
    Gmail/Calendar-capable tool is present on the-hand's live toolset, and
    which tool names matched."""

    has_gmail_calendar_tools: bool
    matched_tools: list[str]

# Mirrors fencepost/SCOPES.md's own v0.2 table: the read-only Gmail/Calendar
# tool names Fencepost would call once the gateway exposes them
# (ListEmails, GetEmail, SearchThreads, ListEvents, GetEvent). Matched
# case-insensitively against live tool names so a provider-prefix rename
# ("Gmail_ListEmails" vs "Google_ListEmails") still trips it -- the point is
# "does ANY gmail/calendar-shaped tool exist yet", not an exact-name pin.
_GMAIL_CALENDAR_PATTERN = re.compile(r"gmail|calendar", re.IGNORECASE)


class GatewayToolsetCheckTamperedError(RuntimeError):
    """Raised by last_toolset_state() when the log's most recent line is
    not valid JSON. Mirrors arcade_app_watch.py's
    ArcadeAppWatchTamperedError: this only ever reads the log's most recent
    line, so skipping a corrupted tip and falling back to an older valid
    entry would silently misreport this hour's real delta against a stale
    snapshot instead of the true last one. Repair the log by hand, then
    rerun."""


def compute_toolset_state(tool_names: list[str]) -> ToolsetState:
    """Fold a live the-hand tool-name list into the durable comparison shape."""
    matched = sorted(t for t in tool_names if _GMAIL_CALENDAR_PATTERN.search(t))
    return {"has_gmail_calendar_tools": bool(matched), "matched_tools": matched}


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


def last_toolset_state(path: str = LOG) -> dict[str, object] | None:
    """The most recently recorded real gateway-toolset check, or None.

    Raises GatewayToolsetCheckTamperedError if the log's last line isn't
    valid JSON -- toolset_delta must never guess past a corrupted tip."""
    entries = _entries(path)
    if not entries:
        return None
    if entries[-1].get("_malformed"):
        raise GatewayToolsetCheckTamperedError(
            f"last_toolset_state(): the most recent line in {path} is not "
            f"valid JSON ({entries[-1]['_error']}) -- refusing to guess "
            "this hour's real delta against a stale snapshot. Repair the "
            "log by hand, then rerun."
        )
    return entries[-1]


def record_toolset_check(state: ToolsetState, checked_at: str, path: str = LOG) -> bool:
    """Append one real observed gateway toolset state. Never edits or removes a prior line.

    Task 498: skips the append -- returns False, writes nothing -- when
    `has_gmail_calendar_tools`/`matched_tools` are identical to the most
    recently recorded entry, mirroring `arcade_app_watch.record_app_check`'s
    identical fix (same task) for this file's own sibling log. Returns True
    when a new line was actually written (the first-ever check, or a real
    exposure change since the last one). A malformed tip is treated as
    "cannot confirm a duplicate" rather than propagated -- recording must
    still be able to repair a corrupted log by appending a fresh valid
    line.
    """
    try:
        last = last_toolset_state(path)
    except GatewayToolsetCheckTamperedError:
        last = None

    if last is not None and (
        bool(last.get("has_gmail_calendar_tools")) == state["has_gmail_calendar_tools"]
        and last.get("matched_tools") == state["matched_tools"]
    ):
        return False

    entry: dict[str, object] = dict(state)
    entry["checked_at"] = checked_at
    _append(entry, path)
    return True


def toolset_delta(state: ToolsetState, path: str = LOG) -> tuple[bool, str]:
    """Whether this hour's live toolset read differs from the last
    recorded check. Returns (changed: bool, reason: str).

    No prior check recorded: changed (first check). Gmail/Calendar tools
    newly present (False -> True): changed -- this is the real milestone
    event, SCOPES.md's v0.2 gate flipping open. Gmail/Calendar tools newly
    absent (True -> False, a gateway regression): changed. Otherwise:
    unchanged, naming the current zero/nonzero state."""
    last = last_toolset_state(path)
    if last is None:
        matched = ", ".join(state["matched_tools"]) or "(none)"
        return True, f"no prior toolset check recorded -- due, matched: {matched}"

    prev_present = bool(last.get("has_gmail_calendar_tools"))
    curr_present = state["has_gmail_calendar_tools"]
    if prev_present != curr_present:
        matched = ", ".join(state["matched_tools"]) or "(none)"
        return True, (
            f"gmail/calendar tool exposure changed: {prev_present} -> {curr_present} "
            f"(matched: {matched})"
        )

    if curr_present:
        return False, f"unchanged, still exposed: {', '.join(state['matched_tools'])}"
    return False, "unchanged, still zero gmail/calendar-capable tools on the-hand gateway"


# Task 669: `toolset_delta`/`record_toolset_check` above only ever run when
# some hourly session happens to hand this module a live tool-name list --
# unlike `records/metrics.jsonl`'s daily aggregate or `ci_watch.py`'s own
# cron-driven cadence, nothing enforces that this happens on any regular
# beat. The result was invisible until checked by hand: this log's last
# real entry sat at 2026-08-02T09:10:44Z for nine days (confirmed live this
# hour, task 669) before anyone noticed, because `ritual_check.py`'s own
# printed block only ever showed a `gateway_toolset` line when a caller
# actively passed `--gateway-toolset` -- silence read identical to "checked
# recently, nothing new" from the outside. `ci_watch.py`'s own sibling
# staleness (task 467's `run_id` bug aside) was caught the same way, by
# hand, one hour earlier (task 667) -- this closes the durable version of
# that same gap for the toolset log specifically, so a fresh session's own
# live `ritual_check.py` run surfaces it without anyone having to remember
# to look.
STALE_AFTER_DAYS = 7.0


class ToolsetFreshness(TypedDict):
    """`compute_toolset_freshness()`'s own return shape."""

    status: str  # "never" | "fresh" | "stale"
    days_since: float | None
    checked_at: str | None
    reason: str | None


def compute_toolset_freshness(now: datetime, path: str = LOG) -> ToolsetFreshness:
    """How long since this log last carried a REAL recorded check, keyed on
    elapsed time rather than a calendar date -- unlike a daily report or a
    daily metrics aggregate, this log has no fixed "expected reading for
    today," so `check_report_freshness`/`compute_metrics_freshness`'s own
    current/pending/stale-by-date shape does not fit. Three states instead:
    "never" (the log is empty -- no check has ever been recorded), "fresh"
    (the last entry is within `STALE_AFTER_DAYS`), "stale" (older than
    that, or the log's own tip is malformed and its true freshness cannot
    be trusted). Read-only: makes no network call and writes nothing,
    mirroring `check_badge_freshness`'s own live-recompute-vs-committed-
    state split -- freshness is a fact ABOUT the log, not a new entry in
    it."""
    try:
        last = last_toolset_state(path)
    except GatewayToolsetCheckTamperedError:
        return {
            "status": "stale",
            "days_since": None,
            "checked_at": None,
            "reason": "the log's own tip is malformed -- last real freshness cannot be trusted",
        }
    if last is None:
        return {
            "status": "never",
            "days_since": None,
            "checked_at": None,
            "reason": "no gateway-toolset check has ever been recorded",
        }
    checked_at_raw = cast(str, last["checked_at"])
    checked_at = datetime.fromisoformat(checked_at_raw.replace("Z", "+00:00"))
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    now_utc = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    days_since = (now_utc.astimezone(timezone.utc) - checked_at.astimezone(timezone.utc)).total_seconds() / 86400.0
    status = "fresh" if days_since <= STALE_AFTER_DAYS else "stale"
    return {"status": status, "days_since": round(days_since, 1), "checked_at": checked_at_raw, "reason": None}


def format_toolset_freshness(result: ToolsetFreshness) -> str:
    if result["status"] == "never":
        return "gateway toolset freshness: NEVER CHECKED -- no gateway-toolset check has ever been recorded"
    if result["status"] == "fresh":
        return f"gateway toolset freshness: fresh (last checked {result['days_since']}d ago, {result['checked_at']})"
    if result["checked_at"] is None:
        return f"gateway toolset freshness: STALE -- {result['reason']}"
    return (
        f"gateway toolset freshness: STALE -- last checked {result['days_since']}d ago "
        f"({result['checked_at']}), over the {STALE_AFTER_DAYS:.0f}-day bar"
    )


class GatewayToolsetCheckArgError(ValueError):
    """<tool_names.json> parsed as valid JSON but not into a dict. Mirrors
    arcade_app_watch.py's ArcadeAppWatchArgError."""


def _load_tool_names_json(path: str) -> dict[str, object]:
    with open(path) as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise GatewayToolsetCheckArgError(
            f"{path}: expected a JSON dict, got {type(raw).__name__}"
        )
    return raw


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "freshness":
        # Unlike check/record, freshness reads no live tool-name list --
        # it is a fact about the LOG's own last entry, so it needs no
        # <tool_names.json> argument at all.
        result = compute_toolset_freshness(datetime.now(timezone.utc))
        print(format_toolset_freshness(result))
        return 0
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, tools_path = argv[1], argv[2]
    raw = _load_tool_names_json(tools_path)
    state = compute_toolset_state(cast("list[str]", raw.get("tool_names", [])))
    if cmd == "check":
        changed, reason = toolset_delta(state, path=LOG)
        print(f"{'changed' if changed else 'unchanged'} -- {reason}")
        return 0
    elif cmd == "record":
        if len(argv) < 4:
            print("usage: record <tool_names.json> <checked_at>")
            return 1
        record_toolset_check(state, argv[3], path=LOG)
        print(f"recorded: {state}")
        return 0
    print(f"unknown command: {cmd!r}")
    return 1


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv))
