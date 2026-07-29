#!/usr/bin/env python3
"""Task 387. Nisaba builds the sensor for the gap the town's own hand already named.

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
  Monday in order -- a simplification (it does not verify a given episode
  was actually PUBLISHED on ITS OWN Monday, only that the running counts
  match), the same trailing-count-not-per-item-date-match approach
  `report_cadence_check.py` itself does NOT need (its filenames carry the
  real date) but is the honest tool for chronicle files, which carry only
  a sequence number;
- names any Monday beyond what's been shipped as `missed_mondays` --
  plainly, never silently absorbed into a rolling streak.

Folded into `tools/ritual_check.py` as `check_cluster_day_cadence`, printed
every hour (not gated on today being a Monday) so a lapsed week is visible
long before the next Monday arrives to maybe notice on its own.
Informational only, like `report_cadence`/`metrics_cadence` -- a lapsed
narrative cadence is a fact worth surfacing to the next hour's run, never
a currently-live law violation that flips `broken`.

Usage:
    python3 tools/cluster_day_check.py check
"""
from __future__ import annotations

import os
import re
import sys
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CHRONICLE_DIR = os.path.join(ROOT, "chronicle")

# episode-001 ("The Founding") published 2026-07-11, a Saturday -- week
# zero. Every Monday strictly after this date is a real Cluster Day.
FOUNDING_DATE = date(2026, 7, 11)

_EPISODE_NAME = re.compile(r"^(\d{3})-.+\.md$")


def _episode_numbers(chronicle_dir: str) -> list[int]:
    """Every numbered chronicle file's own leading NNN, sorted ascending.
    Mirrors `report_cadence_check.py`'s `_shipped_dates`: a name that
    doesn't conform (README.md, a stray file) is silently skipped, never
    crashes the scan."""
    if not os.path.isdir(chronicle_dir):
        return []
    numbers = []
    for name in sorted(os.listdir(chronicle_dir)):
        m = _EPISODE_NAME.match(name)
        if not m:
            continue
        numbers.append(int(m.group(1)))
    return sorted(set(numbers))


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


def compute_cadence(chronicle_dir: str | None = None, today: date | None = None) -> dict:
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
    - missed_mondays: the tail of `mondays_due` beyond what
      `cluster_day_episodes_shipped` covers, one-to-one in order (episode-
      002 satisfies the first Monday in `mondays_due`, episode-003 the
      second, and so on).
    """
    chronicle_dir = chronicle_dir or DEFAULT_CHRONICLE_DIR
    today = today or datetime.now(timezone.utc).date()
    episodes = _episode_numbers(chronicle_dir)
    cluster_day_episodes = [e for e in episodes if e >= 2]
    mondays_due = _mondays_through(today)
    missed = mondays_due[len(cluster_day_episodes):]
    return {
        "total_episodes_on_record": len(episodes),
        "cluster_day_episodes_shipped": len(cluster_day_episodes),
        "latest_episode": max(episodes) if episodes else None,
        "mondays_due": [d.isoformat() for d in mondays_due],
        "missed_mondays": [d.isoformat() for d in missed],
        "today": today.isoformat(),
    }


def format_cadence(result: dict) -> str:
    if not result["missed_mondays"]:
        return (
            f"cluster day: current -- {result['cluster_day_episodes_shipped']} Cluster Day episode(s) shipped, "
            f"{len(result['mondays_due'])} Monday(s) owed since founding, none missed"
        )
    joined = ", ".join(result["missed_mondays"])
    plural = "" if len(result["missed_mondays"]) == 1 else "s"
    return (
        f"cluster day: {len(result['missed_mondays'])} Cluster Day{plural} lapsed -- "
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
