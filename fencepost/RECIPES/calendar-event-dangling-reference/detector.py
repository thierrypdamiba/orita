"""The hundred-sixth real seam recipe: a Google Calendar event's own
title or description names a bare `#N` reference, checked against BOTH
the live issue list and the live PR list, but no issue or pull request
with that number exists at all.

The Calendar-side twin of `email-dangling-reference` (task 1364's own
Gmail leg) and the twelfth leg of the dangling-reference family overall,
after `dangling-issue-reference` (commit messages), `mention-dangling-
reference` (X mentions), `release-note-dangling-reference` (release
bodies), `issue-body-dangling-reference` (issue/PR opening bodies),
`milestone-body-dangling-reference` (milestone descriptions), `own-tweet-
dangling-reference` (the town's own outbound tweets), `review-comment-
dangling-reference` (inline PR review comments), `issue-comment-dangling-
reference` (ordinary issue/PR timeline conversation), `linear-comment-
dangling-reference` (Linear comments), `slack-message-dangling-reference`
(Slack messages), and `email-dangling-reference` (inbound email). None of
the eleven ever read a Google Calendar event.

`calendar-event-claims-unfixed-issue/detector.py`'s own docstring (the
hundred-second real recipe) named this seam and deliberately left it
open: "A named issue that does not exist at all is excluded at confidence
0.0, named not hidden -- a broken reference is a future calendar-side
dangling-reference recipe's own seam, not this one's." This is that
recipe. Same reading surface (`ListEvents`, a calendar event's own
title+description) `calendar-event-claims-unfixed-issue`, `calendar-
event-claims-unmerged-pr`, `calendar-event-claims-dangling-milestone`,
and `calendar-event-claims-open-milestone` already read, a different
claim shape: those four only ever look at a specific closing-keyword or
"milestone #N" phrase; this recipe looks at EVERY bare `#N` reference
regardless of the word in front of it ("any movement on #N", "saw #N
land in the changelog") and checks it against BOTH the issue list and
the PR list -- GitHub shares one number sequence between the two, the
same "checking only one misfires on a perfectly good reference to a
merged PR" discipline every dangling-reference sibling already holds
itself to. With this recipe, the `google_calendar+github` toolkit's own
`claims-X`/dangling-reference grid names all three of the seams
`calendar-event-claims-dangling-milestone`'s own docstring left open
(`claims-dangling-milestone`, closed by task 1380; `claims-open-
milestone`, closed by task 1382; `dangling-reference`, closed here) --
the same five-legs-per-source shape `email-claims-dangling-milestone`'s
own docstring first named for Gmail, now grown for Calendar too, minus
the `claims-unfixed-issue`/`claims-unmerged-pr` pair Calendar already had
before either milestone leg existed.

Reuses `seam_engine.references.referenced_numbers` verbatim -- the one
shared `#N`-extraction grammar `dangling-issue-reference` and its ten
prior dangling-reference siblings already import from the same place, so
a future tightening of the pattern (the cross-repo `owner/repo#N`
exclusion, in particular) lands in all twelve detectors at once or not
at all, never a thirteenth independently retyped copy.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads three local fixture files (`events.json`,
`issues.json`, `pulls.json`), shaped like what a real `ListEvents`/
`ListIssues`/`ListPullRequests` read would return. `ListIssues` and
`ListPullRequests` already sit on `SCOPES.md`'s cleared oath table under
the `github` row, used by every dangling-reference and claims-* recipe in
this engine. `ListEvents` is not a new scope -- it has sat on `SCOPES.md`'s
"Google Calendar (v0.2)" row since `milestone-deadline-no-calendar-event`
first declared it, and all four existing Calendar recipes already ask for
it. Zero Google Calendar tools are exposed on the-hand gateway today, the
same WIP shape `SCOPES.md` already documents; this recipe is fixture-only
and never attempts a live network call.

The seam: a bare `#N` reference inside a calendar event's own title or
description names a GitHub issue or PR number. If no issue or PR with
that number exists at all in either tracker, whoever wrote the event has
a belief about the project that is already out of sync with GitHub's real
number space -- a typo, a reference to something deleted, or a number
meant for a different repo -- and nothing on either platform ever
compares the two. An event with no `#N` reference at all produces no
candidate whatsoever, not even an excluded one -- the identical "not an
invite at all" exclusion every dangling-reference sibling already makes
for a reference-free source. This never grades or blames whoever
organized the event -- CONTRIBUTING.md's "No grading, ever" law, same as
every recipe in this engine: the headline names the gap between two
records, not a person's error.

Confidence is FLAT at 0.75 -- `email-dangling-reference`'s own exact
score, not an independently re-reasoned number just because the reading
surface is Calendar rather than Gmail: a calendar event, like an inbound
email and unlike a still-editable Slack message or Linear comment, is not
a text surface its organizer typically revises after the fact once the
event has been created and the seam scan runs -- there is no grace window
that means anything here (unlike the milestone-claims legs, this recipe
does not need an age gate for a DIFFERENT reason: a nonexistent issue/PR
number will not spontaneously start existing later, so waiting out a race
buys nothing, the same reasoning `calendar-event-claims-dangling-
milestone`'s own docstring already gives for its own flat score). Held at
0.75 rather than `dangling-issue-reference`'s self-authored 0.8: an
organizer's own free text may simply be numbering a different tracker in
their own head, the identical reasoning `mention-dangling-reference`'s
and `email-dangling-reference`'s own docstrings already give for scoring
below a commit message's own repo-scoped convention.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.references import referenced_numbers as _referenced_numbers
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "calendar_event_dangling_reference"
DEFAULT_EVENTS_FIXTURE = _FIXTURE_DIR / "events.json"
DEFAULT_ISSUES_FIXTURE = _FIXTURE_DIR / "issues.json"
DEFAULT_PULLS_FIXTURE = _FIXTURE_DIR / "pulls.json"

# Flat 0.75 -- email-dangling-reference's own exact score, not a
# copy-pasted guess: a calendar event's own free text, like an inbound
# email, is unstructured prose from an organizer who may simply be
# numbering a different tracker in their own head, and is not a text
# surface that gets revised once the scan has already run. See this
# module's own docstring for the full reasoning.
_DANGLING_CONFIDENCE = 0.75


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
class Issue:
    number: int
    title: str
    state: str
    url: str


@dataclass
class PullRequest:
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


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [Issue(number=r["number"], title=r["title"], state=r["state"], url=r["url"]) for r in rows]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [PullRequest(number=r["number"], title=r["title"], state=r["state"], url=r["url"]) for r in rows]


def compute_gaps(
    events: list[CalendarEvent], issues: list[Issue], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other detector in
    this engine. An event with no `#N` reference at all is not examined --
    it never claims anything about a second record, so there is no seam to
    weigh, the same "not an invite at all" exclusion `email-dangling-
    reference.compute_gaps` already makes for a reference-free email.
    `now` is accepted, unused, for interface parity with every sibling
    recipe's `compute_gaps(..., *, now=...)` shape -- this recipe is flat,
    not age-gated, same as its `email-dangling-reference` twin."""
    del now  # unused today; kept for interface parity, see docstring

    known_numbers = {i.number for i in issues} | {p.number for p in pulls}

    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for event in sorted(events, key=lambda e: e.id):
        combined_text = f"{event.title} {event.description}"
        # dict.fromkeys dedupes, order-preserving: an event naming the
        # same #N twice must not produce two identical GapCandidates that
        # tie each other out of rank()'s SEPARATION_MARGIN (task 442's
        # precedent, held by every sibling in this family).
        for n in dict.fromkeys(_referenced_numbers(combined_text)):
            if n in known_numbers:
                excluded.append(GapCandidate(
                    slug=f"calendar-ref-matched-{event.id}-{n}",
                    headline=f"Calendar event {event.id}'s reference to #{n} matches a real issue or PR",
                    detail=f"title '{event.title}', description '{event.description}' "
                           f"(organizer {event.organizer}) references #{n}; a real issue or "
                           f"pull request #{n} exists in this repo. No seam here.",
                    confidence=0.0,
                    evidence=[f"calendar:{event.id}"],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"calendar-event-dangling-reference-{event.id}-{n}",
                headline=f"Calendar event {event.id} ('{event.title}') references #{n}, but no issue or PR #{n} exists here",
                detail=f"title '{event.title}', description '{event.description}' "
                       f"(organizer {event.organizer}, {event.start.isoformat()}) references "
                       f"#{n}; ListIssues + ListPullRequests found no issue or pull request "
                       f"with that number in this repo. An organizer's own belief about the "
                       f"project, sitting on a connected calendar, is already out of sync with "
                       f"GitHub's real number space -- a typo, a reference to something "
                       f"deleted, or a number meant for a different repo.",
                confidence=_DANGLING_CONFIDENCE,
                evidence=[f"calendar:{event.id}"],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    events_path: Path | None = None,
    issues_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the-hand's gateway carries a live
    `ListEvents`/`ListIssues`/`ListPullRequests` read for a connected
    Google Calendar account and these three loaders are swapped for real
    calls. The detection logic does not change one line when that
    happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    events = load_events(events_path)
    issues = load_issues(issues_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(events, issues, pulls, now=now)
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
