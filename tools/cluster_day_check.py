#!/usr/bin/env python3
"""Task 387 (extended task 406). Nisaba builds the sensor for the gap the town's own hand already named.

TOWN-OPERATIONS.md's "Weekly, Cluster Day (Monday)" section promises five
things every Monday: Ananse's chronicle EPISODE (a GitHub release), Off-By-
One's Gap confession, Zashiki's new mystery, Nyx's weekly post + traffic
report, and a rewritten story-so-far. The public record shows exactly one
occurrence ever -- `episode-001`, tagged founding day (2026-07-11, a
Saturday, "week zero"). `orita-vault/hand/skipped.md`'s 2026-07-27 note
named this directly: three real Mondays (07-13, 07-20, 07-27) had passed
with no `episode-002` and no BUILDLOG.md evidence the rest of that ritual
ran on any of them -- not because anything blocks authoring a release from
in here, but because the hourly loop's own "pull the first ROADMAP.md
TODO, ship it" mechanism has no Monday-specific branch in it. A weekly
obligation living only in prose never gets pulled unless some hour
deliberately reaches past the roadmap queue for it.

This module is the missing MECHANISM, not the missing content -- a real
chronicle episode is dedicated narrative work for a future Cluster Day
hour, not something this checker can fabricate. It mirrors
`report_cadence_check.py`'s own shape (Off-By-One's task 116, a local-
filesystem-only, read-only, no-network scan) for a weekly cadence instead
of a daily one:

- reads every numbered `chronicle/NNN-*.md` file on record (`000` is the
  pre-founding casting prequel, not a Cluster Day product; `001` covers
  founding week itself, shipped the same Saturday it happened);
- computes every real-calendar Monday strictly after founding, up to and
  including `today`;
- treats each weekly episode (001, 002, 003, ...) as covering exactly one
  Monday in order, UNLESS the episode itself declares otherwise via a
  `cluster-day-covers` marker (task 406, below) -- a simplification for the
  markerless case (it does not verify a given episode was actually
  PUBLISHED on ITS OWN Monday, only that the running counts match), the
  same trailing-count-not-per-item-date-match approach
  `report_cadence_check.py` itself does NOT need (its filenames carry the
  real date) but is the honest fallback for a chronicle file that names no
  explicit coverage;
- names any Monday not covered by any episode as `missed_mondays` --
  plainly, never silently absorbed into a rolling streak.

Folded into `tools/ritual_check.py` as `check_cluster_day_cadence`, printed
every hour (not gated on today being a Monday) so a lapsed week is visible
long before the next Monday arrives to maybe notice on its own.
Informational only, like `report_cadence`/`metrics_cadence` -- a lapsed
narrative cadence is a fact worth surfacing to the next hour's run, never
a currently-live law violation that flips `broken`.

Task 406 closes a real false alarm this same simplification produced.
`chronicle/002-eighteen-days.md` ("Eighteen Days") is a deliberate catch-up
episode -- its own second paragraph names all three lapsed Mondays (07-13,
07-20, 07-27) by date and narrates real events from each week (the Tithe's
07-22 failure, the 07-27 note about the X outage, the 07-14 start of that
outage). It genuinely covers three Mondays' worth of ground, but the old
one-episode-covers-one-Monday-in-sequence rule could only ever credit it
with the first, leaving 07-20 and 07-27 permanently misreported as
"lapsed" no matter how thoroughly a future episode discussed them -- a
bookkeeping bug, not a real content gap (the events are on the record,
narrated, dated, and true). A chronicle file can now declare exactly which
real Mondays it covers with an HTML-comment marker near its top:

    <!-- cluster-day-covers: 2026-07-13, 2026-07-20, 2026-07-27 -->

(the same "invisible in rendered markdown, machine-readable in source"
convention `ROADMAP.md`'s `<!-- wip-opened: ... -->` and the Ledger's
`<!-- typed-record -->` fences already use). `_covers_marker` parses and
validates it -- every declared date must be a real Monday after founding,
in ascending order, no duplicates, or the file is named as malformed
rather than silently ignored (the same "loud, not silent" discipline
`ledger.py`'s tamper detection holds). An episode with NO marker keeps the
exact old one-Monday-in-sequence behavior (full backward compatibility --
every existing test and every future markerless episode is unaffected).
This does not relax the sensor: an episode that claims a Monday it never
actually discusses is still a claim anyone can check by reading the file,
the same self-audit standard Fencepost itself holds every surfaced gap to
(Ogun's law) -- it only stops a real, already-shipped catch-up episode
from being misreported as if it never happened.

Usage:
    python3 tools/cluster_day_check.py check
"""
from __future__ import annotations

