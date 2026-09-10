"""The hundred-fifth real seam recipe: a Google Calendar event's own
title or description claims a milestone shipped, but the named milestone
is still open.

The Calendar-side twin of `email-claims-open-milestone` (task 1382),
and the fourth leg the `google_calendar+github` toolkit's own `claims-X`
grid has grown, after `calendar-event-claims-unfixed-issue` (the
hundred-second), `calendar-event-claims-unmerged-pr` (the hundred-third),
and `calendar-event-claims-dangling-milestone` (the hundred-fourth) --
the exact recipe that hundred-fourth recipe's own README named by name
("`claims-open-milestone` and `dangling-reference` remain open seams for
a future recipe, named here rather than silently assumed closed") and
left open on purpose.

The `claims-open-milestone` family already checks a "milestone #N
shipped" claim against twelve other surfaces -- `commit-claims-open-
milestone`, `issue-body-claims-open-milestone`, `issue-comment-claims-
open-milestone`, `linear-comment-claims-open-milestone`, `mention-
claims-open-milestone`, `milestone-claims-open-milestone`, `readme-
claims-open-milestone`, `release-claims-open-milestone`, `review-
comment-claims-open-milestone`, `slack-message-claims-open-milestone`,
`tweet-claims-open-milestone`, and `email-claims-open-milestone` --
this is the thirteenth leg, and the first time the family reaches the
Calendar toolkit.

Before writing this file, every one of the 104 existing recipes' own
`recipe.json`s was grepped for its own `toolkit` field to confirm the
gap rather than assume it: `google_calendar+github` names exactly three
recipes today (`calendar-event-claims-unfixed-issue`, `calendar-event-
claims-unmerged-pr`, `calendar-event-claims-dangling-milestone`), and
none of the three ever checks whether a claimed-open milestone is
actually still open -- the dangling-milestone recipe explicitly excludes
a claim naming a REAL milestone (open or closed) at confidence 0.0,
naming this exact gap as a future recipe's own remit rather than
silently treating it as covered.

Reuses `seam_engine.milestone_claims.claimed_milestone_numbers` verbatim
-- the same shared "milestone #N" grammar every `*-claims-*-milestone`
sibling already imports -- rather than a fourteenth independently
retyped copy. Genuinely distinct from `calendar-event-claims-dangling-
milestone`: that recipe's whole seam is a claimed milestone number that
does not exist at all; this recipe's whole seam is a claimed milestone
number that DOES exist and is still open. A single detector run only
ever produces one shape of gap for a given claim (a number either
resolves to a real milestone or it doesn't), so the two recipes never
compete over the same claim.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`events.json`,
`milestones.json`), shaped like what a real `ListEvents`/`ListMilestones`
read would return. Neither scope is new: `ListMilestones` already sits
on `SCOPES.md`'s cleared oath table under the `github` row, used by
every milestone-claim recipe in this engine; `ListEvents` has sat on the
"Google Calendar (v0.2)" row since `milestone-deadline-no-calendar-
event`, and all three existing Calendar recipes already ask for it --
this recipe asks for nothing new. Zero Google Calendar tools are exposed
on the-hand gateway today, the same WIP shape `SCOPES.md` already
documents; this recipe is fixture-only and never attempts a live
network call.

The seam: a "milestone #N" claim phrase inside a calendar event's own
title or description names a real milestone. If that milestone does not
exist at all, it is excluded here -- that is `calendar-event-claims-
dangling-milestone`'s own seam, not this one's (a bare `#N` and a
`milestone #N` claim phrase name different number spaces, the same
boundary every `*-claims-open-milestone` sibling already holds). If it
exists and is closed, the claim was simply true -- excluded, named not
hidden. If it exists and is still open, a calendar event already
sitting on the calendar disagrees with GitHub's own record, and nothing
on either platform ever compares the two. This never grades or blames
whoever created the event -- CONTRIBUTING.md's "No grading, ever" law,
same as every recipe in this engine: the headline names the gap between
two records, not a person's error.

Confidence is age-gated by the event's own `start` time, holding
`calendar-event-claims-unfixed-issue`'s and `email-claims-open-
milestone`'s identical 0.85/0.5 bar exactly -- not an independently
re-reasoned number just because the claim is about a milestone instead
of an issue or PR. A claim checked within 24 hours of the event's own
start might still be a race (the milestone actually closing out moments
after the event was created) rather than a settled overclaim -- unlike
`calendar-event-claims-dangling-milestone`'s flat 0.8, an open milestone
really could close at any moment, so the grace period means something
here.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.milestone_claims import claimed_milestone_numbers as _claimed_milestone_numbers
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "calendar_event_claims_open_milestone"
DEFAULT_EVENTS_FIXTURE = _FIXTURE_DIR / "events.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# A claim checked within this window of the event's own start time may
# just be a race rather than a genuine, settled overclaim -- the
# identical bar every claims-open-milestone sibling already holds
# itself to.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _load_rows(path: Path) -> list[Any]:
    """Refuses a syntactically valid but non-list payload with a named
    error, the same guard every sibling detector's own `_load_rows`
    holds."""
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


@dataclass
class CalendarEvent:
    id: str
    title: str
    description: str
    organizer: str
    start: datetime


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    url: str


def load_events(path: Path | None = None) -> list[CalendarEvent]:
    rows = _load_rows(path or DEFAULT_EVENTS_FIXTURE)
    return [
        CalendarEvent(
            id=r["id"], title=r["title"], description=r.get("description", ""),
            organizer=r.get("organizer", "unknown"), start=_parse_ts(r["start"]),
        )
        for r in rows
    ]


def load_milestones(path: Path | None = None) -> list[Milestone]:
    rows = _load_rows(path or DEFAULT_MILESTONES_FIXTURE)
    return [
        Milestone(number=r["number"], title=r["title"], state=r["state"], url=r["url"])
        for r in rows
    ]


def _find_milestone(number: int, milestones: list[Milestone]) -> Milestone | None:
    for milestone in milestones:
        if milestone.number == number:
            return milestone
    return None


def compute_gaps(
    events: list[CalendarEvent], milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed milestone is excluded, named not
    hidden, the moment an event makes no 'milestone #N' claim at all, the
    moment it names no real milestone at all, or the milestone it names
    is already closed -- everything left over (a shipped-it claim the
    milestone tracker itself contradicts) is surfaced, aged into a
    confidence score rank() can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for event in sorted(events, key=lambda e: e.id):
        combined_text = f"{event.title} {event.description}"
        numbers = _claimed_milestone_numbers(combined_text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{event.id}",
                headline=f"Calendar event {event.id} ('{event.title}') names no milestone claim",
                detail=(
                    f"title '{event.title}', description '{event.description}' -- carries "
                    "no 'milestone #N' claim phrase. No seam here."
                ),
                confidence=0.0,
                evidence=[f"calendar:{event.id}"],
            ))
            continue

        # dict.fromkeys dedupes, order-preserving: an event naming the
        # same #N twice must not produce two identical GapCandidates that
        # tie each other out of rank()'s SEPARATION_MARGIN, the same
        # guard every claims-open-milestone sibling already holds.
        for number in dict.fromkeys(numbers):
            milestone = _find_milestone(number, milestones)
            if milestone is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-not-found-{event.id}-{number}",
                    headline=f"Calendar event {event.id} ('{event.title}') claims milestone #{number}, which doesn't exist",
                    detail=(
                        f"title '{event.title}', description '{event.description}' claims "
                        f"milestone #{number} shipped, but no such milestone exists. No seam "
                        "here (see calendar-event-claims-dangling-milestone)."
                    ),
                    confidence=0.0,
                    evidence=[f"calendar:{event.id}"],
                ))
                continue

            if milestone.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{event.id}-{number}",
                    headline=f"Calendar event {event.id}'s claim about milestone #{number} holds",
                    detail=(
                        f"title '{event.title}', description '{event.description}' claims "
                        f"milestone #{number} ('{milestone.title}') shipped; the milestone is "
                        "closed. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[f"calendar:{event.id}", milestone.url],
                ))
                continue

            age_hours = (now - event.start).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"calendar-event-claims-open-milestone-{event.id}-{number}",
                headline=f"Calendar event {event.id} ('{event.title}') claims milestone #{number} shipped, but it's still open",
                detail=(
                    f"title '{event.title}', description '{event.description}' "
                    f"(organizer {event.organizer}, {event.start.isoformat()}, {age_hours:.1f}h ago) "
                    f"claims milestone #{number} ('{milestone.title}') shipped; the milestone's "
                    f"real state is '{milestone.state}'."
                ),
                confidence=confidence,
                evidence=[f"calendar:{event.id}", milestone.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    events_path: Path | None = None,
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest
    WIP marker this recipe carries until the-hand's gateway carries a
    live `ListEvents`/`ListMilestones` read for a connected Google
    Calendar account and these two loaders are swapped for real calls.
    The detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    events = load_events(events_path)
    milestones = load_milestones(milestones_path)
    surfaced, excluded = compute_gaps(events, milestones, now=now)
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
