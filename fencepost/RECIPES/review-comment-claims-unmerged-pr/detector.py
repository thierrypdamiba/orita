"""The fifty-fifth real seam recipe. A pull request's own inline code
REVIEW comment invokes a real "ships/includes/merges/via #N" claim
against a pull request, but the named PR never actually merged.

The review-comment-side leg the claims-unmerged-pr family had never
grown. `readme-claims-unmerged-pr`, `release-claims-unmerged-pr`,
`tweet-claims-unmerged-pr`, `mention-claims-unmerged-pr`, and
`milestone-claims-unmerged-pr` cover every text surface this family has
ever checked -- README, a release, a tweet, a stranger's own X mention,
and a milestone's own description -- but none of them ever read a
GitHub-native comment surface at all. This recipe is the direct sibling of
`review-comment-claims-unfixed-issue` (task 582, the fifty-fourth real
recipe): that one named this exact boundary in its own README and
`recipe.json`, twice, before anyone built it -- "a closing-keyword claim
naming a real pull request is review-comment-claims-unmerged-pr's own
future seam, not this one's." This recipe is that future seam, built.

Reuses `review-comment-claims-unfixed-issue`'s own live
`ListReviewCommentsInARepository` scope and fixture shape (both already
proven live by `review-comment-dangling-reference`, the forty-fourth real
recipe) and `seam_engine.pr_claims.claimed_pr_numbers` -- the same
"ships/includes/merges/via #N" grammar `release-claims-unmerged-pr`,
`merged-pr-never-released`, `tweet-claims-unmerged-pr`,
`mention-claims-unmerged-pr`, and `milestone-claims-unmerged-pr` already
import from there -- rather than a sixth independently retyped copy of
the identical pattern.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files
(`review_comments.json`, `pulls.json`), shaped like what
`ListReviewCommentsInARepository` and `ListPullRequests` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table --
`ListReviewCommentsInARepository` live since `review-comment-dangling-
reference`; `ListPullRequests` used by nearly every recipe that reads the
PR tracker in this engine. No new scope is asked for anywhere in this
recipe.

The seam: a claim phrase ("ships #N" / "includes #N" / "merges #N" /
"via #N", case-insensitive) inside a review comment names a PR by
number. If that PR does not exist at all, it is excluded here -- that
broken reference belongs to a dangling-reference-family seam, not this
one's. If it exists and is merged, the claim was simply true -- excluded,
named not hidden. A review comment with no body at all (`null` or empty)
is never examined, the identical "not a claim at all" exclusion
`review-comment-dangling-reference.compute_gaps` and
`review-comment-claims-unfixed-issue.compute_gaps` already make for a
body-free comment. If the claimed PR exists and is NOT merged (still
open, or closed without merging), a reviewer's own permanent inline claim
already disagrees with GitHub's own record, and nothing on either
surface ever compares the two -- GitHub never auto-merges anything off a
review comment's own text regardless of what it says, the identical
"never going to resolve itself" reasoning
`review-comment-claims-unfixed-issue`'s own docstring already holds for
the issue side.

Confidence is age-gated off the review comment's own `updated_at`,
mirroring `review-comment-claims-unfixed-issue`'s own 0.55/0.85 bar
exactly (not `mention-claims-unmerged-pr`'s/`tweet-claims-unmerged-pr`'s
0.5/0.85 one) -- a review comment, like an issue/PR body or a milestone
description, is a text surface its own author can edit at any time,
unlike a mention or a tweet, posted once and standing, so the same
editable-surface grace window applies here that already applies to this
recipe's own direct sibling. A claim checked within 24 hours of the
comment's own last update scores 0.55 (below the confidence bar, shown
as a weighed coincidence, not hidden); at or past 24 hours it scores 0.85
(unambiguous -- nobody is coming back to fix it).
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
DEFAULT_REVIEW_COMMENTS_FIXTURE = _HERE.parents[1] / "fixtures" / "review_comment_claims_unmerged_pr" / "review_comments.json"
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "review_comment_claims_unmerged_pr" / "pulls.json"

# A claim checked within this many hours of the review comment's own
# updated_at may simply not have caught up yet -- the same editable-text-
# surface grace window review-comment-claims-unfixed-issue's own
# _EDIT_GRACE_WINDOW_HOURS already holds, applied here to the PR-claim
# seam instead of the issue-claim one.
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
class PullRequest:
    number: int
    title: str
    state: str
    merged: bool
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


def _confidence_for(updated_at: datetime, *, now: datetime) -> float:
    age_hours = (now - updated_at).total_seconds() / 3600.0
    return 0.85 if age_hours >= _EDIT_GRACE_WINDOW_HOURS else 0.55


def compute_gaps(
    comments: list[ReviewComment], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A review comment with no body at all is never
    examined at all -- it claims nothing about a second record, so there
    is no seam to weigh. A comment naming no claim phrase is excluded,
    named not hidden. A claimed PR is excluded, named not hidden, the
    moment it names no real PR at all, or the PR it names is already
    merged -- everything left over (a shipped-it claim the PR tracker
    itself contradicts) is surfaced, aged into a confidence score rank()
    can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for c in sorted(comments, key=lambda c: c.id):
        if not c.body:
            continue

        numbers = _claimed_pr_numbers(c.body)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{c.id}",
                headline=f"Review comment #{c.id} (on PR #{c.pull_request_number}) names no ships/includes/merges/via PR claim",
                detail=f"'{c.body}' ({c.url}) carries no claim-phrase reference. No seam here.",
                confidence=0.0,
                evidence=[c.url],
            ))
            continue

        # dict.fromkeys dedupes, order-preserving: a comment naming the
        # same #N twice must not produce two identical GapCandidates that
        # tie each other out of rank()'s SEPARATION_MARGIN (task 442).
        for number in dict.fromkeys(numbers):
            pr = _find_pull(number, pulls)
            if pr is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-pr-not-found-{c.id}-{number}",
                    headline=f"Review comment #{c.id} (on PR #{c.pull_request_number}) claims #{number} shipped, which doesn't exist",
                    detail=f"'{c.body}' ({c.url}) claims #{number} shipped, but no such PR exists. "
                           f"No seam here (see dangling-issue-reference/review-comment-dangling-reference).",
                    confidence=0.0,
                    evidence=[c.url],
                ))
                continue

            if pr.merged:
                excluded.append(GapCandidate(
                    slug=f"claim-true-{c.id}-{number}",
                    headline=f"Review comment #{c.id}'s claim about #{number} holds",
                    detail=f"'{c.body}' ({c.url}) claims #{number} shipped; PR #{number} "
                           f"('{pr.title}') is merged. No seam here.",
                    confidence=0.0,
                    evidence=[c.url, pr.url],
                ))
                continue

            confidence = _confidence_for(c.updated_at, now=now)
            age_hours = (now - c.updated_at).total_seconds() / 3600.0
            surfaced.append(GapCandidate(
                slug=f"review-comment-claims-unmerged-pr-{c.id}-{number}",
                headline=f"Review comment #{c.id} (on PR #{c.pull_request_number}) claims #{number} shipped, but #{number} never merged",
                detail=(
                    f"'{c.body}' ({c.url}, last updated {c.updated_at.isoformat()}, "
                    f"{age_hours:.1f}h ago) claims #{number} ('{pr.title}') shipped; the "
                    f"PR's real state is '{pr.state}', merged={pr.merged}. GitHub never "
                    f"auto-merges anything off a review comment's own text regardless -- "
                    f"this claim was never going to resolve itself."
                ),
                confidence=confidence,
                evidence=[c.url, pr.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    review_comments_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest
    WIP marker this recipe carries until the Hand's gateway carries a
    live `ListReviewCommentsInARepository`/`ListPullRequests` read for a
    connected account and these two loaders are swapped for real calls.
    The detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    comments = load_review_comments(review_comments_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(comments, pulls, now=now)
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
