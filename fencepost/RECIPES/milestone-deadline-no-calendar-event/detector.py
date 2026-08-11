"""Seventy-ninth real seam recipe: a GitHub milestone has a due date, but no
Google Calendar event was ever created to track it.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads two local fixture files
(`milestones.json`, `events.json`), shaped like what `ListMilestones` and
`ListEvents` would actually return. `ListMilestones` already sits on
`SCOPES.md`'s cleared oath table (used by `overdue-milestone-still-open`
and the whole `*-claims-open-milestone` family); `ListEvents` sits there
too (the "Google Calendar (v0.2)" row) but has never once been declared
by any recipe until this one -- this is the first recipe in the tree to
name a Google Calendar scope at all, confirmed by grep across every
`RECIPES/*/recipe.json` before it (zero hits for `"google_calendar"` or
`"ListEvents"`/`"GetEvent"` as a declared scope). Zero Google Calendar
tools are exposed on the-hand's live gateway today (the same
"registered on the Oath, not yet wired into the gateway" shape
`gmail_calendar.py`'s own module docstring already lives by, and the
identical WIP note `tag-never-released` left for `ListTags`/`ListReleases`
one recipe ago).

The seam: GitHub's milestone object carries its own `due_on` field, and
renders it in red on the milestone's own page once it passes -- but
that is decoration. Nothing in the API or UI ever creates, or even
suggests creating, a calendar entry for it. A deadline that lives only
inside GitHub's own record is invisible to whatever a human actually
glances at each morning; only holding `ListMilestones` and `ListEvents`
at once, matched by keyword and a window around the date, shows the gap
between "GitHub knows about this deadline" and "something will actually
remind a human of it."

Genuinely distinct from every recipe that already reads `ListMilestones`:
`overdue-milestone-still-open` (the 33rd real recipe) asks whether a
milestone's own due date has passed while it is STILL OPEN -- a
same-object, same-account comparison entirely inside GitHub's own
record. This recipe asks an orthogonal question that `overdue-milestone-
still-open` cannot: regardless of whether the milestone is overdue yet,
does anything OUTSIDE GitHub exist to remind a human the date is coming?
A milestone can be perfectly on-time (not yet due) and still carry this
gap; a milestone that is badly overdue can also carry this gap. The two
recipes can both fire on the very same milestone, for two different
reasons, the same way `tag-never-released` and `example-release-vs-
changelog` can both fire on two different objects derived from the same
release. It is also distinct from the whole `*-claims-open-milestone`
family (`commit-claims-open-milestone`, `tweet-claims-open-milestone`,
and siblings): those read a THIRD record's own prose claim ("milestone
#N") and check it against the milestone's live state; this recipe never
reads any prose claim at all, and crosses toolkits (`github` and
`google_calendar`) where every member of that family stays
single-toolkit (`github`) or pairs `github` with `x`/`slack`/`linear`.

Matching is keyword-plus-window, the same two-signal shape
`gmail_calendar.compute_gaps`'s own `_find_match` already established for
its Gmail-vs-Calendar seam (title keyword overlap alone is too weak --
two unrelated deadlines a week apart could share a generic word; a date
window alone is too weak -- two unrelated milestones could fall due the
same week): a Calendar event counts as tracking a milestone's deadline
only if its own title shares a real keyword (`seam_engine.scan._keywords`,
the same stopword-filtered tokenizer `gmail_calendar.py` already uses)
with the milestone's title AND its `start` falls within `_DUE_WINDOW`
(3 days, wider than `gmail_calendar`'s own 2-hour `TIME_TOLERANCE` on
purpose -- a milestone deadline is a day-granularity promise, a meeting
invite is a minute-granularity one; matching this recipe's own precision
to its own object type, not borrowing a neighbor's number that fits a
different one).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate, _keywords

_HERE = Path(__file__).resolve().parent
DEFAULT_MILESTONES_FIXTURE = _HERE.parents[1] / "fixtures" / "milestone_deadline_no_calendar_event" / "milestones.json"
DEFAULT_EVENTS_FIXTURE = _HERE.parents[1] / "fixtures" / "milestone_deadline_no_calendar_event" / "events.json"

# A Calendar event tracks a milestone's due date only if its own `start`
# falls within this many days of `due_on`, either direction -- wide enough
# that a reminder set a day or two early (or a wrap-up event set a day or
# two late) still counts, narrow enough that an unrelated event the same
# month does not. Day-granularity on purpose: a milestone due date is
# itself a bare date, not a timestamped meeting.
_DUE_WINDOW = timedelta(days=3)

# A milestone due within this many days of the scan clock (past or future)
# is judged urgent: either the window to add a reminder before the deadline
# hits is closing fast, or the deadline recently passed with nothing ever
# having tracked it. Further out than this, there is still comfortable time
# left, so the missing calendar entry is weighed in the tail, not surfaced
# as an immediate miss -- mirrors the binary stale/fresh gate every
# `*-still-open`/`*-never-released` sibling already uses, applied to
# distance-from-due-date instead of hours-since-due-date.
_URGENT_DAYS = 7.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    due_on: datetime | None
    open_issues: int
    closed_issues: int
    url: str


@dataclass
class CalendarEvent:
    id: str
    title: str
    start: datetime
    organizer: str
    source: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_milestones(path: Path | None = None) -> list[Milestone]:
    rows = _load_rows(path or DEFAULT_MILESTONES_FIXTURE)
    return [
        Milestone(
            number=r["number"],
            title=r["title"],
            state=r["state"],
            due_on=_parse_ts(r["due_on"]) if r.get("due_on") else None,
            open_issues=r.get("open_issues", 0),
            closed_issues=r.get("closed_issues", 0),
            url=r["url"],
        )
        for r in rows
    ]


def load_events(path: Path | None = None) -> list[CalendarEvent]:
    rows = _load_rows(path or DEFAULT_EVENTS_FIXTURE)
    return [
        CalendarEvent(
            id=r["id"],
            title=r["title"],
            start=_parse_ts(r["start"]),
            organizer=r.get("organizer", "unknown"),
            source=r.get("source", "calendar"),
        )
        for r in rows
    ]


def _find_match(milestone: Milestone, events: list[CalendarEvent]) -> CalendarEvent | None:
    """A Calendar event matches a milestone's deadline if its own `start`
    lands within `_DUE_WINDOW` of `due_on` AND its title shares a real
    keyword with the milestone's title -- either signal alone is too weak,
    the identical two-signal reasoning `gmail_calendar._find_match` already
    holds for its own Gmail-vs-Calendar seam. Raises if called with
    `milestone.due_on is None`; callers only reach this after already
    excluding a milestone with no due date."""
    if milestone.due_on is None:
        raise ValueError(
            f"_find_match(): milestone #{milestone.number} reached the matcher "
            "with due_on=None -- callers must filter that out first."
        )
    milestone_kw = _keywords(milestone.title)
    for ev in events:
        if abs((ev.start - milestone.due_on).total_seconds()) > _DUE_WINDOW.total_seconds():
            continue
        if _keywords(ev.title) & milestone_kw:
            return ev
    return None


def compute_gaps(
    milestones: list[Milestone], events: list[CalendarEvent], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. A milestone is excluded, named not hidden, the moment
    it is closed, carries no due_on, or already has a matching Calendar
    event; everything left over is age-gated on how close its own due_on
    sits to `now`, in either direction."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for m in sorted(milestones, key=lambda m: m.number):
        if m.state != "open":
            excluded.append(GapCandidate(
                slug=f"not-open-{m.number}",
                headline=f"Milestone #{m.number} ('{m.title}') already reads closed",
                detail=(
                    f"Milestone #{m.number} is closed. Whatever its due date promised, "
                    "the work resolved -- no seam here."
                ),
                confidence=0.0,
                evidence=[m.url],
            ))
            continue

        if m.due_on is None:
            excluded.append(GapCandidate(
                slug=f"no-due-date-{m.number}",
                headline=f"Milestone #{m.number} ('{m.title}') carries no due date",
                detail=f"Milestone #{m.number} has no due_on set. No deadline, no seam.",
                confidence=0.0,
                evidence=[m.url],
            ))
            continue

        match = _find_match(m, events)
        if match is not None:
            excluded.append(GapCandidate(
                slug=f"calendar-matched-{m.number}",
                headline=f"Milestone #{m.number} ('{m.title}')'s deadline already has a Calendar event",
                detail=(
                    f"Milestone #{m.number}'s due_on ({m.due_on.isoformat()}) matches calendar "
                    f"event {match.id} ('{match.title}') within {_DUE_WINDOW}. No seam here."
                ),
                confidence=0.0,
                evidence=[m.url, f"calendar:{match.id}"],
            ))
            continue

        days_from_due = abs((m.due_on - now).total_seconds()) / 86400.0
        confidence = 0.85 if days_from_due <= _URGENT_DAYS else 0.5
        when = "still upcoming" if m.due_on >= now else "already passed"
        surfaced.append(GapCandidate(
            slug=f"milestone-deadline-no-calendar-event-{m.number}",
            headline=(
                f"Milestone #{m.number} ('{m.title}') is due {m.due_on.date()}, "
                "no Calendar event tracks it"
            ),
            detail=(
                f"Milestone #{m.number} ('{m.title}') is due {m.due_on.isoformat()} "
                f"({when}, {days_from_due:.1f} day(s) from the scan clock) with "
                f"{m.open_issues} open issue(s) against {m.closed_issues} closed. No "
                f"Calendar event within {_DUE_WINDOW} shares a keyword with its title -- "
                "GitHub renders the date in red on the milestone's own page but never "
                "creates, or suggests creating, a reminder anywhere else."
            ),
            confidence=confidence,
            evidence=[m.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    milestones_path: Path | None = None,
    events_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListMilestones`/`ListEvents` read and these two loaders are swapped
    for real reads. The detection logic does not change when that
    happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    milestones = load_milestones(milestones_path)
    events = load_events(events_path)
    surfaced, excluded = compute_gaps(milestones, events, now=now)
    ranking = rank(surfaced)
    primary = ranking.primary

    return {
        "generated_at": now.isoformat(),
        "source": "fixture",
        "confidence_bar": ranking.confidence_bar,
        "separation_margin": ranking.separation_margin,
        "primary_gap": asdict(primary) if primary else None,
        "tail": [asdict(g) for g in ranking.tail],
        "excluded": [asdict(g) for g in excluded],
    }


if __name__ == "__main__":
    import sys
    print(json.dumps(run_recipe_scan(), indent=2, default=str))
    sys.exit(0)
