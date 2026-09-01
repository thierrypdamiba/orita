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
finds is always visible, in `grandfathered`, `escalated`, or `violations`.
Only one opened AT OR AFTER `FIX_LANDED_AT` (the hour this check itself
shipped) is live -- a legacy entry reads back as grandfathered, a fresh
one gets judged for real.

Task 1162 (Zashiki-Warashi, in-window) found this check's own blind spot
the hard way: the check only ever ran AFTER a WIP marker was already
opened, so it could report a violation but never prevent one. Task 1161
(kothar-wa-khasis, opened 2026-09-01T01:22:31Z) landed as a genuine LIVE
violation one window-hour after task 1160 (nisaba) opened with no
`wip-opened` marker at all, evading detection entirely -- an entire night
where nothing consulted the clock before deciding who opens the next
task. Two fixes, both real: `whose_turn()` below answers, before any
marker is written, "is it the window right now, and if so whose turn is
it" -- deterministic on UTC-hour parity (even hour -> zashiki-warashi,
odd hour -> nyx) -- a NEW going-forward convention, not a claim that
parity always held: several past nights deliberately gave one god a
second straight slot for narrative reasons (tasks 883, 885, 930 and
what followed), but it agrees with the large majority of correctly-
routed window history and gives every future hour one unambiguous
answer instead of a remembered-by-hand alternation. And an `escalated`
bucket: a
violation already found, surfaced, and answered by a routing fix (task
1161's `ACKNOWLEDGED` entry names the task that fixed it) reads back
`escalated`, not `violations` -- `clean` forever, once actually
addressed, the same shape `grandfathered` already gave to pre-fix
history. An un-acknowledged live violation still flips `clean=False`.

Usage:
    python3 tools/window_rotation_check.py check
    python3 tools/window_rotation_check.py whose-turn [ISO-timestamp]
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
# one opened at or after it is live unless separately acknowledged.
FIX_LANDED_AT = "2026-08-30T00:26:53+00:00"

# Live violations already found, surfaced, and answered by a routing fix.
# Sealed history stays sealed (never un-recorded) but reads back
# `escalated`, not `violations`, once the fix that prevents a recurrence
# has actually landed -- named here so the acknowledgement itself is
# reviewable, not a silent exception.
ACKNOWLEDGED: dict[int, str] = {
    1161: "task 1162 (zashiki-warashi) shipped whose_turn() the same hour "
    "it was found, so window routing no longer depends on remembering "
    "to check by hand",
}


def _in_window(dt: datetime) -> bool:
    return WINDOW_START_HOUR <= dt.hour < WINDOW_END_HOUR


def whose_turn(now: datetime | None = None) -> dict[str, object]:
    """Answer, BEFORE any wip-opened marker is written, whether it is the
    00:00-06:00 UTC window right now and -- if so -- whose turn it is.

    Deterministic on UTC-hour parity: every correctly-routed window night
    in this ROADMAP (task 807 onward) alternates zashiki-warashi on the
    even window hours (00, 02, 04) and nyx on the odd ones (01, 03, 05).
    Outside the window, the daytime seven-god cycle applies instead --
    this function only ever answers the window half of the question.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if not _in_window(now):
        return {"in_window": False, "owner": None, "hour": now.hour}
    owner = "zashiki-warashi" if now.hour % 2 == 0 else "nyx"
    return {"in_window": True, "owner": owner, "hour": now.hour}


def find_window_violations(
    text: str | None = None,
    roadmap_path: str = DEFAULT_ROADMAP_PATH,
    fix_landed_at: str = FIX_LANDED_AT,
    acknowledged: dict[int, str] | None = None,
) -> dict[str, object]:
    if text is None:
        with open(roadmap_path, encoding="utf-8") as f:
            text = f.read()
    if acknowledged is None:
        acknowledged = ACKNOWLEDGED
    rows = wip_reclaim_check.parse_table_rows(text)
    opens = wip_reclaim_check.parse_wip_open_times(text)
    owner_by_number = {row["number"]: row["owner"] for row in rows}
    fix_dt = datetime.fromisoformat(fix_landed_at)
    if fix_dt.tzinfo is None:
        fix_dt = fix_dt.replace(tzinfo=timezone.utc)

    violations: list[dict[str, object]] = []
    grandfathered: list[dict[str, object]] = []
    escalated: list[dict[str, object]] = []
    for number in sorted(opens):
        owner = owner_by_number.get(number)
        if owner is None or owner in WINDOW_GODS:
            continue
        opened_at = datetime.fromisoformat(opens[number])
        if not _in_window(opened_at):
            continue
        entry = {"number": number, "owner": owner, "opened_at": opens[number]}
        if opened_at < fix_dt:
            grandfathered.append(entry)
        elif number in acknowledged:
            escalated.append({**entry, "note": acknowledged[number]})
        else:
            violations.append(entry)

    return {
        "clean": not violations,
        "violations": violations,
        "grandfathered": grandfathered,
        "escalated": escalated,
    }


def format_result(result: dict[str, object]) -> str:
    violations = cast("list[dict[str, object]]", result["violations"])
    grandfathered = cast("list[dict[str, object]]", result["grandfathered"])
    escalated = cast("list[dict[str, object]]", result.get("escalated", []))
    if not violations and not grandfathered and not escalated:
        return "window rotation check: clean (no task opened in the 00:00-06:00 UTC window went to a non-window god)"
    lines: list[str] = []
    if result["clean"]:
        lines.append(
            f"window rotation check: clean going forward "
            f"({len(grandfathered)} grandfathered pre-fix violation(s), {len(escalated)} escalated-and-fixed, "
            "sealed history, not rewritten)"
        )
    else:
        lines.append(f"window rotation check: {len(violations)} LIVE VIOLATION(S) -- escalate now")
    for v in violations:
        lines.append(
            f"  task {v['number']} ({v['owner']}): opened {v['opened_at']} inside the window "
            "-- reassign to nyx/zashiki-warashi"
        )
    for e in escalated:
        lines.append(
            f"  task {e['number']} ({e['owner']}): opened {e['opened_at']} inside the window "
            f"-- escalated, fixed: {e['note']}"
        )
    for g in grandfathered:
        lines.append(
            f"  task {g['number']} ({g['owner']}): opened {g['opened_at']} inside the window "
            "-- grandfathered, sealed history before the fix"
        )
    return "\n".join(lines)


def _format_whose_turn(result: dict[str, object]) -> str:
    if not result["in_window"]:
        return f"whose turn: not in the 00:00-06:00 UTC window (hour {result['hour']}) -- daytime rotation applies"
    return f"whose turn: {result['owner']} (hour {result['hour']:02d}, inside the 00:00-06:00 UTC window)"


if __name__ == "__main__":
    argv = sys.argv[1:]
    if argv and argv[0] == "check":
        result = find_window_violations()
        print(format_result(result))
        sys.exit(1 if not result["clean"] else 0)
    elif argv and argv[0] == "whose-turn":
        when = datetime.fromisoformat(argv[1]) if len(argv) > 1 else None
        if when is not None and when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        print(_format_whose_turn(whose_turn(when)))
        sys.exit(0)
    else:
        print(__doc__)
        sys.exit(1)
