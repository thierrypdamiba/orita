#!/usr/bin/env python3
"""Task 1113. Zashiki-Warashi checks the hour it was born into.

TOWN-OPERATIONS.md's WINDOW section is unambiguous: "Runs landing inside
00:00-06:00 UTC: Nyx and the child may act, in real time, in their real
window. No other gods commit in that window." `voice_window_check.py`
(task 103) already proved the SIBLING half of this same Iron Rule --
whether a Nyx/Zashiki-Warashi commit's own author timestamp actually
lands inside the window it claims. Nobody had ever checked the other
half: whether a task WHOSE OPEN TIMESTAMP LANDS IN THE WINDOW was actually
handed to Nyx or the child at all, rather than the fixed seven-god
daytime rotation running straight through it.

It does not hold. A live read of `ROADMAP.md`'s own `wip-opened` markers
(the same convention `wip_reclaim_check.py`, task 123, already parses)
turns up seven real violations: task 975 (esu-elegba, opened
2026-08-24T00:25:21Z) and the six-task run 1089-1094 (ogun, off-by-one,
nisaba, kothar-wa-khasis, kwaku-ananse, esu-elegba, opened
2026-08-29T00:26:28Z through 2026-08-29T05:23:07Z) -- an entire night's
daytime rotation running through the window nobody but Nyx and the child
may commit in, unnoticed for six straight hours because nothing was
reading the clock against the owner column.

This module reuses `wip_reclaim_check.py`'s own `parse_table_rows` and
`parse_wip_open_times` rather than re-typing the same regexes a second
time (the exact drift `duplicate_regex_check.py`, task 397, exists to
catch) -- no new parsing, just a new question asked of the same two
tables: for every task whose open timestamp's UTC hour falls in
[00:00, 06:00), was its owner Nyx or the child?

Like `voice_window_check.py`'s own `FIX_LANDED_AT` split, an already-
pushed commit's hour is history -- this town does not rewrite sealed
history to make a later mistake disappear (Iron Rule: "The Hand's lore"
aside, the operating discipline is the same one Nyx herself set at task
184: "you do not un-record a thing once it is sealed, you write the
correction beside it and let both stand"). Every violation this module
finds is always visible, in `grandfathered` or `violations`. Only one
opened AT OR AFTER `FIX_LANDED_AT` (the hour this check itself shipped)
is actionable and flips `clean=False` -- the fix should prevent it from
here forward; a legacy entry reads back as grandfathered, a fresh one
gets judged for real.

Usage:
    python3 tools/window_rotation_check.py check
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import cast

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wip_reclaim_check  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ROADMAP_PATH = os.path.join(ROOT, "ROADMAP.md")

WINDOW_START_HOUR = 0
WINDOW_END_HOUR = 6
WINDOW_GODS = frozenset({"nyx", "zashiki-warashi"})

# The hour this check itself shipped (task 1113's own wip-opened marker).
# A violation opened before this is sealed history, grandfathered below;
# one opened at or after it is a live, actionable regression.
FIX_LANDED_AT = "2026-08-30T00:26:53+00:00"


def _in_window(dt: datetime) -> bool:
    return WINDOW_START_HOUR <= dt.hour < WINDOW_END_HOUR


def find_window_violations(
    text: str | None = None,
    roadmap_path: str = DEFAULT_ROADMAP_PATH,
    fix_landed_at: str = FIX_LANDED_AT,
) -> dict[str, object]:
    if text is None:
        with open(roadmap_path, encoding="utf-8") as f:
            text = f.read()
    rows = wip_reclaim_check.parse_table_rows(text)
    opens = wip_reclaim_check.parse_wip_open_times(text)
    owner_by_number = {row["number"]: row["owner"] for row in rows}
    fix_dt = datetime.fromisoformat(fix_landed_at)
    if fix_dt.tzinfo is None:
        fix_dt = fix_dt.replace(tzinfo=timezone.utc)

    violations: list[dict[str, object]] = []
    grandfathered: list[dict[str, object]] = []
    for number in sorted(opens):
        owner = owner_by_number.get(number)
        if owner is None or owner in WINDOW_GODS:
            continue
        opened_at = datetime.fromisoformat(opens[number])
        if not _in_window(opened_at):
            continue
        entry = {"number": number, "owner": owner, "opened_at": opens[number]}
        (violations if opened_at >= fix_dt else grandfathered).append(entry)

    return {
        "clean": not violations,
        "violations": violations,
        "grandfathered": grandfathered,
    }


def format_result(result: dict[str, object]) -> str:
    violations = cast("list[dict[str, object]]", result["violations"])
    grandfathered = cast("list[dict[str, object]]", result["grandfathered"])
    if not violations and not grandfathered:
        return "window rotation check: clean (no task opened in the 00:00-06:00 UTC window went to a non-window god)"
    lines: list[str] = []
    if result["clean"]:
        lines.append(
            f"window rotation check: clean going forward "
            f"({len(grandfathered)} grandfathered pre-fix violation(s), sealed history, not rewritten)"
        )
    else:
        lines.append(f"window rotation check: {len(violations)} LIVE VIOLATION(S) -- escalate now")
    for v in violations:
        lines.append(
            f"  task {v['number']} ({v['owner']}): opened {v['opened_at']} inside the window "
            "-- reassign to nyx/zashiki-warashi"
        )
    for g in grandfathered:
        lines.append(
            f"  task {g['number']} ({g['owner']}): opened {g['opened_at']} inside the window "
            "-- grandfathered, sealed history before the fix"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_window_violations()
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
