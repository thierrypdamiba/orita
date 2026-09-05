"""The hundred-second real seam recipe: a Google Calendar event's own
title or description invokes a real GitHub closing keyword against an
issue ("fixes #N" / "closes #N" / "resolves #N", both tenses), but the
issue never actually closed.

The Calendar-side twin of `mention-claims-unfixed-issue` (the X-mention
leg), `slack-message-claims-unfixed-issue` (the Slack-channel leg),
`linear-comment-claims-unfixed-issue` (the Linear-comment leg), and
`email-claims-unfixed-issue` (the Gmail leg) of the `claims-unfixed-issue`
family. All five check the identical closing-keyword grammar against a
claim posted somewhere the town does not fully control -- this recipe
reads a Calendar event's own title/description, a standup note or a
"ship review" meeting entry sitting on a connected calendar, not a tweet,
a mention, a Slack message, a Linear comment, or an email.

Before writing this file, every one of the 101 existing recipes' own
`recipe.json`s was grepped for its own `toolkit` field to confirm the
gap rather than assume it: `google_calendar` appears in exactly one place,
`milestone-deadline-no-calendar-event`'s own `github+google_calendar` --
and that recipe never reads an event's own title/description as a
claim-bearing text surface at all. It only ever asks whether a GitHub
milestone's `due_on` date has ANY calendar event nearby, matching on
keyword-overlap and a time window -- it never parses an event's own text
for a closing-keyword promise. `GetEvent` has sat on `SCOPES.md`'s
"Google Calendar (v0.2)" row, cleared, since `milestone-deadline-no-
calendar-event` first opened the toolkit, but until this recipe nothing
under `RECIPES/` had ever actually read an event's own free text as a
claim. A genuinely new axis, not one more cell filled in on a grid this
repo has already worked inside -- the Calendar toolkit's own text-reading
door, still shut after `milestone-deadline-no-calendar-event`, same shape
`email-claims-unfixed-issue`'s own docstring found for Gmail relative to
`gmail_calendar.py`.

Reuses `seam_engine.closing_keywords.CLOSING_KEYWORD_RE` verbatim -- the
same shared grammar `email-claims-unfixed-issue` and its four
`claims-unfixed-issue` siblings already import, rather than a
seventeenth independently retyped copy of the identical pattern.
"Closing #N" (present participle, Iron Rule #8's own prescribed safe
form) never matches either tense here either, same as everywhere else
this grammar is used. The claim is extracted from `title + " " +
description` combined -- a real Google Calendar event's `description`
field is where a claim like this would ordinarily live (an agenda note,
a follow-up line), but a short claim can just as easily sit in the title
alone ("Fixes #47 review"), and nothing about a claim posted in either
field is less durable or less readable-later than the other.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`events.json`,
`issues.json`), shaped like what a real `ListEvents`/`ListIssues` read
would return. `ListIssues` is already cleared on `SCOPES.md`'s oath table
under the `github` row. `ListEvents` is not a new scope -- it has sat on
`SCOPES.md`'s "Google Calendar (v0.2)" row since `milestone-deadline-no-
calendar-event` first declared it -- but this is the first recipe to read
an event's own text rather than only its start time. Zero Google Calendar
tools are exposed on the-hand gateway today (the same WIP shape SCOPES.md
already documents for `milestone-deadline-no-calendar-event`); this
recipe is fixture-only and never attempts a live network call.

The seam: a closing-keyword phrase inside a calendar event's own title or
description names an issue by number. If that issue does not exist at
all, it is excluded here -- that broken reference belongs to a future
calendar-side dangling-reference recipe, not this one's. If it exists
and is closed, the claim was simply true -- excluded, named not hidden.
If it exists and is still open, an event already sitting on a connected
calendar disagrees with GitHub's own record, and nothing on either
platform ever compares the two. This never grades or blames whoever
created the event -- CONTRIBUTING.md's "No grading, ever" law, same as
every recipe in this engine: the headline names the gap between two
records, not a person's error.

Confidence is age-gated by the event's own `start` time, holding
`email-claims-unfixed-issue`'s/`mention-claims-unfixed-issue`'s/
`slack-message-claims-unfixed-issue`'s/`linear-comment-claims-unfixed-
issue`'s identical 0.85/0.5 bar exactly -- not an independently
re-reasoned number just because the toolkit is new. A claim checked
within 24 hours of the event's own start might still be a race (the real
fix landing moments after the meeting) rather than a settled overclaim.
The check itself is objective: the claimed issue's own live `state`
field, verified against `ListIssues`, not a guess about which tracker
the organizer meant -- the same reasoning every sibling in this family
already gives for holding the identical bar, no independently re-reasoned
number.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.closing_keywords import CLOSING_KEYWORD_RE
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "calendar_event_claims_unfixed_issue"
DEFAULT_EVENTS_FIXTURE = _FIXTURE_DIR / "events.json"
DEFAULT_ISSUES_FIXTURE = _FIXTURE_DIR / "issues.json"

# A claim checked within this window of the event's own start may just be a
# race (the real fix landing moments after the meeting) rather than a
# genuine, settled overclaim -- the identical bar every claims-unfixed-issue
# sibling already holds itself to.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _load_rows(path: Path) -> list[Any]:
    """Refuses a syntactically valid but non-list payload with a named
    error, the same guard every sibling detector's own `_load_rows` holds."""
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
    return [
        Issue(number=r["number"], title=r["title"], state=r["state"], url=r["url"])
        for r in rows
    ]


