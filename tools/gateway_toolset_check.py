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

<tool_names.json> shape: {"tool_names": ["Github_ListIssues", "X_PostTweet", ...]}
-- the caller's own live enumeration of the-hand's exposed tools (e.g. a
ToolSearch/tool-list read against the mcp__the-hand__ namespace), never a
second hand-typed belief about what's connected.
"""
import json
import os
import re

LOG = os.path.join(os.path.dirname(__file__), "..", "HAND", "gateway-toolset-check-log.jsonl")

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


def compute_toolset_state(tool_names: list[str]) -> dict:
    """Fold a live the-hand tool-name list into the durable comparison shape."""
    matched = sorted(t for t in tool_names if _GMAIL_CALENDAR_PATTERN.search(t))
    return {"has_gmail_calendar_tools": bool(matched), "matched_tools": matched}


def _entries(path=LOG):
    """Same malformed-line tolerance as arcade_app_watch.py's _entries()
    (task 311's convention): a line that fails to parse, or parses to
    something other than a dict, is marked {"_malformed": True, ...}
    instead of crashing the caller."""
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
                entries.append({
                    "_malformed": True,
                    "_error": f"parsed to {type(parsed).__name__}, not an object",
                })
                continue
            entries.append(parsed)
    return entries


def _append(entry, path=LOG):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def last_toolset_state(path=LOG):
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


def record_toolset_check(state: dict, checked_at: str, path=LOG) -> None:
    """Append one real observed gateway toolset state. Never edits or removes a prior line."""
    entry = dict(state)
    entry["checked_at"] = checked_at
    _append(entry, path)


def toolset_delta(state: dict, path=LOG):
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


class GatewayToolsetCheckArgError(ValueError):
    """<tool_names.json> parsed as valid JSON but not into a dict. Mirrors
    arcade_app_watch.py's ArcadeAppWatchArgError."""


def _load_tool_names_json(path: str) -> dict:
    with open(path) as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise GatewayToolsetCheckArgError(
            f"{path}: expected a JSON dict, got {type(raw).__name__}"
        )
    return raw


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, tools_path = argv[1], argv[2]
    raw = _load_tool_names_json(tools_path)
    state = compute_toolset_state(raw.get("tool_names", []))
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
