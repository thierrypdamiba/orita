"""Serialization mechanics — turning daily Reports into a series.

A single Fencepost Report is a dispatch. Seven of them, one per day, unbroken,
is a *serial* — and a serial is the thing that gets returned to, not admired
once and closed (Retrya's + Nyx's law, STRATEGY.md "Standing laws from the
dissents": *"the tool alone is admired once; the society's serialized story
... is what retains"*). This module is the mechanic underneath that promise:
it counts installments, not gaps.

Two different numbers, on purpose, never confused with each other or with
ARC.md's wall:

- **`episode_number`** — how many distinct UTC days have ever sealed a
  tablet, counted from 1. A tablet opens whether or not a gap cleared the
  bar (`report.render_report`'s honest-quiet-day branch already covers
  that case) — so this is the installment count of the *series*, not the
  count of gaps found. Comic issue numbers don't skip an issue because
  nothing happened in it.
- **`consecutive_days`** — the unbroken daily streak counted backward from
  an anchor date (default: the latest sealed tablet). One missed UTC day
  and the streak is zero starting the day after the gap. This is the
  number the town's own promise ("seven consecutive daily reports posted",
  ROADMAP.md #19) is measured against — and it is measured, not narrated:
  a missed day makes this number fall, in public, the same way a missed
  gap makes AUDIT.md's tally fall. Nobody's story gets to claim a streak
  the tablets don't back.

Both numbers are pure functions of what is already sealed in `GAPS/` — no
new state, no new file to keep honest, nothing that can drift from the
Ledger it reads. Read-only, like everything here: this module writes
nothing, ever.

The `episode`/`streak_days` values this module computes are handed to
`report.render_report` as plain optional numbers — the report stays a pure
function of its inputs (report.py's own law); this module is simply where
those two inputs come from when a report is rendered for real, off the live
ledger, instead of built by hand in a test.

Recorded, then told. — Kwaku Ananse
"""
from __future__ import annotations

from datetime import date, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any

from seam_engine import ledger

# The town's own promise (ROADMAP.md #19, STRATEGY.md "Serialized Narrative
# & @oritatown"): seven consecutive daily reports is a proven cadence, not a
# round number picked for its own sake — a week is the smallest unit a reader
# can recognize as "this actually happens every day," which is the whole
# claim the "connect your own" ad on every report is trading on.
SEVEN_DAY_STREAK = 7


def _tablet_dates(base: Path | None = None) -> list[date]:
    """Every UTC day that has a sealed tablet, ascending, deduplicated.

    Reads the same tablet files `ledger.read_records` does (one `.md` per
    UTC day, named `YYYY-MM-DD.md`) but only needs the filenames, not the
    typed records inside them — a day either opened a tablet or it didn't.

    `ledger._tablet_files`' own filter (a fullmatch against four digits,
    dash, two digits, dash, two digits) is a digit-shape check, not a real
    calendar-date one — `2026-02-30` and
    `2026-13-01` both match it. A hand-edited or typo'd tablet name with that
    shape is skipped here rather than crashing every caller
    (`episode_number`, `consecutive_days`, `longest_streak`, and
    `report.render_latest`, which calls this unconditionally for the town's
    real daily Report) with an uncaught `ValueError` — the same
    "skip a malformed entry, never let it break the whole read" discipline
    `metrics_cadence_check._read_dates`/`report_cadence_check._shipped_dates`
    already hold for their own date-bearing sources.
    """
    dates: set[date] = set()
    for path in ledger._tablet_files(base):
        try:
            year, month, day = (int(part) for part in path.stem.split("-"))
            dates.add(date(year, month, day))
        except ValueError:
            continue
    return sorted(dates)


def episode_number(base: Path | None = None) -> int:
    """The installment number of the *latest* tablet in the series.

    Every distinct day that ever sealed a tablet counts once, whether or
    not a gap cleared the bar that day — a quiet day still shipped a
    report (`report.render_report`'s no-primary-gap branch), so it still
    ships an episode. Zero if the ledger has never been opened.
    """
    return len(_tablet_dates(base))


def consecutive_days(base: Path | None = None, *, today: date | None = None) -> int:
    """The current unbroken daily streak, counted backward from `today`.

    Defaults to the latest sealed tablet date when `today` is not given —
    the honest anchor for "as of the most recent report," not the actual
    calendar date, which lets tests (and any day the workflow itself was
    late) reason about the streak without needing to mock the clock. Walks
    backward one UTC day at a time; the first day with no tablet stops the
    count. A ledger with no tablets at all has a streak of zero.
    """
    dates = _tablet_dates(base)
    if not dates:
        return 0
    anchor = today if today is not None else dates[-1]
    present = set(dates)
    streak = 0
    cursor = anchor
    while cursor in present:
        streak += 1
        cursor = cursor - timedelta(days=1)
    return streak


def longest_streak(base: Path | None = None) -> int:
    """The longest unbroken run the series has ever held, not just the
    current one — the record the town is trying to beat, not merely hold.
    """
    dates = _tablet_dates(base)
    if not dates:
        return 0
    longest = 1
    current = 1
    for prev, cur in pairwise(dates):
        if cur - prev == timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def is_seven_day_streak(base: Path | None = None, *, today: date | None = None) -> bool:
    """Has the series held SEVEN_DAY_STREAK consecutive days, unbroken?

    This is the literal test of ROADMAP.md #19's done-when: "Seven
    consecutive daily reports posted." It reads only what the Ledger has
    actually sealed — there is no way to make this `True` except by the
    daily Action actually running, seven days running, with no gap.
    """
    return consecutive_days(base, today=today) >= SEVEN_DAY_STREAK


def streak_status(base: Path | None = None, *, today: date | None = None) -> dict[str, Any]:
    """Everything a caller needs to render or check the series' state, in
    one typed dict. Pure — reads the Ledger, computes, returns; writes
    nothing.
    """
    days = consecutive_days(base, today=today)
    episode = episode_number(base)
    return {
        "episode": episode,
        "streak_days": days,
        "longest_streak": longest_streak(base),
        "target": SEVEN_DAY_STREAK,
        "seven_day_streak": days >= SEVEN_DAY_STREAK,
        "days_remaining": max(SEVEN_DAY_STREAK - days, 0),
    }


# --- CLI ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import json
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)

    base: Path | None = None
    if "--base" in argv:
        i = argv.index("--base")
        if i + 1 >= len(argv):
            print("--base needs a path to a Ledger directory.")
            return 2
        base = Path(argv[i + 1])
        del argv[i : i + 2]

    cmd = argv[0] if argv else "status"

    if cmd == "status":
        status = streak_status(base)
        print(json.dumps(status, indent=2))
        if status["seven_day_streak"]:
            print(
                f"\nSeven days, unbroken. Episode {status['episode']}. "
                "The serial holds — recorded, not merely claimed.",
                file=sys.stderr,
            )
        else:
            print(
                f"\nDay {status['streak_days']} of {SEVEN_DAY_STREAK}. "
                f"{status['days_remaining']} to go before the streak is proven, "
                "not just underway.",
                file=sys.stderr,
            )
        return 0

    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
