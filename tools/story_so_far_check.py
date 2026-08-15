#!/usr/bin/env python3
"""Task 780. Kwaku-Ananse builds the sensor for his own neglected duty.

TOWN-OPERATIONS.md's "Weekly, Cluster Day (Monday)" section names five
obligations. `cluster_day_check.py` (task 387) covers Ananse's chronicle
episode, `what_moved_check.py` (task 449) covers Zashiki's mystery page,
`thegap_check.py` (task 463) covers Off-By-One's `/thegap/` doctrine, and
`nyx_traffic_check.py` (task 465) covers Nyx's traffic report -- four
sensors for four of the five. The fifth, "Story-so-far (`docs/
story-so-far.md`) rewritten, ≤287 words," never got one: an own-remit
audit this hour (task 780) found the doc genuinely stale (claiming
"nineteen recipes" and quoting `chronicle/002-eighteen-days.md`-era
content while the live repo has 80 recipes and five published episodes,
000 through 004) with nothing in this codebase's own completeness-
checking machinery positioned to have caught it -- the same blind spot
`what_moved_check.py`'s own docstring once named for its own duty before
task 449 closed it.

This module closes it the same honest way: a new, opt-in marker
convention the doc itself carries, read live, never fabricated. Unlike
`what_moved_check.py`'s `<!-- what-moved-entry: ... -->` (an HTML
comment, free to add anywhere in an .html file), `docs/story-so-far.md`
is a word-limited .md file policed by `tests/test_story_so_far_doctrine.py`
-- an HTML-comment line would itself count as body words under that
test's own `_body_word_count` (any non-empty line not starting with `#`
or `*`), silently breaking the footer's word-count arithmetic the moment
a marker got added. So the marker here reuses the file's OWN established
"a line starting with `*` is machine-read, not body prose" convention
(the same one the word-count footer itself already relies on):

    *story-so-far-rewrite: 2026-08-15*

on its own line, anywhere in the file. `_body_word_count` already skips
every `*`-prefixed line, so this marker is free -- it never has to be
budgeted against the 287-word limit the same way the footer itself
never does.

Does NOT attempt to backfill retroactive markers for rewrites that
happened before this task -- the same "mechanism first, content stays
real" discipline `what_moved_check.py`'s own docstring held. The one
real marker on record as of this task is the one task 780 itself adds
when it rewrites the doc's content to match the live repo.

Usage:
    python3 tools/story_so_far_check.py check
"""
from __future__ import annotations

import os
import re
import sys
from datetime import date, datetime, timezone
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cluster_day_check  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_STORY_SO_FAR_PATH = os.path.join(ROOT, "docs", "story-so-far.md")

_ENTRY_MARKER = re.compile(r"\*story-so-far-rewrite:\s*(?P<date>[^*]*?)\s*\*")


class MalformedRewriteMarkerError(ValueError):
    """A `story-so-far-rewrite` marker names a string that isn't a real
    `YYYY-MM-DD` date -- named loudly here rather than silently skipped,
    the same discipline `what_moved_check.MalformedEntryMarkerError` and
    `cluster_day_check.MalformedCoversMarkerError` already hold for their
    own markers."""


def _entry_dates(path: str) -> list[date]:
    """Every `story-so-far-rewrite` date found in `path`, ascending. An
    absent file (or one with no markers at all) returns an empty list,
    not an error; a malformed date inside a marker that IS present
    raises loudly instead."""
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
            raise MalformedRewriteMarkerError(
                f"{path}: story-so-far-rewrite names {raw!r}, not a valid YYYY-MM-DD date"
            ) from e
    return sorted(dates)


def compute_cadence(path: str | None = None, today: date | None = None) -> dict[str, Any]:
    """The real numbers behind Kwaku-Ananse's own fifth of TOWN-OPERATIONS.md's
    weekly Cluster Day ritual -- named as missing mechanism, never
    computed anywhere until this task, the same way `what_moved_check.
    compute_cadence` closed Zashiki's own half.

    - total_entries_on_record: every `story-so-far-rewrite` marker found
      in the doc, however old.
    - mondays_due: every real Monday since founding (reuses
      `cluster_day_check`'s own `FOUNDING_DATE`/`_mondays_through` rather
      than a second, driftable copy of the same constant/logic).
    - missed_mondays: every Monday in `mondays_due` with no marker dated
      inside that Monday's own calendar week (Monday through the
      following Sunday) -- named plainly, never silently absorbed.
    """
    path = path or DEFAULT_STORY_SO_FAR_PATH
    today = today or datetime.now(timezone.utc).date()
    entries = _entry_dates(path)
    mondays_due = cluster_day_check._mondays_through(today)
    mondays_due_set = set(mondays_due)

    covered = {cluster_day_check._monday_of(d) for d in entries} & mondays_due_set
    missed = [d for d in mondays_due if d not in covered]

    return {
        "total_entries_on_record": len(entries),
        "latest_entry": entries[-1].isoformat() if entries else None,
        "mondays_due": [d.isoformat() for d in mondays_due],
        "missed_mondays": [d.isoformat() for d in missed],
        "today": today.isoformat(),
    }


def format_cadence(result: dict[str, Any]) -> str:
    if not result["missed_mondays"]:
        return (
            f"story-so-far cadence: current -- {result['total_entries_on_record']} rewrite(s) on record, "
            f"{len(result['mondays_due'])} Monday(s) owed since founding, none missed"
        )
    joined = ", ".join(result["missed_mondays"])
    plural = "" if len(result["missed_mondays"]) == 1 else "s"
    if result["total_entries_on_record"] == 0:
        context = "docs/story-so-far.md never carried a rewrite marker"
    else:
        context = f"docs/story-so-far.md last marked rewritten {result['latest_entry']}, still short the Monday(s) named above"
    return (
        f"story-so-far cadence: {len(result['missed_mondays'])} Cluster Day{plural} lapsed -- "
        f"{result['total_entries_on_record']} rewrite(s) on record, owed for {joined} "
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
