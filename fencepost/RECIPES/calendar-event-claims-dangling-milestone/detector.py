"""The hundred-fourth real seam recipe: a Google Calendar event's own
title or description invokes a real "milestone #N" claim phrase, but no
milestone with that number exists at all.

The Calendar-side twin of `commit-claims-dangling-milestone`,
`issue-body-claims-dangling-milestone`, `issue-comment-claims-dangling-
milestone`, `linear-comment-claims-dangling-milestone`, `mention-claims-
dangling-milestone`, `milestone-claims-dangling-milestone`, `readme-
claims-dangling-milestone`, `release-claims-dangling-milestone`,
`review-comment-claims-dangling-milestone`, `slack-message-claims-
dangling-milestone`, `tweet-claims-dangling-milestone`, and
`email-claims-dangling-milestone` -- the thirteenth leg of that family,
and the third leg the Calendar toolkit's own `claims-X` grid has grown
(after `calendar-event-claims-unfixed-issue`, the hundred-second real
recipe, and `calendar-event-claims-unmerged-pr`, the hundred-third).

Before writing this file, every one of the 103 existing recipes' own
`recipe.json`s was grepped for its own `toolkit` field to confirm the
gap rather than assume it: `google_calendar+github` names exactly two
recipes today, `calendar-event-claims-unfixed-issue` (closing-keyword
claims against the issue tracker) and `calendar-event-claims-unmerged-pr`
(ships/includes/merges/via claims against the PR tracker) -- neither
ever reads a "milestone #N" claim phrase, and neither ever opens
`ListMilestones`. `email-claims-dangling-milestone` (task 1364) drew the
identical line for the Gmail toolkit and named it plainly: "every other
`claims-*` source in this engine ... already carries all five legs of
its own family (claims-dangling-milestone, claims-open-milestone,
claims-unfixed-issue, claims-unmerged-pr, dangling-reference); email was
the one source stuck at four." Calendar is the newer toolkit -- two legs
grown so far, not five -- and this recipe closes one of the three still
missing (`claims-dangling-milestone`; `claims-open-milestone` and
`dangling-reference` remain open seams for a future recipe, named here
rather than silently assumed closed).

Reuses `seam_engine.milestone_claims.claimed_milestone_numbers` verbatim
-- the same shared "milestone #N" grammar every `*-claims-*-milestone`
sibling already imports -- rather than a copy retyped a second time for
the Calendar toolkit specifically. Genuinely distinct from a future
calendar-side dangling-reference recipe: milestones and issues/PRs are
separate GitHub number spaces (the same distinction
`email-claims-dangling-milestone`'s own docstring draws for Gmail), so a
`#N` that resolves cleanly as a real issue could still be a dangling
MILESTONE claim, and this recipe never touches the issue or PR trackers
at all, only `ListMilestones`.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`events.json`,
`milestones.json`), shaped like what a real `ListEvents`/`ListMilestones`
read would return. `ListMilestones` already sits on `SCOPES.md`'s
cleared oath table under the `github` row, used by every milestone-claim
recipe in this engine. `ListEvents` is not a new scope -- it has sat on
`SCOPES.md`'s "Google Calendar (v0.2)" row since `milestone-deadline-no-
calendar-event` first declared it, and both existing Calendar recipes
already ask for it -- this recipe asks for nothing new. Zero Google
Calendar tools are exposed on the-hand gateway today, the same WIP shape
`SCOPES.md` already documents; this recipe is fixture-only and never
attempts a live network call.

The seam: a "milestone #N" claim phrase inside a calendar event's own
title or description names a milestone number that does not exist at
all. If the number DOES resolve to a real milestone -- open or closed,
this recipe does not care which -- the claim is excluded here, named not
hidden: whether that claim is TRUE is a future
`calendar-event-claims-open-milestone`'s own seam, not this one's. An
event with no "milestone #N" claim phrase at all (a bare `#N` aside, or
no claim-relevant text) produces no candidate. This never grades or
blames whoever created the event -- CONTRIBUTING.md's "No grading, ever"
law, same as every recipe in this engine.

Confidence is flat (0.8), not age-gated -- mirrors every other
`*-claims-dangling-milestone` sibling's own reasoning, including
`email-claims-dangling-milestone`'s and `calendar-event-claims-unfixed-
issue`'s shared explanation for why NOT to reuse the 0.85/0.5 age-gated
bar here: an OPEN milestone could close at any moment, so a fresh claim
about an open one might just be a race the event hasn't caught up to
yet -- but a milestone number that does not exist right now will not
spontaneously start existing later no matter how long the event sits on
the calendar, so there is no grace period that means anything here.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "calendar_event_claims_dangling_milestone"
DEFAULT_EVENTS_FIXTURE = _FIXTURE_DIR / "events.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# Flat, not age-gated -- see the module docstring. Mirrors every other
# `*-claims-dangling-milestone` sibling's own `_DANGLING_CONFIDENCE`
# exactly (0.8): a nonexistent milestone number will not spontaneously
# start existing, whatever the age of the event naming it.
_DANGLING_CONFIDENCE = 0.8


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
    own `compute_gaps`. An event naming no 'milestone #N' claim phrase at
    all is excluded, named not hidden. A claimed milestone is excluded,
    named not hidden, the moment it names a real milestone (open or
    closed, this recipe does not care which) -- everything left over (a
    claimed milestone number with no real milestone behind it at all) is
    surfaced at a flat confidence.

    `now` is accepted, unused -- kept for interface parity with every
    other recipe's own `compute_gaps(..., now=...)` shape (`run_recipe_
    scan` always threads one through); this recipe's confidence is flat,
    not age-gated, so there is nothing here for `now` to weigh against,
    the identical reasoning `email-claims-dangling-milestone`'s own
    detector already gives for the same unused parameter."""
    del now  # unused today; kept for interface parity, see docstring above.
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
        # guard every dangling-milestone sibling already holds.
        for number in dict.fromkeys(numbers):
            milestone = _find_milestone(number, milestones)
            if milestone is not None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-exists-{event.id}-{number}",
                    headline=f"Calendar event {event.id}'s claimed milestone #{number} is real",
                    detail=(
                        f"title '{event.title}', description '{event.description}' -- claims "
                        f"milestone #{number} ('{milestone.title}', state '{milestone.state}'); "
                        "the milestone exists. Whether the claim itself is TRUE is a different "
                        "recipe's seam, not this one's. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[f"calendar:{event.id}", milestone.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"calendar-event-claims-dangling-milestone-{event.id}-{number}",
                headline=f"Calendar event {event.id} ('{event.title}') claims milestone #{number}, which doesn't exist",
                detail=(
                    f"title '{event.title}', description '{event.description}' "
                    f"(organizer {event.organizer}, {event.start.isoformat()}) claims "
                    f"milestone #{number}, but no milestone with that number exists at all. "
                    "A calendar entry renders the number as plain text regardless; nothing on "
                    "either platform ever checks a 'milestone #N' claim phrase inside an event "
                    "against the real milestone tracker."
                ),
                confidence=_DANGLING_CONFIDENCE,
                evidence=[f"calendar:{event.id}"],
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
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the-hand's gateway carries a live
    `ListEvents`/`ListMilestones` read for a connected Google Calendar
    account and these two loaders are swapped for real calls. The
    detection logic does not change one line when that happens."""
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
