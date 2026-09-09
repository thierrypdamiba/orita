"""The hundred-third real seam recipe: a Google Calendar event's own
title or description invokes a real "ships/includes/merges/via #N" claim
against a pull request, but the named PR is not actually merged.

The Calendar-side twin of `mention-claims-unmerged-pr` (the X-mention
leg), `slack-message-claims-unmerged-pr` (the Slack-channel leg),
`linear-comment-claims-unmerged-pr` (the Linear-comment leg), `review-
comment-claims-unmerged-pr` (the review-comment leg), `milestone-claims-
unmerged-pr`/`release-claims-unmerged-pr` (the milestone/release legs),
and `email-claims-unmerged-pr` (the Gmail leg) of the `claims-unmerged-pr`
family, and the second leg `calendar-event-claims-unfixed-issue` (task
1258, the hundred-second real recipe) opened for the Calendar toolkit's
own `claims-X` grid -- that recipe's own docstring excluded exactly one
target from its own scope ("a named issue that does not exist at all is
excluded here... that broken reference is a future calendar-side
dangling-reference recipe's own seam, not this one's") but never claimed
to close the PR-claim leg itself; this recipe is that leg.

Grepped every one of the 102 existing recipes' own `recipe.json` before
writing this one, the same discipline `calendar-event-claims-unfixed-
issue`'s own docstring already used: `google_calendar` appears in exactly
two places today -- `milestone-deadline-no-calendar-event` (a due-date/
time-window match, never a text claim) and `calendar-event-claims-
unfixed-issue` (the issue-closing-keyword leg). Neither reads a calendar
event's own text for a "shipped it" PR claim. Calendar is the newest
source this engine reads (added by task 1258, after the ten-source-by-
three-target `claims-X` grid named in `slack-message-claims-unmerged-
pr`'s own docstring had already closed every other cell) -- so unlike
that grid, Calendar still has open cells: this recipe closes one of them
(`claims-unmerged-pr`); `claims-open-milestone`, `claims-dangling-
milestone`, and `dangling-reference` remain open for a future hour to
name.

Reuses `seam_engine.pr_claims.claimed_pr_numbers` verbatim -- the same
shared "ships/includes/merges/via #N" grammar every `claims-unmerged-pr`
sibling already imports from there -- rather than a ninth independently
retyped copy of the identical pattern. Reuses `calendar-event-claims-
unfixed-issue`'s own `CalendarEvent` dataclass shape (id/title/
description/organizer/start) verbatim, and `slack-message-claims-
unmerged-pr`'s own `PullRequest` dataclass shape (number/title/state/
merged/url) verbatim -- no new data model invented where an identical one
already exists two directories over.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`events.json`,
`pulls.json`), shaped like what a real `ListEvents`/`ListPullRequests`
read would return. `ListPullRequests` is already cleared on `SCOPES.md`'s
oath table under the `github` row, used by nearly every recipe in this
engine that reads the PR tracker. `ListEvents` is not a new scope either
-- it has sat on `SCOPES.md`'s "Google Calendar (v0.2)" row since
`milestone-deadline-no-calendar-event` first declared it, and `calendar-
event-claims-unfixed-issue` already asks for it too. `google_calendar+
github` is not a new toolkit pair -- both Calendar siblings already
propose it. Zero Google Calendar tools are exposed on the-hand gateway
today, the same WIP shape `SCOPES.md` already documents; this recipe is
fixture-only and never attempts a live network call.

The seam: a `ships #N`/`includes #N`/`merges #N`/`via #N` claim phrase
inside a calendar event's own title or description names a pull request
by number. If that PR does not exist at all, it is excluded here -- that
broken reference belongs to a future calendar-side dangling-reference
recipe, not this one. If it exists and is merged, the claim was simply
true -- excluded, named not hidden. If it exists and is NOT merged (still
open, or closed without merging), an event already sitting on a connected
calendar disagrees with GitHub's own record, and nothing on either
platform ever compares the two. This never grades or blames whoever
created the event -- CONTRIBUTING.md's "No grading, ever" law, same as
every recipe in this engine: the headline names the gap between two
records, not a person's error.

Confidence is age-gated by the event's own `start` time, holding
`calendar-event-claims-unfixed-issue`'s own 0.85/0.5 bar exactly -- not an
independently re-reasoned number just because the target changed from an
issue to a PR. A calendar event, like a Slack message, a Linear comment,
a tweet, or a mention, is posted once (created) and stands; a claim
checked within 24 hours of the event's own start might still be a race
(the real merge landing moments after the meeting) rather than a settled
overclaim (0.5, below the 0.70 confidence bar, shown as a weighed-and-
dropped coincidence, not hidden). At or past 24 hours with the named PR
still unmerged, it is unambiguous (flat 0.85). The check itself is
objective: the claimed PR's own live `merged`/`state` fields, verified
against `ListPullRequests`, not a guess about which tracker the organizer
meant -- the same reasoning every `claims-unmerged-pr` sibling already
gives for holding this identical bar.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.pr_claims import claimed_pr_numbers as _claimed_pr_numbers
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "calendar_event_claims_unmerged_pr"
DEFAULT_EVENTS_FIXTURE = _FIXTURE_DIR / "events.json"
DEFAULT_PULLS_FIXTURE = _FIXTURE_DIR / "pulls.json"

# A claim checked within this window of the event's own start may just be a
# race (the real merge landing moments after the meeting) rather than a
# genuine, settled overclaim -- the identical bar calendar-event-claims-
# unfixed-issue and every claims-unmerged-pr sibling already hold themselves
# to.
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
class PullRequest:
    number: int
    title: str
    state: str
    merged: bool
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


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [
        PullRequest(number=r["number"], title=r["title"], state=r["state"], merged=r["merged"], url=r["url"])
        for r in rows
    ]


def _find_pull(number: int, pulls: list[PullRequest]) -> PullRequest | None:
    for pr in pulls:
        if pr.number == number:
            return pr
    return None


def compute_gaps(
    events: list[CalendarEvent], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed PR is excluded, named not hidden, the
    moment an event names no real PR at all, or the PR it names is already
    merged -- everything left over (a shipped-it claim the PR tracker
    itself contradicts) is surfaced, aged into a confidence score rank()
    can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for event in sorted(events, key=lambda e: e.id):
        combined_text = f"{event.title} {event.description}"
        numbers = _claimed_pr_numbers(combined_text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{event.id}",
                headline=f"Calendar event {event.id} ('{event.title}') names no ships/includes/merges/via PR claim",
                detail=(
                    f"title '{event.title}', description '{event.description}' -- carries "
                    "no ships/includes/merges/via claim-phrase reference. No seam here."
                ),
                confidence=0.0,
                evidence=[f"calendar:{event.id}"],
            ))
            continue

        # dict.fromkeys dedupes, order-preserving: an event naming the same
        # PR twice must not produce two identical GapCandidates that tie
        # each other out of rank()'s SEPARATION_MARGIN, the same guard
        # every claims-unmerged-pr sibling's own compute_gaps already holds.
        for number in dict.fromkeys(numbers):
            pr = _find_pull(number, pulls)
            if pr is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-pr-not-found-{event.id}-{number}",
                    headline=f"Calendar event {event.id} ('{event.title}') claims #{number} shipped, which doesn't exist",
                    detail=(
                        f"title '{event.title}', description '{event.description}' -- claims "
                        f"#{number} shipped, but no such PR exists. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[f"calendar:{event.id}"],
                ))
                continue

            if pr.merged:
                excluded.append(GapCandidate(
                    slug=f"claim-true-{event.id}-{number}",
                    headline=f"Calendar event {event.id}'s claim about #{number} holds",
                    detail=(
                        f"title '{event.title}' claims #{number} ('{pr.title}') shipped; "
                        f"PR #{number} is merged. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[f"calendar:{event.id}", pr.url],
                ))
                continue

            age_hours = (now - event.start).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"calendar-event-claims-unmerged-pr-{event.id}-{number}",
                headline=f"Calendar event {event.id} ('{event.title}') claims #{number} shipped, but #{number} never merged",
                detail=(
                    f"title '{event.title}', description '{event.description}' "
                    f"(organizer {event.organizer}, {event.start.isoformat()}, "
                    f"{age_hours:.1f}h ago) claims #{number} ('{pr.title}') shipped; "
                    f"the PR's real state is '{pr.state}', merged={pr.merged}."
                ),
                confidence=confidence,
                evidence=[f"calendar:{event.id}", pr.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    events_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the-hand's gateway carries a live
    `ListEvents`/`ListPullRequests` read for a connected Google Calendar
    account and these two loaders are swapped for real calls. The
    detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    events = load_events(events_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(events, pulls, now=now)
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
