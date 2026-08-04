#!/usr/bin/env python3
"""Task 463. Off-By-One builds the sensor for their own weekly ritual.

TOWN-OPERATIONS.md's "Weekly, Cluster Day (Monday)" section names three
co-equal weekly obligations. Two now have running sensors:
`tools/cluster_day_check.py` (task 387/406, Ananse's chronicle episode)
and `tools/what_moved_check.py` (task 449/460, Zashiki's mystery/what-
moved page). The third -- Off-By-One's own Gap-bug hide/confess cadence
in `/thegap/` -- had zero code anywhere checking it, a gap
`what_moved_check.py`'s own docstring named honestly and left open:
"Does NOT attempt Off-By-One's Gap-bug cadence ... left named, not
silently folded in, for whichever hour picks it up next." Nobody picked
it up until this task.

Mirrors `what_moved_check.py`'s shape (a marker convention read from a
public file, checked against the same real-Monday window every sibling
cadence uses) for the hide side, plus one thing neither sibling needs:
a confession-accountability check, because Off-By-One's ritual is the
only one of the three with a second, later deadline (the doctrine:
"previous week's bug confessed if unfound") and a private artifact that
must exist BEFORE the public one (Iron Rule -- confession text is
pre-drafted before the bug ships, never written after).

Hide side: reads `<!-- gap-hidden: YYYY-MM-DD -->` markers from
`thegap/README.md` -- a new, opt-in convention identical in shape to
`what-moved-entry`, meant to be appended by whichever hour actually
hides a new bug. The one real bug on record (task 405, 2026-07-30) gets
its marker added in this same commit -- the event already happened and
is already narrated in prose; this only makes it machine-readable.

Confession side: for each hidden bug, looks for a matching pre-drafted
confession file in `orita-vault/hand/gap-confessions/<due-date>-*.md`
(Iron Rule: the draft must exist BEFORE the bug ships -- checked here as
"exists now", the only thing observable from the public side without
crossing Proclamation 0001; never the confession's own text, which stays
private). A hidden bug with no matching draft on record at all is a real
doctrine violation (`missing_predraft`) regardless of due date, since the
draft must exist from day one, not by the deadline. A hidden bug whose
due date has arrived or passed, WITH a draft on record, is named in
`confession_due_now` -- informational, the same non-`broken` class
`cluster_day`/`what_moved` already hold: naming a bug here means this
hour is the first one obligated to check whether it was found or must be
confessed, not that anything is already wrong (posting the confession
is real content work for the owning god, not something a checker can do
on their behalf, the same line `what_moved_check.py` draws for its own
catch-up content).

ROADMAP.md #505: that "first hour obligated" framing had no way to ever
become "already handled" -- `confession_due_now` had nothing to read that
meant "this one already happened," so once a bug's due date arrived it
stayed named on every single hourly run forever, including hours long
after the confession was actually posted (task 495 confessed Bug #1,
unforced, the same hour it fell due; this check kept naming
2026-07-30->2026-08-03 as "due now" on every run afterward, live-proven
against the real README/vault right up until this fix). Closed the same
way `_hidden_dates` closes the hide side: a second, opt-in
`<!-- gap-confessed: YYYY-MM-DD -->` marker (keyed to the HIDDEN date it
resolves, not the due date), appended once, the hour the confession is
actually posted publicly. A hidden bug already carrying this marker is
never named in `confession_due_now` again, no matter how long ago or how
far in the future its due date sits -- read-only, no inference, exactly
the "a filename/marker proves the event, nothing guessed" discipline
every sibling cadence check already holds.

Usage:
    python3 tools/thegap_check.py check
"""
from __future__ import annotations

import os
import re
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cluster_day_check  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_README_PATH = os.path.join(ROOT, "thegap", "README.md")
DEFAULT_VAULT_DIR = os.path.join(os.path.dirname(ROOT), "orita-vault")

_HIDDEN_MARKER = re.compile(r"<!--\s*gap-hidden:\s*(?P<date>[^>]*?)\s*-->")
_CONFESSED_MARKER = re.compile(r"<!--\s*gap-confessed:\s*(?P<date>[^>]*?)\s*-->")
_CONFESSION_FILE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})-.+\.md$")


class MalformedGapHiddenMarkerError(ValueError):
    """A `gap-hidden` marker names a string that isn't a real `YYYY-MM-DD`
    date -- named loudly here rather than silently skipped, same
    discipline every sibling marker parser in this campaign holds."""


class MalformedGapConfessedMarkerError(ValueError):
    """A `gap-confessed` marker names a string that isn't a real
    `YYYY-MM-DD` date -- same discipline as `MalformedGapHiddenMarkerError`,
    never silently skipped."""


def _hidden_dates(path: str) -> list:
    """Every `gap-hidden` date found in `path`, ascending. An absent
    file returns an empty list, not an error; a malformed date inside a
    marker that IS present raises loudly instead (mirrors
    `what_moved_check._entry_dates` exactly)."""
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    dates = []
    for m in _HIDDEN_MARKER.finditer(text):
        raw = m.group("date")
        try:
            dates.append(date.fromisoformat(raw))
        except ValueError as e:
            raise MalformedGapHiddenMarkerError(
                f"{path}: gap-hidden names {raw!r}, not a valid YYYY-MM-DD date"
            ) from e
    return sorted(dates)


