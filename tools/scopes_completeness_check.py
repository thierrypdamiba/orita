#!/usr/bin/env python3
"""Task 135. Ogun closes the gap in his own Oath's table.

`fencepost/SCOPES.md`'s Read-Only Oath table names the four toolkits
Fencepost's own code uses. It said nothing about the other apps
`tools/arcade_app_watch.py`'s durable log (task 122) has recorded connected
on the-hand's shared gateway -- two of them, `arcade-linear` and
`arcade-slack`, write-capable. An Oath that only accounts for what it uses
and stays silent on what else the shared gateway can already reach is not
the complete account of risk surface STRATEGY.md's own standing law
demands. Task 135 added a `## Every connected app, accounted for` section
naming every app_id the log knows, by status. This module keeps that
section honest going forward: a newly connected app that never gets added
to the table is a real governance gap, the same class of quiet miss
Fencepost itself exists to catch.

Same discipline as `wip_reclaim_check.py`/`ritual_completeness_check.py`:
local-filesystem-only, no network call of its own. Reads
`arcade_app_watch.py`'s own last recorded `connected_app_ids` (never a
live `Arcade_ListApps` call) and `fencepost/SCOPES.md`'s own text.

Usage:
    python3 tools/scopes_completeness_check.py check
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arcade_app_watch  # noqa: E402
import gateway_toolset_check  # noqa: E402
import text_patterns  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SCOPES_PATH = os.path.join(ROOT, "fencepost", "SCOPES.md")
DEFAULT_APP_LOG_PATH = os.path.join(ROOT, "HAND", "arcade-app-check-log.jsonl")
DEFAULT_TOOLSET_LOG_PATH = gateway_toolset_check.LOG

_SECTION_HEADER = re.compile(r"^## Every connected app, accounted for\s*$", re.MULTILINE)
_TABLE_ROW_APP_ID = re.compile(r"^\|\s*`([^`]+)`", re.MULTILINE)
_TABLE_ROW_STATUS = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*([^|\n]+?)\s*\|\s*$", re.MULTILINE)

# The one status phrasing that must never appear next to arcade-google while
# zero Gmail/Calendar tools are actually live on the gateway -- the exact
# stale claim task 541 found and named but didn't fix (not its remit).
_IN_USE_CLAIM = "in use by fencepost"


def _section(scopes_text: str) -> str:
    """The `## Every connected app, accounted for` section's body text, or
    "" if the section itself is missing. Delegates to `text_patterns.
    bounded_section` (task 552), the shared read this file's own logic was
    the first of three to hand-write."""
    return text_patterns.bounded_section(scopes_text, _SECTION_HEADER)


def _accounted_for_app_ids(scopes_text: str) -> set:
    """Every app_id named in a `| `app_id`... |` table row inside the
    `## Every connected app, accounted for` section, structurally --
    never a hardcoded list of expected ids. Returns an empty set if the
    section itself is missing (a real gap, not silently treated as
    vacuously accounted-for)."""
    return {m.group(1) for m in _TABLE_ROW_APP_ID.finditer(_section(scopes_text))}


def _row_status(scopes_text: str, app_id: str) -> str | None:
    """The status text of the named app_id's row in the accounted-for
    section, or None if that row doesn't exist."""
    for m in _TABLE_ROW_STATUS.finditer(_section(scopes_text)):
        if m.group(1) == app_id:
            return m.group(2)
    return None


def _last_connected_app_ids(app_log_path: str) -> list:
    """The most recently recorded `connected_app_ids` list, read through
    `arcade_app_watch.py`'s own guarded `last_app_state()` rather than a
    second, unguarded parse of the same file. A malformed last line
    raises `arcade_app_watch.ArcadeAppWatchTamperedError` -- the same
    refuse-to-guess-past-a-corrupted-tip guarantee every other reader of
    this log already gets -- instead of an uncaught
    `json.JSONDecodeError`. Empty list if the log has never been
    written -- nothing connected is not an error."""
    state = arcade_app_watch.last_app_state(path=app_log_path)
    if state is None:
        return []
    return state.get("connected_app_ids", [])


def _google_row_is_stale(scopes_text: str, toolset_log_path: str) -> bool:
    """True when `arcade-google`'s row claims "in use by Fencepost" while
    the last recorded live gateway-toolset check (task 464) shows zero
    Gmail/Calendar-capable tools actually exposed. A malformed toolset log
    tip is treated as "cannot confirm staleness" (False), the same
    cannot-confirm-past-a-corrupted-tip stance `_last_connected_app_ids`
    takes on its own log; no toolset check ever recorded is likewise not
    an error here -- silence is not a lie, only a claim would be."""
    try:
        toolset_state = gateway_toolset_check.last_toolset_state(toolset_log_path)
    except gateway_toolset_check.GatewayToolsetCheckTamperedError:
        return False
    if toolset_state is None or toolset_state.get("has_gmail_calendar_tools"):
        return False
    status = _row_status(scopes_text, "arcade-google")
    return status is not None and _IN_USE_CLAIM in status.lower()


def check_scopes_completeness(
    scopes_path: str = DEFAULT_SCOPES_PATH,
    app_log_path: str = DEFAULT_APP_LOG_PATH,
    toolset_log_path: str = DEFAULT_TOOLSET_LOG_PATH,
) -> dict:
    """Cross-check every currently-connected real app_id against
    `fencepost/SCOPES.md`'s own `## Every connected app, accounted for`
    section. Returns `clean: True` with the accounted-for set when every
    connected app_id is named AND no row's status text outruns what's
    actually live (task 542: the table naming an app_id was never the
    whole claim -- what it says about that app_id can go stale too);
    otherwise `clean: False`, the specific missing ids, and whether the
    `arcade-google` row's own claim is stale -- never a pass/fail without
    saying which specific thing is wrong."""
    with open(scopes_path, encoding="utf-8") as f:
        scopes_text = f.read()
    accounted = _accounted_for_app_ids(scopes_text)
    connected = _last_connected_app_ids(app_log_path)
    missing = sorted(set(connected) - accounted)
    stale_google_claim = _google_row_is_stale(scopes_text, toolset_log_path)
    return {
        "clean": not missing and not stale_google_claim,
        "connected_app_ids": sorted(connected),
        "accounted_for_app_ids": sorted(accounted),
        "missing": missing,
        "stale_google_claim": stale_google_claim,
    }


def format_result(result: dict) -> str:
    if result["stale_google_claim"]:
        return (
            "scopes completeness: BROKEN -- stale arcade-google claim: row says "
            "\"in use by Fencepost\" but the last recorded gateway-toolset check "
            "found zero Gmail/Calendar tools live"
        )
    if not result["connected_app_ids"]:
        return "scopes completeness: clean (no apps recorded as connected)"
    if result["clean"]:
        return f"scopes completeness: clean ({len(result['connected_app_ids'])} connected app(s), all accounted for)"
    return f"scopes completeness: BROKEN -- undocumented connected app(s): {', '.join(result['missing'])}"


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = check_scopes_completeness()
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