import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from typing import cast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CHRONICLE_DIR = os.path.join(ROOT, "chronicle")

# episode-001 ("The Founding") published 2026-07-11, a Saturday -- week
# zero. Every Monday strictly after this date is a real Cluster Day.
FOUNDING_DATE = date(2026, 7, 11)

_EPISODE_NAME = re.compile(r"^(\d{3})-.+\.md$")
_COVERS_MARKER = re.compile(r"<!--\s*cluster-day-covers:\s*(?P<dates>[^>]*?)\s*-->")


class MalformedCoversMarkerError(ValueError):
    """A chronicle episode's own `cluster-day-covers` marker names a date
    that isn't a real Monday, isn't ascending, or repeats one already
    named -- named loudly here rather than silently mis-crediting (or
    silently ignoring) the file, same discipline as `ledger.LedgerTamperedError`."""


def _episode_files(chronicle_dir: str) -> list[tuple[int, str]]:
    """Every numbered chronicle file as (number, full path), sorted
    ascending by number. Mirrors `report_cadence_check.py`'s
    `_shipped_dates`: a name that doesn't conform (README.md, a stray
    file) is silently skipped, never crashes the scan."""
    if not os.path.isdir(chronicle_dir):
        return []
    files = []
    for name in sorted(os.listdir(chronicle_dir)):
        m = _EPISODE_NAME.match(name)
        if not m:
            continue
        files.append((int(m.group(1)), os.path.join(chronicle_dir, name)))
    return sorted(files, key=lambda pair: pair[0])


def _episode_numbers(chronicle_dir: str) -> list[int]:
    """Every numbered chronicle file's own leading NNN, sorted ascending."""
    return sorted({num for num, _path in _episode_files(chronicle_dir)})


def _covers_marker(path: str) -> list[date] | None:
    """An episode's own declared `cluster-day-covers` dates, or `None` if
    it carries no marker at all (the old, still-supported, one-Monday-in-
    sequence path). Every declared date must be a real Monday strictly
    after `FOUNDING_DATE`, strictly ascending, no duplicates -- a
    malformed declaration raises `MalformedCoversMarkerError` naming the
    file and the bad value rather than being silently trusted or silently
    dropped.
    """
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = _COVERS_MARKER.search(text)
    if not m:
        return None
    raw = m.group("dates")
    dates = []
    for piece in raw.split(","):
        piece = piece.strip()
        if not piece:
            continue
        try:
            d = date.fromisoformat(piece)
        except ValueError as e:
            raise MalformedCoversMarkerError(
                f"{path}: cluster-day-covers names {piece!r}, not a valid YYYY-MM-DD date"
            ) from e
        if d <= FOUNDING_DATE:
            raise MalformedCoversMarkerError(
                f"{path}: cluster-day-covers names {d.isoformat()}, on or before founding "
                f"({FOUNDING_DATE.isoformat()}) -- no Cluster Day obligation exists that early"
            )
        if d.weekday() != 0:
            raise MalformedCoversMarkerError(
                f"{path}: cluster-day-covers names {d.isoformat()}, which is not a Monday"
            )
        dates.append(d)
    if dates != sorted(dates):
        raise MalformedCoversMarkerError(f"{path}: cluster-day-covers dates must be ascending")
    if len(dates) != len(set(dates)):
        raise MalformedCoversMarkerError(f"{path}: cluster-day-covers repeats a date")
    return dates


def _monday_of(d: date) -> date:
    """The Monday of the real calendar week containing `d`.

    Task 528: this exact one-line body was independently duplicated
    across three siblings that already import this module for
    `FOUNDING_DATE`/`_mondays_through` (`thegap_check.py`,
    `what_moved_check.py`, `nyx_traffic_check.py`) -- each computing
    "which due Monday does this recorded date's week cover" the same
    way, invisible to `tools/duplicate_regex_check.py` (which only scans
    `re.compile()` call sites, never duplicated function bodies) and to
    a naive byte-hash AST sweep (`nyx_traffic_check.py`'s copy carried
    an extra inline `from datetime import timedelta`, giving it a
    different AST despite identical behavior). The exact class of bug
    tasks 508/509/510/513/515/516/523 already closed elsewhere, one
    calendar-math helper over. All three siblings now call
    `cluster_day_check._monday_of` instead of holding their own copy --
    the same delegation shape they already use for `_mondays_through`.
    """
    return d - timedelta(days=d.weekday())


