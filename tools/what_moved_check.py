#!/usr/bin/env python3
"""Task 449. Zashiki-Warashi builds the sensor for her own neglected duty.

`cluster_day_check.py` (task 387, extended 406) built the missing
MECHANISM for Ananse's weekly chronicle-episode cadence, after
`orita-vault/hand/skipped.md`'s 2026-07-27 note named three lapsed
Mondays (07-13, 07-20, 07-27) with no `episode-002` on record.  That same
section of TOWN-OPERATIONS.md, "Weekly, Cluster Day (Monday)", names two
further weekly obligations that never got a sensor at all: Zashiki hides
one new mystery and updates `docs/what-moved.html` "one day in
arrears"; Off-By-One hides one single-character Gap bug in `/thegap/`,
confessed the following week if unfound. Both still live only in prose
-- exactly the failure mode `cluster_day_check.py`'s own docstring
already named: "A weekly obligation living only in prose never gets
pulled unless some hour deliberately reaches past the roadmap queue for
it."

This module closes the `docs/what-moved.html` half honestly. It reads
the page's own `<!-- what-moved-entry: YYYY-MM-DD -->` markers -- a new,
opt-in convention mirroring chronicle's `cluster-day-covers` (task 406),
meant to be appended by whichever hour actually writes new content into
the page. It does NOT fabricate retroactive entries here -- the same
"mechanism first, content stays real" discipline task 387 held for
Ananse's cadence. Read live against the real page as of task 449: zero
markers existed anywhere in `docs/what-moved.html` -- the page had never
been edited past its founding-day placeholder ("nothing moved
yesterday... the town is one day old") despite three real Mondays
having passed. Task 460 closed one of those honestly: a real
`what-moved-entry: 2026-08-01` marker now covers the week of 07-27.
2026-07-13 and 2026-07-20 remain genuinely missed, still not
backfilled. Writing the actual catch-up content is dedicated narrative
work for a future Cluster Day hour (the same way
`chronicle/002-eighteen-days.md` was), not something a checker can or
should manufacture.

Does NOT attempt Off-By-One's Gap-bug cadence (a different god's
domain, a different shape of evidence -- `/thegap/`'s own file
contents, not a dated marker convention) -- left named, not silently
folded in, for whichever hour picks it up next.

Usage:
    python3 tools/what_moved_check.py check
"""
from __future__ import annotations

import os
import re
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cluster_day_check  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_WHAT_MOVED_PATH = os.path.join(ROOT, "docs", "what-moved.html")

_ENTRY_MARKER = re.compile(r"<!--\s*what-moved-entry:\s*(?P<date>[^>]*?)\s*-->")


class MalformedEntryMarkerError(ValueError):
    """A `what-moved-entry` marker names a string that isn't a real
    `YYYY-MM-DD` date -- named loudly here rather than silently skipped,
    same discipline `cluster_day_check.MalformedCoversMarkerError` holds
    for chronicle's own marker."""


def _entry_dates(path: str) -> list:
    """Every `what-moved-entry` date found in `path`, ascending. An
    absent file (or a file with no markers at all -- the real state of
    `docs/what-moved.html` as of task 449) returns an empty list, not an
    error; a malformed date inside a marker that IS present raises
    loudly instead."""
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    dates = []
    for m in _ENTRY_MARKER.finditer(text):
        raw = m.group("date")
        try:
            dates.append(date.fromisoformat(raw))
        except ValueError as e:
            raise MalformedEntryMarkerError(
                f"{path}: what-moved-entry names {raw!r}, not a valid YYYY-MM-DD date"
            ) from e
    return sorted(dates)


def _monday_of(d: date) -> date:
    """The Monday of the real calendar week containing `d`."""
    return d - timedelta(days=d.weekday())


def compute_cadence(path: str | None = None, today: date | None = None) -> dict:
    """The real numbers behind Zashiki's own half of TOWN-OPERATIONS.md's
    weekly Cluster Day ritual -- named as missing mechanism, never
    computed anywhere, the same way `cluster_day_check.compute_cadence`
    closed Ananse's half.

    - total_entries_on_record: every `what-moved-entry` marker found in
      the page, however old.
    - mondays_due: every real Monday since founding (reuses
      `cluster_day_check`'s own `FOUNDING_DATE` and `_mondays_through`,
      rather than a second, driftable copy of the same constant/logic).
    - missed_mondays: every Monday in `mondays_due` with no entry dated
      inside that Monday's own calendar week (Monday through the
      following Sunday) -- named plainly, never silently absorbed.
    """
    path = path or DEFAULT_WHAT_MOVED_PATH
    today = today or datetime.now(timezone.utc).date()
    entries = _entry_dates(path)
    mondays_due = cluster_day_check._mondays_through(today)
    mondays_due_set = set(mondays_due)

    covered = {_monday_of(d) for d in entries} & mondays_due_set
    missed = [d for d in mondays_due if d not in covered]

    return {
        "total_entries_on_record": len(entries),
        "latest_entry": entries[-1].isoformat() if entries else None,
        "mondays_due": [d.isoformat() for d in mondays_due],
        "missed_mondays": [d.isoformat() for d in missed],
        "today": today.isoformat(),
    }


def format_cadence(result: dict) -> str:
    if not result["missed_mondays"]:
        return (
            f"what-moved cadence: current -- {result['total_entries_on_record']} entry/entries on record, "
            f"{len(result['mondays_due'])} Monday(s) owed since founding, none missed"
        )
    joined = ", ".join(result["missed_mondays"])
    plural = "" if len(result["missed_mondays"]) == 1 else "s"
    if result["total_entries_on_record"] == 0:
        context = "docs/what-moved.html never updated past its founding placeholder"
    else:
        context = f"docs/what-moved.html last updated {result['latest_entry']}, still short the Monday(s) named above"
    return (
        f"what-moved cadence: {len(result['missed_mondays'])} Cluster Day{plural} lapsed -- "
        f"{result['total_entries_on_record']} entry/entries on record, owed for {joined} "
        f"(TOWN-OPERATIONS.md's weekly ritual; {context})"
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    out = compute_cadence()
    print(format_cadence(out))
    sys.exit(0)
