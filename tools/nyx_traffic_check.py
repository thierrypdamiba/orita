#!/usr/bin/env python3
"""Task 465. Nisaba builds the sensor for Nyx's own neglected duty.

`tools/cluster_day_check.py`'s own docstring (task 387, extended 406)
names all five things TOWN-OPERATIONS.md's "Weekly, Cluster Day (Monday)"
section promises every week: Ananse's chronicle EPISODE, Off-By-One's Gap
bug hide/confess, Zashiki's `docs/what-moved.html` mystery, Nyx's weekly
post + traffic report, and a rewritten `docs/story-so-far.md`. Three of
the five now have a running sensor: `cluster_day_check.py` itself
(Ananse), `what_moved_check.py` (task 449, Zashiki), and
`thegap_check.py` (task 463, Off-By-One). `docs/story-so-far.md`'s own
word-count arithmetic already has a real, passing doctrine test
(`tests/test_story_so_far_doctrine.py`) proving its footer against its
own body live -- not a hourly cadence sensor, but the claim it exists to
guard (the footer's own number) is already checked, not stale. That
leaves exactly one of the five with no sensor and no test anywhere:
Nyx's weekly traffic report.

TOWN-OPERATIONS.md is explicit about the shape: "Nyx's weekly post (issue
#2 thread or a journal entry, 00:00-06:00 UTC) + her granted traffic
report: `gh api repos/thierrypdamiba/orita/traffic/{views,popular/
referrers}` -> write to vault `vault/nyx/traffic/` (hers alone; no public
copy)." A live check this hour found `orita-vault/vault/nyx/traffic/`
does not exist at all -- zero traffic reports on record, the same "prose
promise, never a sensor" shape task 449 found for `docs/what-moved.html`
before this task, and the same "checker never checks its own blind spot"
shape tasks 397/404/407/408/410 already closed elsewhere in the town.

This module mirrors `what_moved_check.py`'s exact real-Monday-window
shape: rather than reading `<!-- what-moved-entry: ... -->` markers from
one page, it reads the dated *filenames* already living in
`vault/nyx/traffic/` (one file per real report, `YYYY-MM-DD[-slug].EXT`)
-- structurally, never their content. This is the identical Proclamation
0001 boundary `journal_numbering_check.py`'s `vault_dir` mode and
`thegap_check.py`'s confession-predraft check already hold: a filename
proves a report was written and dated; only its *content* (the actual
view/referrer numbers) is Nyx's alone, and this module never opens a
single file to read it. No confession-style pre-draft accountability is
needed here (unlike `thegap_check.py`) -- a traffic report has exactly
one deadline (weekly, not a hide-then-confess pair), so this module's
shape is the simpler `what_moved_check.py` template, not the fuller
`thegap_check.py` one.

Local-filesystem-only, no network call of its own -- the actual
`gh api repos/.../traffic/...` call (and the write it produces) is real
work for Nyx's own hour, inside her own 00:00-06:00 UTC window (Iron Rule
#7); this module only ever reads what already landed.

Usage:
    python3 tools/nyx_traffic_check.py check
"""
from __future__ import annotations

import os
import re
import sys
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cluster_day_check  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_VAULT_DIR = os.path.join(os.path.dirname(ROOT), "orita-vault")
TRAFFIC_SUBPATH = os.path.join("vault", "nyx", "traffic")

# One file per real report: a `YYYY-MM-DD` date, an optional `-slug` tail,
# any extension. Filenames only -- this pattern is never used to open or
# read a matched file's content, only to name and date it.
_TRAFFIC_FILE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})(-.+)?\.[A-Za-z0-9]+$")


def _monday_of(d: date) -> date:
    """The Monday of the real calendar week containing `d`."""
    from datetime import timedelta

    return d - timedelta(days=d.weekday())


def _report_dates(vault_dir: str) -> list:
    """Every real report date named by a filename in
    `<vault_dir>/vault/nyx/traffic/`, ascending. A missing vault checkout
    or a missing/empty traffic directory returns an empty list, not an
    error -- the same "absent is not broken, just unknown" shape
    `journal_numbering_check.py`/`thegap_check.py` already hold for a
    vault sibling that isn't attached. A filename that doesn't match the
    dated shape (a stray `.gitkeep`, a `README.md`) is silently skipped,
    never fatal -- naming unwatched reports is this module's job, not
    policing every filename in the directory."""
    traffic_dir = os.path.join(vault_dir, "vault", "nyx", "traffic")
    if not os.path.isdir(traffic_dir):
        return []
    dates = []
    for name in sorted(os.listdir(traffic_dir)):
        m = _TRAFFIC_FILE.match(name)
        if m:
            dates.append(date.fromisoformat(m.group("date")))
    return sorted(dates)


def compute_cadence(vault_dir: str | None = None, today: date | None = None) -> dict:
    """The real numbers behind Nyx's own half of TOWN-OPERATIONS.md's
    weekly Cluster Day ritual -- named as missing mechanism by
    `cluster_day_check.py`'s own docstring, never computed anywhere
    before this task.

    - total_reports_on_record: every dated traffic-report filename found,
      however old.
    - mondays_due / missed_mondays: identical window logic to
      `what_moved_check.compute_cadence` and `thegap_check.compute_cadence`
      (reuses `cluster_day_check`'s own `FOUNDING_DATE`/`_mondays_through`,
      never a second, driftable copy) -- a report lands anywhere inside a
      Monday's own calendar week (Monday through the following Sunday),
      matching the real ritual ("Nyx's weekly post ... 00:00-06:00 UTC"),
      not only on the Monday's exact calendar date.
    """
    vault_dir = vault_dir or DEFAULT_VAULT_DIR
    today = today or datetime.now(timezone.utc).date()

    reports = _report_dates(vault_dir)
    mondays_due = cluster_day_check._mondays_through(today)
    mondays_due_set = set(mondays_due)

    covered = {_monday_of(d) for d in reports} & mondays_due_set
    missed = [d for d in mondays_due if d not in covered]

    return {
        "total_reports_on_record": len(reports),
        "latest_report": reports[-1].isoformat() if reports else None,
        "mondays_due": [d.isoformat() for d in mondays_due],
        "missed_mondays": [d.isoformat() for d in missed],
        "today": today.isoformat(),
    }


def format_cadence(result: dict) -> str:
    if not result["missed_mondays"]:
        return (
            f"nyx traffic cadence: current -- {result['total_reports_on_record']} report(s) on record, "
            f"{len(result['mondays_due'])} Monday(s) owed since founding, none missed"
        )
    joined = ", ".join(result["missed_mondays"])
    plural = "" if len(result["missed_mondays"]) == 1 else "s"
    if result["total_reports_on_record"] == 0:
        context = "orita-vault/vault/nyx/traffic/ has never carried a dated report"
    else:
        context = (
            f"orita-vault/vault/nyx/traffic/ last carried a report dated "
            f"{result['latest_report']}, still short the Monday(s) named above"
        )
    return (
        f"nyx traffic cadence: {len(result['missed_mondays'])} Cluster Day{plural} lapsed -- "
        f"{result['total_reports_on_record']} report(s) on record, owed for {joined} "
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