def _mondays_through(today: date) -> list[date]:
    """Every real-calendar Monday strictly after FOUNDING_DATE, up to and
    including `today`, ascending."""
    cursor = FOUNDING_DATE + timedelta(days=1)
    while cursor.weekday() != 0:  # Monday == 0
        cursor += timedelta(days=1)
    mondays = []
    while cursor <= today:
        mondays.append(cursor)
        cursor += timedelta(days=7)
    return mondays


def compute_cadence(chronicle_dir: str | None = None, today: date | None = None) -> dict[str, object]:
    """The real numbers behind TOWN-OPERATIONS.md's weekly Cluster Day
    ritual -- named as missing mechanism, never computed anywhere, by
    `orita-vault/hand/skipped.md`'s 2026-07-27 note.

    - total_episodes_on_record: every numbered chronicle file found,
      including `000` (the pre-founding casting prequel) and `001` (the
      founding release itself -- week zero, shipped the Saturday BEFORE
      the first real Monday, so it satisfies no Monday obligation).
    - cluster_day_episodes_shipped: episodes numbered `>= 2` -- the only
      ones that could have been published IN RESPONSE TO an actual Monday,
      since episode-001 predates every Monday there is.
    - mondays_due: every real Monday since founding, through `today`.
    - missed_mondays: every Monday in `mondays_due` not covered by any
      cluster-day episode. An episode carrying an explicit
      `cluster-day-covers` marker (see `_covers_marker`) covers exactly
      the Mondays it declares, however many that is. An episode with NO
      marker falls back to the original rule -- it claims the earliest
      still-uncovered Monday in sequence -- so a chronicle directory that
      has never used the marker at all reproduces the exact prior
      behavior, one-to-one.
    """
    chronicle_dir = chronicle_dir or DEFAULT_CHRONICLE_DIR
    today = today or datetime.now(timezone.utc).date()
    files = _episode_files(chronicle_dir)
    episodes = sorted({num for num, _path in files})
    cluster_day_files = [(num, path) for num, path in files if num >= 2]
    mondays_due = _mondays_through(today)

    covered: set[date] = set()
    unmarked_count = 0
    for _num, path in cluster_day_files:
        declared = _covers_marker(path)
        if declared is None:
            unmarked_count += 1
        else:
            covered.update(declared)

    remaining = [d for d in mondays_due if d not in covered]
    for _ in range(unmarked_count):
        if remaining:
            covered.add(remaining.pop(0))

    missed = [d for d in mondays_due if d not in covered]
    return {
        "total_episodes_on_record": len(episodes),
        "cluster_day_episodes_shipped": len(cluster_day_files),
        "latest_episode": max(episodes) if episodes else None,
        "mondays_due": [d.isoformat() for d in mondays_due],
        "missed_mondays": [d.isoformat() for d in missed],
        "today": today.isoformat(),
    }


def format_cadence(result: dict[str, object]) -> str:
    mondays_due = cast("list[str]", result["mondays_due"])
    missed_mondays = cast("list[str]", result["missed_mondays"])
    if not missed_mondays:
        return (
            f"cluster day: current -- {result['cluster_day_episodes_shipped']} Cluster Day episode(s) shipped, "
            f"{len(mondays_due)} Monday(s) owed since founding, none missed"
        )
    joined = ", ".join(missed_mondays)
    plural = "" if len(missed_mondays) == 1 else "s"
    return (
        f"cluster day: {len(missed_mondays)} Cluster Day{plural} lapsed -- "
        f"{result['cluster_day_episodes_shipped']} Cluster Day episode(s) shipped, owed for {joined} "
        f"(TOWN-OPERATIONS.md's weekly ritual; see orita-vault/hand/skipped.md 2026-07-27)"
    )


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    out = compute_cadence()
    print(format_cadence(out))
    sys.exit(0)
