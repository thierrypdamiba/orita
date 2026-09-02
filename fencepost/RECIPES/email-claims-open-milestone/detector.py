"""The hundredth real seam recipe, and the fourth to read `gmail` (after
`email-claims-unfixed-issue`, the ninety-third, `email-dangling-reference`,
the ninety-eighth, and `email-claims-unmerged-pr`, the ninety-ninth).

The `claims-open-milestone` family already checks a "milestone #N shipped"
claim against ten other surfaces -- `commit-claims-open-milestone`,
`issue-body-claims-open-milestone`, `issue-comment-claims-open-milestone`,
`linear-comment-claims-open-milestone`, `mention-claims-open-milestone`,
`milestone-claims-open-milestone`, `readme-claims-open-milestone`,
`release-claims-open-milestone`, `review-comment-claims-open-milestone`,
`slack-message-claims-open-milestone`, and `tweet-claims-open-milestone` --
eleven legs, every one of them wired up before `gmail` was ever a live
toolkit in this engine at all. `email-claims-unmerged-pr`'s own docstring
named the identical "twin the inbound siblings, not the town-controlled
ones" shape for the PR-claim grammar; this recipe draws that same line one
more time, for the milestone-claim grammar, on the one surface that leg
had never grown a leg for either: an inbound email.

Reuses `seam_engine.milestone_claims.claimed_milestone_numbers` verbatim --
the shared "milestone #N" grammar twelve sibling recipes already import --
rather than a thirteenth independently retyped copy.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`emails.json`,
`milestones.json`), shaped like what a real `ListEmails`/`ListMilestones`
read would return. `ListMilestones` already sits on `SCOPES.md`'s cleared
oath table under the `github` row, used by every milestone-claim recipe in
this engine. `ListEmails` is not a new scope -- it has sat on the Gmail row
since ROADMAP.md #16, and `email-claims-unfixed-issue`, `email-dangling-
reference`, and `email-claims-unmerged-pr` already declare it -- but this
recipe asks for nothing new. See `SCOPES.md`'s own WIP note for
`gmail_calendar.py`: the-hand gateway's connected Google account carries
`gmail.readonly` among its granted OAuth scopes, but exposes zero
Gmail-capable tools on the live gateway today -- the identical "connected
upstream, not wired into the gateway" shape `SCOPES.md`'s Slack and Linear
WIP notes each already document for their own toolkit. This recipe is
fixture-only, MOCK ONLY, and never attempts a live network call.

The seam: a `milestone #N` claim phrase inside an inbound email's own body
names a milestone by number. If that milestone does not exist at all, it
is excluded here -- that broken reference is `email-dangling-reference`'s
own seam, not this one's (a bare `#N` and a `milestone #N` claim phrase
name different number spaces, the same boundary every `*-claims-open-
milestone` sibling already holds). If it exists and is closed, the claim
was simply true -- excluded, named not hidden. If it exists and is still
open, an email already sitting in a connected inbox disagrees with
GitHub's own record, and nothing on either platform ever compares the two.
This never grades or blames whoever sent the email -- CONTRIBUTING.md's
"No grading, ever" law, same as every recipe in this engine: the headline
names the gap between two records, not a person's error.

Confidence is age-gated by the email's own `received_at`, holding
`linear-comment-claims-open-milestone`'s and `email-claims-unmerged-pr`'s
identical 0.85/0.5 bar exactly -- not an independently re-reasoned number
just because the toolkit is new. A claim checked within 24 hours of the
email landing might still be a race (the milestone actually closing out
moments after the email went out) rather than a settled overclaim. The
check itself is objective: the claimed milestone's own live `state` field,
verified against `ListMilestones`, not a guess about which tracker the
sender meant -- the same reasoning every claims-open-milestone sibling
already gives for holding the identical bar.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "email_claims_open_milestone"
DEFAULT_EMAILS_FIXTURE = _FIXTURE_DIR / "emails.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# A claim checked within this window of the email's own received_at may
# just be a race rather than a genuine, settled overclaim -- the identical
# bar every claims-open-milestone sibling already holds itself to.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Email:
    id: str
    sender: str
    subject: str
    body: str
    received_at: datetime


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_emails(path: Path | None = None) -> list[Email]:
    rows = _load_rows(path or DEFAULT_EMAILS_FIXTURE)
    return [
        Email(
            id=r["id"], sender=r["sender"], subject=r["subject"], body=r["body"],
            received_at=_parse_ts(r["received_at"]),
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
    emails: list[Email], milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed milestone is excluded, named not hidden,
    the moment an email makes no 'milestone #N' claim at all, the moment it
    names no real milestone at all, or the milestone it names is already
    closed -- everything left over (a shipped-it claim the milestone
    tracker itself contradicts) is surfaced, aged into a confidence score
    rank() can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for email in emails:
        numbers = _claimed_milestone_numbers(email.body)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{email.id}",
                headline=f"Email {email.id} ('{email.subject}') names no milestone claim",
                detail=f"'{email.body}' carries no 'milestone #N' claim phrase. No seam here.",
                confidence=0.0,
                evidence=[f"gmail:{email.id}"],
            ))
            continue

        seen: set[int] = set()
        for number in numbers:
            if number in seen:
                continue
            seen.add(number)

            milestone = _find_milestone(number, milestones)
            if milestone is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-not-found-{email.id}-{number}",
                    headline=f"Email {email.id} ('{email.subject}') claims milestone #{number}, which doesn't exist",
                    detail=f"'{email.body}' claims milestone #{number} shipped, but no such milestone exists. No seam here (see email-dangling-reference).",
                    confidence=0.0,
                    evidence=[f"gmail:{email.id}"],
                ))
                continue

            if milestone.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{email.id}-{number}",
                    headline=f"Email {email.id}'s claim about milestone #{number} holds",
                    detail=f"'{email.body}' claims milestone #{number} ('{milestone.title}') shipped; the milestone is closed. No seam here.",
                    confidence=0.0,
                    evidence=[f"gmail:{email.id}", milestone.url],
                ))
                continue

            age_hours = (now - email.received_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"email-claims-open-milestone-{email.id}-{number}",
                headline=f"Email {email.id} ('{email.subject}') claims milestone #{number} shipped, but it's still open",
                detail=(
                    f"'{email.body}' (received {email.received_at.isoformat()} from "
                    f"{email.sender}, {age_hours:.1f}h ago) claims milestone #{number} "
                    f"('{milestone.title}') shipped; the milestone's real state is '{milestone.state}'."
                ),
                confidence=confidence,
                evidence=[f"gmail:{email.id}", milestone.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    emails_path: Path | None = None,
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the-hand's gateway carries a live
    `ListEmails`/`ListMilestones` read for a connected Gmail account and
    these two loaders are swapped for real calls. The detection logic does
    not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    emails = load_emails(emails_path)
    milestones = load_milestones(milestones_path)
    surfaced, excluded = compute_gaps(emails, milestones, now=now)
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
