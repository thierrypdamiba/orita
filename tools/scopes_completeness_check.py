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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SCOPES_PATH = os.path.join(ROOT, "fencepost", "SCOPES.md")
DEFAULT_APP_LOG_PATH = os.path.join(ROOT, "HAND", "arcade-app-check-log.jsonl")

_SECTION_HEADER = re.compile(r"^## Every connected app, accounted for\s*$", re.MULTILINE)
_NEXT_HEADER = re.compile(r"^## ", re.MULTILINE)
_TABLE_ROW_APP_ID = re.compile(r"^\|\s*`([^`]+)`", re.MULTILINE)


def _accounted_for_app_ids(scopes_text: str) -> set:
    """Every app_id named in a `| `app_id`... |` table row inside the
    `## Every connected app, accounted for` section, structurally --
    never a hardcoded list of expected ids. Returns an empty set if the
    section itself is missing (a real gap, not silently treated as
    vacuously accounted-for)."""
    header_match = _SECTION_HEADER.search(scopes_text)
    if header_match is None:
        return set()
    start = header_match.end()
    next_match = _NEXT_HEADER.search(scopes_text, pos=start)
    end = next_match.start() if next_match else len(scopes_text)
    section = scopes_text[start:end]
    return {m.group(1) for m in _TABLE_ROW_APP_ID.finditer(section)}


def _last_connected_app_ids(app_log_path: str) -> list:
    """The most recently recorded `connected_app_ids` list from
    `arcade_app_watch.py`'s own durable log. Empty list if the log has
    never been written -- nothing connected is not an error."""
    if not os.path.exists(app_log_path):
        return []
    import json

    with open(app_log_path) as f:
        lines = [line for line in f if line.strip()]
    if not lines:
        return []
    return json.loads(lines[-1]).get("connected_app_ids", [])


def check_scopes_completeness(
    scopes_path: str = DEFAULT_SCOPES_PATH,
    app_log_path: str = DEFAULT_APP_LOG_PATH,
) -> dict:
    """Cross-check every currently-connected real app_id against
    `fencepost/SCOPES.md`'s own `## Every connected app, accounted for`
    section. Returns `clean: True` with the accounted-for set when every
    connected app_id is named; otherwise `clean: False` and the specific
    missing ids -- never a pass/fail without saying which app is
    undocumented."""
    with open(scopes_path, encoding="utf-8") as f:
        scopes_text = f.read()
    accounted = _accounted_for_app_ids(scopes_text)
    connected = _last_connected_app_ids(app_log_path)
    missing = sorted(set(connected) - accounted)
    return {
        "clean": not missing,
        "connected_app_ids": sorted(connected),
        "accounted_for_app_ids": sorted(accounted),
        "missing": missing,
    }


def format_result(result: dict) -> str:
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
