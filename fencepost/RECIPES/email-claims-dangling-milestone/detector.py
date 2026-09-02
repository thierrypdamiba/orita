"""The hundred-first real seam recipe: an inbound email invokes a real
"milestone #N" claim phrase, but no milestone with that number exists at
all.

`email-claims-open-milestone` (task 1195, the hundredth real recipe) drew
this exact line in its own docstring, the same line
`linear-comment-claims-open-milestone` drew before it: a claimed milestone
number that names no real milestone at all is excluded there, named not
hidden -- "that broken reference is `email-dangling-reference`'s own seam,
not this one's." That line was wrong about which recipe would eventually
close it -- `email-dangling-reference` (task 1082) watches a bare `#N`
against the issue/PR number space, and never opens `ListMilestones` at
all, so the "milestone #N" dangling claim it gestured at was never really
that recipe's seam either. This recipe is the one that actually closes it:
the Gmail-sourced sibling of `commit-claims-dangling-milestone`,
`issue-body-claims-dangling-milestone`, `issue-comment-claims-dangling-
milestone`, `linear-comment-claims-dangling-milestone`, `mention-claims-
dangling-milestone`, `milestone-claims-dangling-milestone`, `readme-
claims-dangling-milestone`, `release-claims-dangling-milestone`,
`review-comment-claims-dangling-milestone`, `slack-message-claims-
dangling-milestone`, and `tweet-claims-dangling-milestone`, which close
the identical seam for a commit message, an issue/PR body, an issue/PR
timeline comment, a Linear issue comment, an X mention, a milestone's own
description, a README, a release, a pull request's own inline review
comment, a Slack channel message, and a tweet respectively -- the
twelfth leg of that family, and the fifth leg the `claims-*-milestone`
pair of families has now grown on the Gmail surface (after
`email-claims-unfixed-issue`, `email-dangling-reference`,
`email-claims-unmerged-pr`, and `email-claims-open-milestone`), closing
the one leg the `email` family itself had never grown: every other
`claims-*` source in this engine (issue-body, issue-comment,
linear-comment, mention, readme, review-comment, slack-message) already
carries all five legs of its own family (claims-dangling-milestone,
claims-open-milestone, claims-unfixed-issue, claims-unmerged-pr,
dangling-reference); `email` was the one source stuck at four.

Deliberately reuses `seam_engine.milestone_claims.claimed_milestone_
numbers` verbatim -- the same shared "milestone #N" grammar twenty-five
sibling recipes already import -- rather than a twenty-sixth independently
retyped copy of the identical pattern.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`emails.json`,
`milestones.json`), shaped like what a real `ListEmails`/`ListMilestones`
read would return. `ListMilestones` already sits on `SCOPES.md`'s cleared
oath table under the `github` row, used by every milestone-claim recipe
in this engine. `ListEmails` is not a new scope -- it has sat on the
Gmail row since ROADMAP.md #16, and `email-claims-unfixed-issue`,
`email-dangling-reference`, `email-claims-unmerged-pr`, and
`email-claims-open-milestone` already declare it -- this recipe asks for
nothing new. See `SCOPES.md`'s own WIP note for `gmail_calendar.py`:
the-hand gateway's connected Google account carries `gmail.readonly`
among its granted OAuth scopes, but exposes zero Gmail-capable tools on
the live gateway today -- the identical "connected upstream, not wired
into the gateway" shape `SCOPES.md`'s Slack and Linear WIP notes each
already document for their own toolkit. This recipe is fixture-only,
MOCK ONLY, and never attempts a live network call.

Genuinely distinct from `email-dangling-reference`: that recipe watches a
bare same-repo `#N` posted inside an inbound email's own body against
BOTH the issue list and the PR list -- GitHub's shared issue/PR number
sequence -- and never once opens `ListMilestones`. A milestone lives in
its own, separate number space that issues and pull requests never
touch, so a `#N` that resolves cleanly as an issue could still be a
dangling MILESTONE claim, and a `#N` that is a real milestone could just
as easily collide with a real issue number. Confusing the two spaces
would be exactly the false-positive failure Ogun's law calls fatal -- so
this recipe reads `claimed_milestone_numbers`'s own "milestone #N" phrase
grammar, never the bare-`#N` grammar `email-dangling-reference` already
owns.

Also genuinely distinct from `email-claims-open-milestone`: that recipe
excludes a claimed milestone number that names no real milestone at all
("no such milestone exists, see email-dangling-reference" -- its own
excluded-not-surfaced text, which this recipe is the actual referent
of), and surfaces only a claim that names a real, still-OPEN milestone.
This recipe is the mirror image: it excludes any claim that resolves to
a REAL milestone at all, open OR closed -- whether the claim is TRUE is
`email-claims-open-milestone`'s own remit, not this one's. This recipe
asks a narrower question: does the claimed number resolve to anything
real, full stop.

The claim stays narrow, the same no-grading law every sibling holds: an
email that merely mentions a bare `#N` in passing ("see #4604 for
background, nothing shipped to claim here") makes no milestone claim at
all, and is excluded, not guessed into either bucket -- that bare shape
is `email-dangling-reference`'s own seam, not this one's.

Confidence is flat (0.8), not age-gated -- mirrors every other
`*-claims-dangling-milestone` sibling's own reasoning rather than
`email-claims-open-milestone`'s 24-hour edit-grace bar. That bar exists
because an OPEN milestone could close at any moment, so a fresh claim
about it might just be a race the email hasn't caught up to yet; a
milestone number that does not exist right now will not spontaneously
start existing later no matter how long the email sits unread, so there
is no grace period that means anything here.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "email_claims_dangling_milestone"
DEFAULT_EMAILS_FIXTURE = _FIXTURE_DIR / "emails.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# Flat, not age-gated -- see the module docstring. Mirrors every other
# `*-claims-dangling-milestone` sibling's own `_DANGLING_CONFIDENCE`
# exactly (0.8): a nonexistent milestone number will not spontaneously
# start existing, whatever the age of the email naming it.
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
    own `compute_gaps`. An email naming no 'milestone #N' claim phrase at
    all is excluded, named not hidden. A claimed milestone is excluded,
    named not hidden, the moment it names a real milestone (open or
    closed, this recipe does not care which) -- everything left over (a
    claimed milestone number with no real milestone behind it at all) is
    surfaced at a flat confidence.

    `now` is accepted, unused -- kept for interface parity with every
    other recipe's own `compute_gaps(..., now=...)` shape (`run_recipe_
    scan` always threads one through), the identical "unused today, kept
    for the shape" choice every other `*-claims-dangling-milestone`
    sibling's own detector already makes and explains for the identical
    reason: this recipe's confidence is flat, not age-gated, so there is
    nothing here for `now` to weigh against."""
    del now  # unused today; kept for interface parity, see docstring above.
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

        # dict.fromkeys dedupes, order-preserving: an email naming the
        # same #N twice must not produce two identical GapCandidates that
        # tie each other out of rank()'s SEPARATION_MARGIN, the same
        # guard every dangling-milestone sibling already holds.
        for number in dict.fromkeys(numbers):
            milestone = _find_milestone(number, milestones)
            if milestone is not None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-exists-{email.id}-{number}",
                    headline=f"Email {email.id}'s claimed milestone #{number} is real",
                    detail=(
                        f"'{email.body}' claims milestone #{number} "
                        f"('{milestone.title}', state '{milestone.state}'); the milestone "
                        "exists. Whether the claim itself is TRUE is a different recipe's "
                        "seam (email-claims-open-milestone), not this one's. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[f"gmail:{email.id}", milestone.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"email-claims-dangling-milestone-{email.id}-{number}",
                headline=f"Email {email.id} ('{email.subject}') claims milestone #{number}, which doesn't exist",
                detail=(
                    f"'{email.body}' claims milestone #{number}, but no milestone with "
                    "that number exists at all. An inbox renders the number as plain text "
                    "regardless; nothing on either platform ever checks a 'milestone #N' "
                    "claim phrase inside an inbound email against the real milestone "
                    "tracker."
                ),
                confidence=_DANGLING_CONFIDENCE,
                evidence=[f"gmail:{email.id}"],
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
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest
    WIP marker this recipe carries until the-hand's gateway carries a
    live `ListEmails`/`ListMilestones` read for a connected Gmail account
    and these two loaders are swapped for real calls. The detection logic
    does not change one line when that happens."""
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
