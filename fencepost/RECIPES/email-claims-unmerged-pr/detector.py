"""The ninety-ninth real seam recipe, and the twelfth leg of the
claims-unmerged-pr family. `commit-claims-unmerged-pr`, `readme-claims-
unmerged-pr`, `release-claims-unmerged-pr`, `milestone-claims-unmerged-pr`,
`issue-body-claims-unmerged-pr`, `issue-comment-claims-unmerged-pr`,
`review-comment-claims-unmerged-pr`, and `tweet-claims-unmerged-pr` each
check a "shipped it" claim the town made about ITSELF, somewhere the town
fully controls; `mention-claims-unmerged-pr`, `slack-message-claims-
unmerged-pr`, and `linear-comment-claims-unmerged-pr` check the identical
claim against three inbound surfaces the town does not control. None of
those eleven ever read an inbound email.

`email-claims-unfixed-issue`'s own docstring (the ninety-third real
recipe) opened the Gmail toolkit against the closing-keyword grammar and
the issue tracker; `email-dangling-reference` (the ninety-eighth) opened
it a second time against the bare `#N` reference. This recipe opens it a
third time against the "ships/includes/merges/via #N" PR-claim grammar --
the Gmail-side twin of `mention-claims-unmerged-pr`, `slack-message-claims-
unmerged-pr`, and `linear-comment-claims-unmerged-pr`, exactly the same
"twin the inbound siblings, not the town-controlled ones" shape `email-
claims-unfixed-issue` already drew against `mention-claims-unfixed-issue`/
`slack-message-claims-unfixed-issue`/`linear-comment-claims-unfixed-issue`.

Reuses `seam_engine.pr_claims.claimed_pr_numbers` verbatim -- the same
shared "ships/includes/merges/via #N" grammar every claims-unmerged-pr
sibling already imports from there -- rather than a twelfth independently
retyped copy of the identical pattern.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`emails.json`,
`pulls.json`), shaped like what a real `ListEmails`/`ListPullRequests`
read would return. `ListPullRequests` already sits on `SCOPES.md`'s
cleared oath table under the `github` row, used by nearly every recipe in
this engine. `ListEmails` is the same scope `email-claims-unfixed-issue`
and `email-dangling-reference` already ask for -- no new scope is asked
for anywhere in this recipe. See `SCOPES.md`'s own WIP note for this
toolkit: the-hand gateway's connected Google account carries
`gmail.readonly` among its granted OAuth scopes, but exposes zero
Gmail-capable tools anywhere in its live MCP toolset today -- the
identical "connected upstream, not wired into the gateway" shape
`SCOPES.md`'s Slack/Linear WIP notes each carry for their own toolkit.

The seam: a claim phrase ("ships #N" / "includes #N" / "merges #N" /
"via #N", case-insensitive) inside an inbound email's own body names a
pull request by number. If that PR does not exist at all, it is excluded
here -- that broken reference is `email-dangling-reference`'s own seam,
not this one's. If it exists and is merged, the claim was simply true --
excluded, named not hidden. If it exists and is NOT merged (still open,
or closed without merging), an email already sitting in a connected inbox
disagrees with GitHub's own record, and nothing on either platform ever
compares the two. This never grades or blames whoever sent the email --
CONTRIBUTING.md's "No grading, ever" law, same as every recipe in this
engine: the headline names the gap between two records, not a person's
error.

Confidence is age-gated by the email's own `received_at`, holding
`mention-claims-unmerged-pr`'s/`slack-message-claims-unmerged-pr`'s/
`linear-comment-claims-unmerged-pr`'s identical 0.85/0.5 bar exactly --
not an independently re-reasoned number just because the toolkit is new.
A claim checked within 24 hours of the email landing might still be a
race (the real merge landing moments after the email went out) rather
than a settled overclaim. The check itself is objective: the claimed
PR's own live `state`/`merged` fields, verified against
`ListPullRequests`, not a guess about which tracker the sender meant --
the same reasoning every claims-unmerged-pr sibling already gives for
holding the identical bar.
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
DEFAULT_EMAILS_FIXTURE = _HERE.parents[1] / "fixtures" / "email_claims_unmerged_pr" / "emails.json"
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "email_claims_unmerged_pr" / "pulls.json"

# A claim checked within this window of the email's own received_at may
# just be a race rather than a genuine, settled overclaim -- the identical
# bar mention-claims-unmerged-pr/slack-message-claims-unmerged-pr/
# linear-comment-claims-unmerged-pr each hold themselves to.
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
class PullRequest:
    number: int
    title: str
    state: str
    merged: bool
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
    emails: list[Email], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed PR is excluded, named not hidden, the
    moment it names no real PR at all, or the PR it names is actually
    merged -- everything left over (a shipped-it claim the PR tracker
    itself contradicts) is surfaced, aged into a confidence score rank()
    can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for email in emails:
        numbers = _claimed_pr_numbers(email.body)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{email.id}",
                headline=f"Email {email.id} ('{email.subject}') names no ships/includes/merges/via PR claim",
                detail=f"'{email.body}' carries no claim-phrase reference. No seam here.",
                confidence=0.0,
                evidence=[f"gmail:{email.id}"],
            ))
            continue

        seen: set[int] = set()
        for number in numbers:
            if number in seen:
                continue
            seen.add(number)

            pr = _find_pull(number, pulls)
            if pr is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-pr-not-found-{email.id}-{number}",
                    headline=f"Email {email.id} ('{email.subject}') claims #{number} shipped, which doesn't exist",
                    detail=f"'{email.body}' claims #{number} shipped, but no such PR exists. No seam here (see email-dangling-reference).",
                    confidence=0.0,
                    evidence=[f"gmail:{email.id}"],
                ))
                continue

            if pr.merged:
                excluded.append(GapCandidate(
                    slug=f"claim-true-{email.id}-{number}",
                    headline=f"Email {email.id}'s claim about #{number} holds",
                    detail=f"'{email.body}' claims #{number} shipped; PR #{number} ('{pr.title}') is merged. No seam here.",
                    confidence=0.0,
                    evidence=[f"gmail:{email.id}", pr.url],
                ))
                continue

            age_hours = (now - email.received_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"email-claims-unmerged-pr-{email.id}-{number}",
                headline=f"Email {email.id} ('{email.subject}') claims #{number} shipped, but #{number} never merged",
                detail=(
                    f"'{email.body}' (received {email.received_at.isoformat()} from "
                    f"{email.sender}, {age_hours:.1f}h ago) claims #{number} "
                    f"('{pr.title}') shipped; the PR's real state is '{pr.state}', merged={pr.merged}."
                ),
                confidence=confidence,
                evidence=[f"gmail:{email.id}", pr.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    emails_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the-hand's gateway carries a live
    `ListEmails`/`ListPullRequests` read for a connected Gmail account and
    these two loaders are swapped for real calls. The detection logic does
    not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    emails = load_emails(emails_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(emails, pulls, now=now)
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
