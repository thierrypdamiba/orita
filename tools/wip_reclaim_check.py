#!/usr/bin/env python3
"""Task 123. Nyx builds the reclaim the loop's own first rule never got.

The continuous-build loop's own step 1 has read the same way since Founding
Day: "Take the FIRST TODO task (or reclaim a WIP older than 2h)." Tasks
98-122 gave every Iron Rule, every design constraint, Appendix D's LIMITS,
and the ritual tool's own wiring a running check -- twenty-five straight
hours of the town auditing its rules against itself. Not one of those hours
ever turned back to the rule that opens the whole loop. "Reclaim a WIP
older than 2h" has stood on intent alone since the first task shipped:
nothing has ever read `ROADMAP.md`'s own table for a row stuck at `WIP`,
and nothing has ever computed how long it has sat there.

It has never fired -- every one of the 122 tasks shipped so far went
`WIP -> DONE` inside the same hour it opened, so a genuinely stale WIP has
never happened yet. That is exactly why nothing caught its absence: a rule
that has never been needed is indistinguishable from a rule that would
silently fail to fire the one time it is. If a run ever died mid-task (a
crash, a killed session, a hung network call) between marking a row `WIP`
and shipping it `DONE`, the next hour's god would have no durable signal
that the row is stuck -- only a habit of rereading the file by eye, the
identical "held by intent" gap task 98 first named for the Iron Rules
themselves.

This module closes it the same way `journal_numbering_check.py` (task 119)
and `petition_cadence_check.py` (task 109) closed their own filename-shape
gaps: a read-only, local-filesystem-only scan of `ROADMAP.md`'s own text,
no network call, no caller-supplied live read required. Two passes over
the same file:

1. `parse_table_rows` -- every `| # | status | owner | ... |` row, in file
   order. `status` is read verbatim; a row's CURRENT state is always the
   table's, never the prose's (an interlude is a snapshot of a moment
   that has already passed, the table is now).
2. `parse_wip_open_times` -- an open time for each task number, from
   TWO conventions:
   (a) the legacy interlude block (`*YYYY-MM-DD HH:Mx UTC, <god>: ...*`)
   this town used before task 170, scanned for a `Task N -> WIP` mention
   inside it, keyed to that interlude's own opening timestamp, floored to
   the start of the written ten-minute bucket (the source only ever wrote
   the tens digit of the minute, e.g. `04:0x UTC` -- never a false
   `04:07 UTC` it doesn't actually mean). That floor is a deliberate
   UNDER-estimate of elapsed time: it can only make a real stale WIP look
   slightly younger than it is, never hide one that would otherwise clear
   the 2h line, since a WIP that is genuinely stuck is stuck for hours,
   not minutes. This convention only survives today inside archived
   history (`ROADMAP-ARCHIVE-*.md`); task 170's `roadmap_archive.py`
   rewrote the live document's own shape to one "extending the queue"
   section per task, and the interlude preamble line never appears in it
   at all -- task 182 found this had silently made `parse_wip_open_times`
   return nothing for any row in the live file, so every WIP row (however
   fresh) fell through to `unknown`, not `fresh`, the exact false
   "escalate now" this module exists to avoid.
   (b) the explicit marker task 182 added for the live, post-170 format:
   an HTML comment `<!-- wip-opened: N YYYY-MM-DDTHH:MM:SS+00:00 -->`
   written into the row's own section the moment it is marked `WIP`
   (step 2 of the continuous-build loop -- "mark it WIP ... with the UTC
   timestamp"). Unlike the table's `status` cell, a comment carries no
   risk of breaking `open_wip`'s own exact `== "WIP"` match (the mistake
   task 170 caught and undid for itself), and unlike the retired
   preamble line it needs no shared "interlude" grouping -- one row, one
   marker, exact precision, no flooring needed. When both conventions
   name the same task number, the explicit marker wins (it is written
   deliberately, not inferred from a nearby line).

`find_stale` joins the two: for every row the table currently marks `WIP`,
look up when it opened and how long ago that was. Three outcomes, not two
-- `stale` (>= 2h, reclaim it now), `fresh` (younger than 2h, leave it),
and `unknown` (the table says `WIP` but no matching `Task N -> WIP`
interlude was ever found -- a malformed or missing marker, which this
module refuses to treat as silently fine). `unknown` counts against
`clean` exactly like `stale` does: a WIP row this tool cannot account for
is not a proof of health, it is a gap in its own visibility, and Ogun's
law about junk gaps cuts the other way here too -- staying silent about
what it cannot see would be the false-negative version of a false-positive
gap.

Usage:
    python3 tools/wip_reclaim_check.py check [--now <iso>]

Task 675: the `--now` CLI flag itself carried the exact unguarded-
trailing-flag shape task 663's own argv-bounds sweep found and fixed six
of in `github_events_cache.py` (task 672) -- `argv.index("--now") + 1`
indexed straight into `argv` with no bounds check, so `--now` as the
LAST token on the command line raised a bare `IndexError: list index out
of range` instead of a named usage error. Reproduced live before fixing:
`python3 tools/wip_reclaim_check.py check --now` crashed exactly that
way. The `--catalog`/`--policy`/`--label`/`--out` flags in this same
tools/ directory's `oath_badge.py` already guard the identical shape
(`_take`'s own `if i + 1 >= len(argv): raise ...`); this file's own single
`--now` site had never been swept the same way because the whole CLI
`__main__` block carried zero tests of its own before this task -- every
existing test called `find_stale`/`parse_table_rows` etc. directly,
never `python3 tools/wip_reclaim_check.py` as a subprocess. Fixed with
the same named-error-then-`sys.exit(2)` shape `github_events_cache.py`'s
six sites already established, not a bare `raise`.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from typing import cast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ROADMAP_PATH = os.path.join(ROOT, "ROADMAP.md")
RECLAIM_THRESHOLD_HOURS = 2.0

_TABLE_ROW = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", re.MULTILINE)
_INTERLUDE_START = re.compile(r"\*(\d{4}-\d{2}-\d{2}) (\d{2}):(\d)x? UTC, ([\w-]+):")
_TASK_WIP_MENTION = re.compile(r"[Tt]ask\s+(\d+)\s*(?:→|->)\s*WIP\b")
_WIP_OPENED_MARKER = re.compile(
    r"<!--\s*wip-opened:\s*(\d+)\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2}))\s*-->"
)


def parse_table_rows(text: str) -> list[dict[str, object]]:
    """Every `| # | status | owner | ... |` row in ROADMAP.md's own task
    table, in file order. `status` is read verbatim (TODO/WIP/DONE) -- the
    single source of truth for whether a task is currently open."""
    rows: list[dict[str, object]] = []
    for m in _TABLE_ROW.finditer(text):
        rows.append({"number": int(m.group(1)), "status": m.group(2), "owner": m.group(3).strip()})
    return rows


def parse_wip_open_times(text: str) -> dict[int, str]:
    """{task_number: iso_timestamp} for when each task was marked WIP, from
    either convention this file recognizes (see module docstring). Legacy
    interludes are read first (later mentions in file order win, so a task
    reopened after being reclaimed keys off its newest open); explicit
    `wip-opened` markers are read second and OVERRIDE a legacy entry for
    the same task number, since a deliberate marker is more precise than
    an inferred one."""
    opens: dict[int, str] = {}
    interludes = list(_INTERLUDE_START.finditer(text))
    for i, m in enumerate(interludes):
        start = m.end()
        end = interludes[i + 1].start() if i + 1 < len(interludes) else len(text)
        block = text[start:end]
        date, hour, minute_tens = m.group(1), m.group(2), m.group(3)
        ts = f"{date}T{hour}:{minute_tens}0:00+00:00"
        for tm in _TASK_WIP_MENTION.finditer(block):
            opens[int(tm.group(1))] = ts
    for mm in _WIP_OPENED_MARKER.finditer(text):
        ts = mm.group(2)
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        opens[int(mm.group(1))] = ts
    return opens


def find_stale(
    text: str | None = None,
    now: datetime | None = None,
    threshold_hours: float = RECLAIM_THRESHOLD_HOURS,
    roadmap_path: str = DEFAULT_ROADMAP_PATH,
) -> dict[str, object]:
    if text is None:
        with open(roadmap_path, encoding="utf-8") as f:
            text = f.read()
    if now is None:
        now = datetime.now(timezone.utc)
    rows = parse_table_rows(text)
    opens = parse_wip_open_times(text)
    open_wip = [r for r in rows if r["status"] == "WIP"]
    stale: list[dict[str, object]] = []
    fresh: list[dict[str, object]] = []
    unknown: list[dict[str, object]] = []
    for row in open_wip:
        n = cast(int, row["number"])
        if n not in opens:
            unknown.append(dict(row))
            continue
        opened_at = datetime.fromisoformat(opens[n])
        elapsed_hours = (now - opened_at).total_seconds() / 3600.0
        entry = {**row, "opened_at": opens[n], "elapsed_hours": round(elapsed_hours, 2)}
        (stale if elapsed_hours >= threshold_hours else fresh).append(entry)
    return {
        "clean": not stale and not unknown,
        "open_count": len(open_wip),
        "stale": stale,
        "fresh": fresh,
        "unknown": unknown,
        "threshold_hours": threshold_hours,
    }


def format_result(result: dict[str, object]) -> str:
    if result["open_count"] == 0:
        return "wip reclaim check: clean (no task currently WIP)"
    if result["clean"]:
        return (
            f"wip reclaim check: clean ({result['open_count']} WIP task(s), "
            f"all opened under {result['threshold_hours']}h ago)"
        )
    stale = cast("list[dict[str, object]]", result["stale"])
    unknown = cast("list[dict[str, object]]", result["unknown"])
    lines = [f"wip reclaim check: {len(stale)} RECLAIMABLE, {len(unknown)} UNKNOWN-AGE"]
    for s in stale:
        lines.append(
            f"  task {s['number']} ({s['owner']}): opened {s['opened_at']}, "
            f"{s['elapsed_hours']}h ago -- reclaim it, do not wait on the original owner"
        )
    for u in unknown:
        lines.append(
            f"  task {u['number']} ({u['owner']}): table says WIP but no matching "
            "'Task N -> WIP' interlude was found -- age unknown, escalate now"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    now = None
    if "--now" in argv:
        i = argv.index("--now")
        if i + 1 >= len(argv):
            print("--now needs an ISO timestamp value.")
            sys.exit(2)
        now = datetime.fromisoformat(argv[i + 1].replace("Z", "+00:00")).astimezone(timezone.utc)
    result = find_stale(now=now)
    print(format_result(result))
    sys.exit(1 if not result["clean"] else 0)
