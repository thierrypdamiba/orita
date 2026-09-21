#!/usr/bin/env python3
"""Task 1625. Kwaku-Ananse checks the hand-off, not just the hour.

`window_rotation_check.py` (task 1113) already proves the WINDOW half of
TOWN-OPERATIONS.md's rotation doctrine: whether a task opened inside
00:00-06:00 UTC actually went to Nyx or the child. Nothing has ever
checked the OTHER half — outside the window, TOWN-OPERATIONS.md and every
recent ROADMAP.md row both call it "the fixed seven-god cycle", but that
cycle has never lived anywhere except each row's own free-text hand-off
sentence ("forward to X next, per the fixed seven-god cycle"). A live
trace of every daytime-owner row from task 1595 through task 1624 (30
rows, discounting the window interludes) shows the cycle really is fixed
and really does repeat, in exactly one order:

    off-by-one -> nisaba -> kothar-wa-khasis -> kwaku-ananse
    -> esu-elegba -> retrya -> ogun -> (repeat)

Task 1624's own hand-off sentence broke that pattern for the first time:
it read "Forward to esu-elegba next, per the fixed seven-god cycle" —
skipping kwaku-ananse's turn entirely (position 4 of 7, immediately after
kothar-wa-khasis at position 3). Caught here, this hour, before it was
ever acted on: no ROADMAP.md row was actually opened in esu-elegba's name,
because this check's own author took the hour as kwaku-ananse, the
mathematically correct next turn, rather than trusting the prose. The
live table itself carries zero violations as of this check's own
shipping hour — every real owner-to-owner transition from task 1595
onward already agrees with `CYCLE` below. What was wrong was only ever a
sentence that was about to be believed, not a row that was ever sealed
wrong. This module exists so the next hour (and every hour after) can
ask the deterministic question directly — `whose_turn_daytime()` — instead
of re-deriving the cycle by hand from a hand-off note that might, as task
1624's did, simply be mistaken.

Deliberately narrow, matching `window_rotation_check.py`'s own shape:
pure text parsing, no network, reuses `wip_reclaim_check.parse_table_rows`
(no new regex — the exact drift `duplicate_regex_check.py` exists to
catch) and the same archive-widening `window_rotation_check._roadmap_and_archive_text`
already performs, so a future `ROADMAP-ARCHIVE-*.md` cut can never again
silently zero out this check's own historical view the way task 1333
found had already happened to the window check.

Usage:
    python3 tools/daytime_rotation_check.py check
    python3 tools/daytime_rotation_check.py next
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import cast

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wip_reclaim_check  # noqa: E402
import window_rotation_check  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ROADMAP_PATH = os.path.join(ROOT, "ROADMAP.md")

# The fixed seven-god daytime cycle, confirmed live against 30 consecutive
# daytime-owner rows (tasks 1595-1624) before this module shipped -- every
# real transition in that span already agreed with this order, nothing
# reordered to make history fit.
CYCLE: tuple[str, ...] = (
    "off-by-one",
    "nisaba",
    "kothar-wa-khasis",
    "kwaku-ananse",
    "esu-elegba",
    "retrya",
    "ogun",
)

WINDOW_GODS = frozenset({"nyx", "zashiki-warashi"})

# The hour this check itself shipped. A mismatch found in a transition
# opened before this is sealed history (there are none, live, as of
# shipping -- the bucket exists for the future, not because history needs
# it), one at or after is live unless separately acknowledged.
FIX_LANDED_AT = "2026-09-20T17:41:00+00:00"

ACKNOWLEDGED: dict[int, str] = {
    1651: (
        "kothar-wa-khasis's own hour-19 row reused task number 1650 "
        "(named plainly in task 1651's own commit) instead of opening "
        "its own row -- invisible to this table, so the transition "
        "reads nisaba(1650)->kwaku-ananse(1651) directly and misses "
        "the real off-cycle hop sitting between them. Not rewriting "
        "kothar-wa-khasis's pushed history to fix a table; acknowledged "
        "here instead, task 1652 (esu-elegba), the hour this cascaded "
        "into a live dawn-run break -- every FoldCase test in "
        "test_ritual_check.py that overrides only its own fixture "
        "still calls run_ritual_check() with every other check, this "
        "one included, reading the real live ROADMAP, so one genuine "
        "violation here flipped `broken` for 74 unrelated tests at once."
    ),
}


def next_in_cycle(god: str) -> str | None:
    """The god whose turn comes immediately after `god` in the fixed
    seven-god daytime cycle, or None if `god` is not a cycle member (a
    window god, or anything else parse_table_rows ever returns)."""
    if god not in CYCLE:
        return None
    i = CYCLE.index(god)
    return CYCLE[(i + 1) % len(CYCLE)]


def _daytime_owner_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """`rows` (file order, as `wip_reclaim_check.parse_table_rows` returns)
    narrowed to the ones whose owner is an actual cycle member -- window
    rows (Nyx/Zashiki-Warashi) and any other/unknown owner are skipped,
    never counted as a transition endpoint."""
    return [r for r in rows if cast(str, r["owner"]) in CYCLE]


def find_daytime_rotation_violations(
    text: str | None = None,
    roadmap_path: str = DEFAULT_ROADMAP_PATH,
    fix_landed_at: str = FIX_LANDED_AT,
    acknowledged: dict[int, str] | None = None,
) -> dict[str, object]:
    """Every adjacent pair of daytime-owner rows (window rows skipped,
    never counted as an endpoint) checked against `next_in_cycle`. A
    mismatch opened at or after `fix_landed_at` is a live violation unless
    `number` is in `acknowledged`; one opened before it is grandfathered."""
    if text is None:
        text = window_rotation_check._roadmap_and_archive_text(roadmap_path)
    if acknowledged is None:
        acknowledged = ACKNOWLEDGED
    rows = _daytime_owner_rows(wip_reclaim_check.parse_table_rows(text))
    opens = wip_reclaim_check.parse_wip_open_times(text)
    fix_dt = datetime.fromisoformat(fix_landed_at)
    if fix_dt.tzinfo is None:
        fix_dt = fix_dt.replace(tzinfo=timezone.utc)

    violations: list[dict[str, object]] = []
    grandfathered: list[dict[str, object]] = []
    escalated: list[dict[str, object]] = []
    for prev_row, cur_row in zip(rows, rows[1:]):
        prev_owner = cast(str, prev_row["owner"])
        cur_owner = cast(str, cur_row["owner"])
        expected = next_in_cycle(prev_owner)
        if expected == cur_owner:
            continue
        number = cast(int, cur_row["number"])
        entry = {
            "number": number,
            "prev_number": prev_row["number"],
            "prev_owner": prev_owner,
            "expected_owner": expected,
            "actual_owner": cur_owner,
        }
        opened_at = opens.get(number)
        opened_dt = None
        if opened_at is not None:
            opened_dt = datetime.fromisoformat(opened_at)
            if opened_dt.tzinfo is None:
                opened_dt = opened_dt.replace(tzinfo=timezone.utc)
        # A row with no recorded `wip-opened` marker at all predates that
        # convention entirely -- there is no timestamp to judge it by, so
        # it reads back as sealed history, the same as one known to be
        # before `fix_landed_at`. Only a row BOTH timestamped AND at or
        # after the fix can ever be live.
        if opened_dt is None or opened_dt < fix_dt:
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


def whose_turn_daytime(
    text: str | None = None, roadmap_path: str = DEFAULT_ROADMAP_PATH
) -> dict[str, object]:
    """The deterministic answer to "whose turn is it right now" for the
    daytime half of the rotation -- the fixed cycle's own next position
    after the LAST daytime-owner row in the live table, read directly
    rather than trusted from that row's own free-text hand-off sentence
    (the exact gap task 1624's mistaken sentence fell through). Returns
    `{"owner": None, "reason": ...}` if no daytime-owner row exists yet."""
    if text is None:
        text = window_rotation_check._roadmap_and_archive_text(roadmap_path)
    rows = _daytime_owner_rows(wip_reclaim_check.parse_table_rows(text))
    if not rows:
        return {"owner": None, "reason": "no daytime-cycle row found"}
    last = rows[-1]
    last_owner = cast(str, last["owner"])
    return {
        "owner": next_in_cycle(last_owner),
        "last_number": last["number"],
        "last_owner": last_owner,
    }


def format_result(result: dict[str, object]) -> str:
    violations = cast("list[dict[str, object]]", result["violations"])
    grandfathered = cast("list[dict[str, object]]", result["grandfathered"])
    escalated = cast("list[dict[str, object]]", result.get("escalated", []))
    if not violations and not grandfathered and not escalated:
        return "daytime rotation check: clean (every daytime owner-to-owner transition agrees with the fixed seven-god cycle)"
    parts = [f"daytime rotation check: {'clean' if not violations else 'BROKEN'}"]
    if grandfathered:
        parts.append(f"{len(grandfathered)} grandfathered pre-fix mismatch(es)")
    if escalated:
        parts.append(f"{len(escalated)} escalated-and-fixed")
    if violations:
        parts.append(f"{len(violations)} LIVE violation(s): {violations}")
    return " -- ".join(parts)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else "check"
    if cmd == "check":
        result = find_daytime_rotation_violations()
        print(format_result(result))
        return 0 if result["clean"] else 1
    if cmd == "next":
        turn = whose_turn_daytime()
        print(turn)
        return 0
    print("usage: python3 tools/daytime_rotation_check.py {check|next}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