def _claimed_issue_numbers(text: str) -> list[int]:
    return [int(n) for n in CLOSING_KEYWORD_RE.findall(text)]


def _find_issue(number: int, issues: list[Issue]) -> Issue | None:
    for issue in issues:
        if issue.number == number:
            return issue
    return None


def compute_gaps(
    events: list[CalendarEvent], issues: list[Issue], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed issue is excluded, named not hidden, the
    moment an event names no real issue at all, or the issue it names is
    already closed -- everything left over (a fix-claim the issue tracker
    itself contradicts) is surfaced, aged into a confidence score rank()
    can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for event in sorted(events, key=lambda e: e.id):
        combined_text = f"{event.title} {event.description}"
        numbers = _claimed_issue_numbers(combined_text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{event.id}",
                headline=f"Calendar event {event.id} ('{event.title}') names no fixes/closes/resolves issue claim",
                detail=(
                    f"title '{event.title}', description '{event.description}' -- carries "
                    "no closing-keyword reference. No seam here."
                ),
                confidence=0.0,
                evidence=[f"calendar:{event.id}"],
            ))
            continue

        # dict.fromkeys dedupes, order-preserving: an event naming the same
        # issue twice must not produce two identical GapCandidates that tie
        # each other out of rank()'s SEPARATION_MARGIN, the same guard
        # email-claims-unfixed-issue already holds.
        for number in dict.fromkeys(numbers):
            issue = _find_issue(number, issues)
            if issue is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-issue-not-found-{event.id}-{number}",
                    headline=f"Calendar event {event.id} ('{event.title}') claims fixing #{number}, which doesn't exist",
                    detail=(
                        f"title '{event.title}', description '{event.description}' -- claims "
                        f"#{number} fixed, but no such issue exists. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[f"calendar:{event.id}"],
                ))
                continue

            if issue.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{event.id}-{number}",
                    headline=f"Calendar event {event.id}'s claim about #{number} holds",
                    detail=(
                        f"title '{event.title}' claims #{number} fixed; issue #{number} "
                        f"('{issue.title}') is closed. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[f"calendar:{event.id}", issue.url],
                ))
                continue

            age_hours = (now - event.start).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"calendar-event-claims-unfixed-issue-{event.id}-{number}",
                headline=f"Calendar event {event.id} ('{event.title}') claims #{number} fixed, but #{number} is still open",
                detail=(
                    f"title '{event.title}', description '{event.description}' "
                    f"(organizer {event.organizer}, {event.start.isoformat()}, "
                    f"{age_hours:.1f}h ago) claims #{number} ('{issue.title}') fixed; "
                    f"the issue's real state is '{issue.state}'."
                ),
                confidence=confidence,
                evidence=[f"calendar:{event.id}", issue.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    events_path: Path | None = None,
    issues_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the-hand's gateway carries a live
    `ListEvents`/`ListIssues` read for a connected Google Calendar account
    and these two loaders are swapped for real calls. The detection logic
    does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    events = load_events(events_path)
    issues = load_issues(issues_path)
    surfaced, excluded = compute_gaps(events, issues, now=now)
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