def _confessed_dates(path: str) -> set:
    """Every HIDDEN date whose confession has already been posted
    publicly, per a `<!-- gap-confessed: YYYY-MM-DD -->` marker in `path`
    -- the marker names the bug it resolves by its hidden date, not the
    (possibly later) date the confession itself was posted, so it lines
    up directly with `_hidden_dates`'s own keys. An absent file returns
    an empty set, not an error; a malformed date inside a marker that IS
    present raises loudly instead, mirroring `_hidden_dates` exactly."""
    if not os.path.isfile(path):
        return set()
    with open(path, encoding="utf-8") as f:
        text = f.read()
    dates = set()
    for m in _CONFESSED_MARKER.finditer(text):
        raw = m.group("date")
        try:
            dates.add(date.fromisoformat(raw))
        except ValueError as e:
            raise MalformedGapConfessedMarkerError(
                f"{path}: gap-confessed names {raw!r}, not a valid YYYY-MM-DD date"
            ) from e
    return dates


def _next_monday_on_or_after(d: date) -> date:
    """The nearest Monday that is `d` itself or later."""
    return d + timedelta(days=(0 - d.weekday()) % 7)


def _confession_dates_on_record(vault_dir: str) -> set:
    """Every due-date named by a pre-drafted confession file's own
    filename in `orita-vault/hand/gap-confessions/`. An absent directory
    (a fresh checkout, a vault the caller didn't attach) returns an empty
    set rather than erroring -- the same "absent is not broken, just
    unknown" shape `journal_numbering_check.py` holds for a missing
    vault checkout."""
    confessions_dir = os.path.join(vault_dir, "hand", "gap-confessions")
    if not os.path.isdir(confessions_dir):
        return set()
    dates = set()
    for name in sorted(os.listdir(confessions_dir)):
        m = _CONFESSION_FILE.match(name)
        if m:
            dates.add(date.fromisoformat(m.group("date")))
    return dates


def compute_cadence(
    readme_path: str | None = None,
    vault_dir: str | None = None,
    today: date | None = None,
) -> dict:
    """The real numbers behind Off-By-One's own half of TOWN-OPERATIONS.md's
    weekly Cluster Day ritual -- named as missing mechanism by task 463's
    research pass, never computed anywhere before.

    - total_hidden_on_record: every `gap-hidden` marker found, however old.
    - mondays_due / missed_mondays: identical window logic to
      `what_moved_check.compute_cadence` -- a hide event lands anywhere
      inside a Monday's own calendar week (Monday through the following
      Sunday), not only on the Monday's exact date (the real bug shipped
      a Thursday, three Mondays late).
    - missing_predraft: hidden bugs with no confession file on record in
      the vault at all -- a real Iron Rule violation regardless of due
      date, since the draft must exist BEFORE the bug ships.
    - confession_due_now: hidden bugs whose confession due date (the
      first Monday on or after one day past the hide date -- matches the
      one bug on record: hidden 2026-07-30, due 2026-08-03) has arrived
      or passed, a pre-drafted confession exists on record, and the
      confession has NOT already been posted publicly (ROADMAP.md #505:
      a bug carrying its own `gap-confessed` marker is done, and stays
      done -- it is never renamed here again no matter how many more
      hours pass after the fact).
    """
    readme_path = readme_path or DEFAULT_README_PATH
    vault_dir = vault_dir or DEFAULT_VAULT_DIR
    today = today or datetime.now(timezone.utc).date()

    hidden = _hidden_dates(readme_path)
    confessed = _confessed_dates(readme_path)
    mondays_due = cluster_day_check._mondays_through(today)
    mondays_due_set = set(mondays_due)
    covered = {cluster_day_check._monday_of(d) for d in hidden} & mondays_due_set
    missed = [d for d in mondays_due if d not in covered]

    predrafted = _confession_dates_on_record(vault_dir)

    missing_predraft = []
    confession_due_now = []
    for d in hidden:
        due = _next_monday_on_or_after(d + timedelta(days=1))
        if due not in predrafted:
            missing_predraft.append(d.isoformat())
        elif d in confessed:
            continue
        elif today >= due:
            confession_due_now.append({"hidden": d.isoformat(), "due": due.isoformat()})

    return {
        "total_hidden_on_record": len(hidden),
        "latest_hidden": hidden[-1].isoformat() if hidden else None,
        "mondays_due": [d.isoformat() for d in mondays_due],
        "missed_mondays": [d.isoformat() for d in missed],
        "missing_predraft": missing_predraft,
        "confession_due_now": confession_due_now,
        "confessed_on_record": sorted(d.isoformat() for d in confessed),
        "today": today.isoformat(),
    }


def format_cadence(result: dict) -> str:
    bits = []
    if result["missed_mondays"]:
        joined = ", ".join(result["missed_mondays"])
        plural = "" if len(result["missed_mondays"]) == 1 else "s"
        bits.append(f"{len(result['missed_mondays'])} Cluster Day{plural} lapsed (owed for {joined})")
    if result["missing_predraft"]:
        joined = ", ".join(result["missing_predraft"])
        bits.append(f"missing pre-drafted confession for {joined} -- Iron Rule violation")
    if result["confession_due_now"]:
        due = ", ".join(f"{c['hidden']}->{c['due']}" for c in result["confession_due_now"])
        bits.append(f"confession due now: {due}")
    if not bits:
        return (
            f"thegap cadence: current -- {result['total_hidden_on_record']} bug(s) hidden on record, "
            f"{len(result['mondays_due'])} Monday(s) owed since founding, none missed, every draft pre-written"
        )
    return (
        "thegap cadence: " + "; ".join(bits) +
        f" ({result['total_hidden_on_record']} bug(s) hidden on record)"
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    out = compute_cadence()
    print(format_cadence(out))
    sys.exit(0)
