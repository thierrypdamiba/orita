#!/usr/bin/env python3
"""Task 135. Ogun closes the gap in his own Oath's table.

`fencepost/SCOPES.md`'s Read-Only Oath table names the six toolkits
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

Task 781 (Esu-Elegba): the sentence above used to say "four toolkits" --
true the day task 135 wrote it, stale from the moment tasks 599/600 added
Slack and Linear rows to the very table the sentence describes (six rows,
not four, ever since). Nothing had ever structurally counted that table's
own rows against the sentence's number-word; two hand-typed things (this
docstring and `SCOPES.md`'s own copy of the same sentence) had silently
agreed to be wrong together for weeks while every OTHER check in this
module and `test_consent_doctrine.py` kept passing, because none of them
ever read that specific sentence. `_toolkit_table_row_count`/
`_claimed_toolkit_count` close it the same way `_google_row_is_stale`
already closes a different staleness class in this same file: parse the
live table, parse the live claim, flip `stale_toolkit_count_claim` the
moment they disagree, and never again trust a docstring's word for its
own count.

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
from typing import cast

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

# Task 781: the "Concretely, on the toolkits in use:" table (SCOPES.md's
# real toolkit-scope table, a different shape from the app_id/status table
# above) and the number-word claim about its own row count, two sections
# later under "## Every connected app, accounted for". Same row shape and
# same re.MULTILINE-is-load-bearing lesson `test_consent_doctrine.py`'s own
# `_parse_toolkit_table` already names for this identical table.
_TOOLKIT_TABLE_START = "Concretely, on the toolkits in use:"
_TOOLKIT_TABLE_END = "**WIP note"
_TOOLKIT_TABLE_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$", re.MULTILINE)
_TOOLKIT_COUNT_CLAIM_RE = re.compile(r"table above names the ([a-z]+) toolkits", re.IGNORECASE)
_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def _section(scopes_text: str) -> str:
    """The `## Every connected app, accounted for` section's body text, or
    "" if the section itself is missing. Delegates to `text_patterns.
    bounded_section` (task 552), the shared read this file's own logic was
    the first of three to hand-write."""
    return text_patterns.bounded_section(scopes_text, _SECTION_HEADER)


def _accounted_for_app_ids(scopes_text: str) -> set[str]:
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


def _last_connected_app_ids(app_log_path: str) -> list[str]:
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
    return cast("list[str]", state.get("connected_app_ids", []))


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


def _toolkit_table_row_count(scopes_text: str) -> int:
    """Real data rows in SCOPES.md's "Concretely, on the toolkits in use:"
    table, counted structurally -- the header row and the `|--|--|--|`
    separator row are both excluded on sight, never a hand-typed number.
    Zero if the table's start marker is missing entirely."""
    if _TOOLKIT_TABLE_START not in scopes_text:
        return 0
    start = scopes_text.index(_TOOLKIT_TABLE_START)
    end = scopes_text.index(_TOOLKIT_TABLE_END, start) if _TOOLKIT_TABLE_END in scopes_text[start:] else len(scopes_text)
    table_text = scopes_text[start:end]
    count = 0
    for toolkit_cell, _uses_cell, _never_cell in _TOOLKIT_TABLE_ROW.findall(table_text):
        toolkit_cell = toolkit_cell.strip()
        if not toolkit_cell or set(toolkit_cell) <= {"-"}:
            continue  # the `|--|--|--|` separator row
        if toolkit_cell.lower() == "toolkit":
            continue  # the header row itself
        count += 1
    return count


def _claimed_toolkit_count(scopes_text: str) -> int | None:
    """The number-word in "*Task 135. The table above names the {N}
    toolkits Fencepost's own code uses.*", converted to an int. None if
    that sentence is missing, or names a word `_NUMBER_WORDS` doesn't
    know -- never guessed silently."""
    match = _TOOLKIT_COUNT_CLAIM_RE.search(scopes_text)
    if not match:
        return None
    return _NUMBER_WORDS.get(match.group(1).lower())


def check_scopes_completeness(
    scopes_path: str = DEFAULT_SCOPES_PATH,
    app_log_path: str = DEFAULT_APP_LOG_PATH,
    toolset_log_path: str = DEFAULT_TOOLSET_LOG_PATH,
) -> dict[str, object]:
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
    claimed_toolkit_count = _claimed_toolkit_count(scopes_text)
    live_toolkit_count = _toolkit_table_row_count(scopes_text)
    stale_toolkit_count_claim = (
        claimed_toolkit_count is not None and claimed_toolkit_count != live_toolkit_count
    )
    return {
        "clean": not missing and not stale_google_claim and not stale_toolkit_count_claim,
        "connected_app_ids": sorted(connected),
        "accounted_for_app_ids": sorted(accounted),
        "missing": missing,
        "stale_google_claim": stale_google_claim,
        "stale_toolkit_count_claim": stale_toolkit_count_claim,
        "claimed_toolkit_count": claimed_toolkit_count,
        "live_toolkit_count": live_toolkit_count,
    }


def format_result(result: dict[str, object]) -> str:
    if result["stale_google_claim"]:
        return (
            "scopes completeness: BROKEN -- stale arcade-google claim: row says "
            "\"in use by Fencepost\" but the last recorded gateway-toolset check "
            "found zero Gmail/Calendar tools live"
        )
    if result["stale_toolkit_count_claim"]:
        return (
            "scopes completeness: BROKEN -- stale toolkit-count claim: SCOPES.md's own "
            f"sentence claims {result['claimed_toolkit_count']} toolkit(s), the "
            f"\"toolkits in use\" table itself names {result['live_toolkit_count']}"
        )
    if not result["connected_app_ids"]:
        return "scopes completeness: clean (no apps recorded as connected)"
    if result["clean"]:
        return (
            f"scopes completeness: clean "
            f"({len(cast('list[str]', result['connected_app_ids']))} connected app(s), all accounted for)"
        )
    return (
        f"scopes completeness: BROKEN -- undocumented connected app(s): "
        f"{', '.join(cast('list[str]', result['missing']))}"
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = check_scopes_completeness()
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
