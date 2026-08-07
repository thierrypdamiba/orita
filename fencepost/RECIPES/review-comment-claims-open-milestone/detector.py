"""The fifty-sixth real seam recipe. A pull request's own inline code
review comment invokes a real "milestone #N" claim phrase, but the named
milestone is not actually closed.

The missing review-comment-side leg of the claims-open-milestone family
alongside
[`../readme-claims-open-milestone/`](../readme-claims-open-milestone/),
[`../release-claims-open-milestone/`](../release-claims-open-milestone/),
[`../tweet-claims-open-milestone/`](../tweet-claims-open-milestone/),
[`../mention-claims-open-milestone/`](../mention-claims-open-milestone/),
and
[`../milestone-claims-open-milestone/`](../milestone-claims-open-milestone/)
-- those five already check whether a "milestone #N" claim phrase holds
against the milestone tracker, but every one of them reads either a
surface the town itself controls (its own README, release notes, another
milestone's own description, tweets) or a stranger's inbound X mention.
None of them ever read a GitHub-native surface at all. This recipe is the
direct sibling of
[`../review-comment-claims-unfixed-issue/`](../review-comment-claims-unfixed-issue/)
(the fifty-fourth real recipe) and
[`../review-comment-claims-unmerged-pr/`](../review-comment-claims-unmerged-pr/)
(the fifty-fifth): those two already proved a review comment is a
GitHub-native claim surface for the issue-side and PR-side legs of the
claims-X grid; this is the third and final leg the review-comment source
had never grown -- the six-sources-times-three-claim-types grid
`review-comment-claims-unfixed-issue`'s own README first named (five
sources, fifteen legs, before review-comment joined as a sixth) is
closed, complete, 6x18, the moment this recipe merges.

**The seam it watches:** a pull request's own inline code review comment
invokes a real "milestone #N" claim phrase against a milestone number --
"this also ships milestone #6001 while we're in here", "I think this
closes milestone #6003 too" -- but milestone #N is not actually closed
(still open). GitHub gives a milestone no auto-close-style keyword of its
own at all (the same reason `milestone-closed-never-released/detector.py`
invented the `milestone #N` grammar in the first place rather than
overloading the issue-side closing-keyword one or the PR-side
ships/includes/merges/via one) -- so a review comment naming a milestone
was never wired to anything on GitHub's side regardless of whether the
milestone ever closes. Two fixtures, no live account --
[`../../fixtures/review_comment_claims_open_milestone/review_comments.json`](../../fixtures/review_comment_claims_open_milestone/review_comments.json)
and
[`.../milestones.json`](../../fixtures/review_comment_claims_open_milestone/milestones.json)
-- shaped like what `ListReviewCommentsInARepository` and `ListMilestones`
would actually return. Both scopes already sit on `SCOPES.md`'s cleared
oath table (`ListReviewCommentsInARepository` live since
`review-comment-dangling-reference`, the forty-fourth real recipe;
`ListMilestones` used by every `*-claims-open-milestone` sibling). No new
scope is asked for anywhere in this recipe.

A claimed milestone that doesn't exist at all is excluded here, named not
hidden -- that broken reference belongs to a dangling-reference recipe's
own seam (over issues/PRs), not this one's (over milestones; no
review-comment-side milestone-dangling-reference recipe exists yet
either -- a genuinely separate future seam). A claimed milestone that IS
closed is excluded too -- the claim was simply true. A review comment
with no "milestone #N" claim phrase at all (a bare "same root cause as
#N" aside, or no `#N` at all) never becomes a candidate, and neither does
a review comment with no body at all -- neither claims anything about a
second record, so there is no seam to weigh.

Reuses `seam_engine.milestone_claims.claimed_milestone_numbers` verbatim
-- the same shared grammar `milestone-closed-never-released`,
`release-claims-open-milestone`, `milestone-closed-not-tweeted`,
`tweet-claims-open-milestone`, `mention-claims-open-milestone`, and
`readme-claims-open-milestone` already import from there -- rather than a
seventh independently retyped copy of the identical pattern.

**Confidence is age-gated off the review comment's own `updated_at`,
mirroring `review-comment-claims-unfixed-issue`'s and
`review-comment-claims-unmerged-pr`'s own 0.55/0.85 bar exactly rather
than `tweet-claims-open-milestone`'s/`release-claims-open-milestone`'s
0.5/0.85 one.** A review comment, like an issue/PR body or a milestone
description, is a text surface its own author can edit at any time --
unlike a tweet or a mention, posted once and standing, there is a real
"may simply not have caught up yet" grace period that means something
here. A claim checked within 24 hours of the comment's own last update
scores 0.55 (below the confidence bar, shown as a weighed coincidence,
not hidden); at or past 24 hours it scores 0.85 (unambiguous -- nobody is
coming back to fix it). See `recipe.json`'s `confidence_notes` for the
full reasoning.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "review_comment_claims_open_milestone"
DEFAULT_REVIEW_COMMENTS_FIXTURE = _FIXTURE_DIR / "review_comments.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# A claim checked within this many hours of the review comment's own
# updated_at may simply not have caught up yet -- the same editable-text-
# surface grace window review-comment-claims-unfixed-issue's own
# _EDIT_GRACE_WINDOW_HOURS already holds, applied here to the milestone
# leg of the claims-X grid instead of the issue leg.
_EDIT_GRACE_WINDOW_HOURS = 24.0


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
class ReviewComment:
    id: int
    pull_request_number: int
    body: str
    updated_at: datetime
    url: str


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    url: str


def load_review_comments(path: Path | None = None) -> list[ReviewComment]:
    rows = _load_rows(path or DEFAULT_REVIEW_COMMENTS_FIXTURE)
    return [
        ReviewComment(
            id=r["id"], pull_request_number=r["pull_request_number"],
            body=r.get("body") or "",
            updated_at=_parse_ts(r["updated_at"]), url=r["url"],
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


def _confidence_for(updated_at: datetime, *, now: datetime) -> float:
    age_hours = (now - updated_at).total_seconds() / 3600.0
    return 0.85 if age_hours >= _EDIT_GRACE_WINDOW_HOURS else 0.55


def compute_gaps(
    comments: list[ReviewComment], milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A review comment with no body at all is never
    examined at all -- it claims nothing about a second record, so there
    is no seam to weigh, the identical "not an invite at all" exclusion
    `review-comment-claims-unfixed-issue.compute_gaps` already makes for a
    body-free review comment. A comment naming no "milestone #N" claim
    phrase is excluded, named not hidden. A claimed milestone is excluded,
    named not hidden, the moment it names no real milestone at all, or the
    milestone it names is already closed -- everything left over (a
    shipped-it claim the milestone tracker itself contradicts) is
    surfaced, aged into a confidence score rank() can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for c in sorted(comments, key=lambda c: c.id):
        if not c.body:
            continue

        numbers = _claimed_milestone_numbers(c.body)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{c.id}",
                headline=f"Review comment #{c.id} (on PR #{c.pull_request_number}) names no milestone claim",
                detail=f"'{c.body}' ({c.url}) carries no 'milestone #N' claim phrase. No seam here.",
                confidence=0.0,
                evidence=[c.url],
            ))
            continue

        # dict.fromkeys dedupes, order-preserving: a comment naming the
        # same #N twice must not produce two identical GapCandidates that
        # tie each other out of rank()'s SEPARATION_MARGIN.
        for number in dict.fromkeys(numbers):
            milestone = _find_milestone(number, milestones)
            if milestone is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-not-found-{c.id}-{number}",
                    headline=f"Review comment #{c.id} (on PR #{c.pull_request_number}) claims milestone #{number}, which doesn't exist",
                    detail=f"'{c.body}' ({c.url}) claims milestone #{number} shipped, but no such milestone exists. "
                           f"No seam here (a broken reference is a dangling-reference recipe's own seam).",
                    confidence=0.0,
                    evidence=[c.url],
                ))
                continue

            if milestone.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{c.id}-{number}",
                    headline=f"Review comment #{c.id}'s claim about milestone #{number} holds",
                    detail=f"'{c.body}' ({c.url}) claims milestone #{number} ('{milestone.title}') shipped; "
                           f"the milestone is closed. No seam here.",
                    confidence=0.0,
                    evidence=[c.url, milestone.url],
                ))
                continue

            confidence = _confidence_for(c.updated_at, now=now)
            age_hours = (now - c.updated_at).total_seconds() / 3600.0
            surfaced.append(GapCandidate(
                slug=f"review-comment-claims-open-milestone-{c.id}-{number}",
                headline=f"Review comment #{c.id} (on PR #{c.pull_request_number}) claims milestone #{number} shipped, but it's still open",
                detail=(
                    f"'{c.body}' ({c.url}, last updated {c.updated_at.isoformat()}, "
                    f"{age_hours:.1f}h ago) claims milestone #{number} ('{milestone.title}') shipped; "
                    f"the milestone's real state is '{milestone.state}'. Milestones carry no auto-close "
                    f"trigger of their own regardless -- this claim was never going to resolve itself."
                ),
                confidence=confidence,
                evidence=[c.url, milestone.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    review_comments_path: Path | None = None,
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListReviewCommentsInARepository`/`ListMilestones` read for a connected
    account and these two loaders are swapped for real calls. The
    detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    comments = load_review_comments(review_comments_path)
    milestones = load_milestones(milestones_path)
    surfaced, excluded = compute_gaps(comments, milestones, now=now)
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
