"""The sixty-third real seam recipe: a pull request merged without a single
comment from a reviewer it explicitly requested.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before this
one: this module only ever reads two local fixture files
(`pull_requests.json`, `review_comments.json`), shaped like what
`ListPullRequests` and `ListReviewCommentsInARepository` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table under
the `github` row -- this recipe asks Arcade for nothing new. Neither has
ever been paired together in one recipe before; a new pairing of two
already-sworn scopes is not a new scope.

The seam it watches sits on a field none of the sixty-two prior recipes has
ever read: `requested_reviewers`, a real, structured field GitHub's own Pull
Request API returns -- the exact list of logins a PR's author (or a branch
protection rule) explicitly asked to sign off before the work lands. That
field is GitHub's own solicitation, not a claim buried in prose the way
every recipe in the claims-X family reads one -- there is no regex here,
nothing to parse out of a body, just one structured list compared against
one structured fact: did that named person ever actually leave an inline
review comment on this pull request at all? GitHub does not require the
answer to be yes before letting the PR merge (only a repository's own
branch-protection rule can force that, and nothing in this recipe assumes
one is configured), and once the PR merges, `requested_reviewers` is not
retroactively cleared or flagged just because the request went unanswered
-- the pending solicitation and the actual merge simply drift apart forever,
with nothing on GitHub's side that would ever compare them again. Neither
`ListPullRequests` alone (a merged PR's own `requested_reviewers` field
reads identically whether that person ever showed up or not) nor
`ListReviewCommentsInARepository` alone (an *absence* of a comment from one
particular login proves nothing on its own -- maybe nobody was ever asked)
shows this; only holding both at the same instant does.

This is a genuinely different axis from every family this repo has already
saturated. It is not the claims-X grid (seven text surfaces x three claim
phrases, 21/21 closed) -- there is no claim phrase here, no body text
parsed at all, just one structured field against one structured fact. It is
not the dangling-reference grid (nine legs, all asking whether a `#N`
target *exists*) -- this recipe never reads a `#N` reference anywhere. It
is not the `*-still-open` family (a promise made in prose that a target's
own state never caught up to) -- a requested reviewer is not a promise the
PR itself made about its own fate, it is a solicitation GitHub's own
tooling made on the PR's behalf, and the PR in question has *already*
resolved (merged) by the time this recipe has anything to say about it. It
is not the `*-not-tweeted`/`*-never-released`/`*-not-announced` family
(missing external publicity across toolkits) or the `*-credited`/
`*-thanked` family (an X handle missing from, or missing from, a credit
list) -- this recipe never leaves the `github` toolkit at all. And it is
not `merged-pr-branch-not-deleted` or `deleted-branch-pr-still-open`'s own
branch-lifecycle seam, even though it shares their general shape (a
post-resolution GitHub-native expectation nothing forces closed) -- those
two watch a branch's own survival; this one watches a *person's* named,
solicited, never-fulfilled review.

The claim is scoped narrowly on purpose, the same "no-grading law" every
sibling holds: this recipe never claims the requested reviewer dropped the
ball, ignored the request, or did anything wrong -- reviewers get
reassigned, go on leave, or get overtaken by a maintainer merging anyway,
all ordinary and blameless. It claims only the narrow, provable fact that
the two records disagree: GitHub's own solicitation names a login, and
that login left no review comment on this PR, ever, in the read-so-far
history. It also makes no claim about a review submitted with NO comment
text at all (a bare "Approve"/"Request changes" with nothing written) --
`ListReviewCommentsInARepository` reads only the inline, per-line comment
thread, not the review-submission event itself, so a silent approval is
outside what this recipe's own scope can see. That narrower, honest claim
is the whole of it.

Confidence is age-gated on how long the pull request has sat merged while
its named reviewer's request goes unanswered, reusing `merged-pr-branch-
not-deleted`'s and `deleted-branch-pr-still-open`'s own 24-hour bar rather
than inventing a new number for a structurally similar "GitHub offers no
forcing function, only a human notices" family: under 24 hours may simply
be a review still in flight, weighed in the tail at 0.5; at or past 24
hours it is unambiguous, a flat 0.85. A pull request that has not merged
yet (still open, or closed without merging) is excluded -- there is no
resolved promise to check a review against yet. A merged pull request that
named no requested reviewer at all is excluded too -- no solicitation was
ever made, so there is nothing this recipe could call unfulfilled. A
merged pull request with no recorded `merged_at` timestamp is excluded as
malformed, not guessed into either bucket. A blank requested-reviewer entry
(an empty string) is excluded outright -- not a real login. See
`recipe.json`'s `confidence_notes` for the full reasoning.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "merged_pr_requested_reviewer_never_reviewed"
DEFAULT_PULLS_FIXTURE = _FIXTURE_DIR / "pull_requests.json"
DEFAULT_REVIEW_COMMENTS_FIXTURE = _FIXTURE_DIR / "review_comments.json"

# A merged PR whose requested reviewer has not yet commented, under this
# age, may simply be a review still in flight -- not yet a gap. Matches
# merged-pr-branch-not-deleted's and deleted-branch-pr-still-open's own
# 24-hour bar for a structurally similar "GitHub offers no forcing
# function, only a human notices" family, rather than inventing a new
# number.
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
class PullRequest:
    number: int
    title: str
    state: str
    merged_at: datetime | None
    requested_reviewers: list[str]
    url: str


@dataclass
class ReviewComment:
    id: int
    pull_request_number: int
    author: str
    body: str
    url: str


def load_pull_requests(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [
        PullRequest(
            number=r["number"], title=r["title"], state=r["state"],
            merged_at=_parse_ts(r["merged_at"]) if r.get("merged_at") else None,
            requested_reviewers=list(r.get("requested_reviewers", [])),
            url=r["url"],
        )
        for r in rows
    ]


def load_review_comments(path: Path | None = None) -> list[ReviewComment]:
    rows = _load_rows(path or DEFAULT_REVIEW_COMMENTS_FIXTURE)
    return [
        ReviewComment(
            id=r["id"], pull_request_number=r["pull_request_number"],
            author=r["author"], body=r.get("body", ""), url=r["url"],
        )
        for r in rows
    ]


def _dedup_preserve_order(logins: list[str]) -> list[str]:
    """Every requested-reviewer login, de-duplicated, first-seen order --
    the same per-item contract `commit-closes-keyword-issue-closed-not-
    planned`'s own `_closing_refs` already holds for a different list."""
    seen: list[str] = []
    for login in logins:
        if login not in seen:
            seen.append(login)
    return seen


def _commenters_on(pr_number: int, review_comments: list[ReviewComment]) -> set[str]:
    return {c.author for c in review_comments if c.pull_request_number == pr_number}


def compute_gaps(
    pulls: list[PullRequest], review_comments: list[ReviewComment], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. One candidate per (pull request, requested reviewer)
    pair, the same per-pair contract this family's closing-keyword
    siblings already establish for a comparable "several separate
    promises inside one record" shape: a PR naming several requested
    reviewers makes a separate solicitation to each, and each is judged on
    its own merits. Every branch below is named, not silently folded into
    another."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for pr in pulls:
        if pr.state != "merged":
            excluded.append(GapCandidate(
                slug=f"not-merged-{pr.number}",
                headline=f"PR #{pr.number} has not merged",
                detail=(
                    f"'{pr.title}' ({pr.url}) reads state={pr.state!r}, not merged -- "
                    "no resolved promise exists yet for a review request to have gone unanswered against."
                ),
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        reviewers = _dedup_preserve_order(pr.requested_reviewers)
        reviewers = [r for r in reviewers if r]  # blank entries handled separately below
        has_blank = "" in pr.requested_reviewers

        if has_blank:
            excluded.append(GapCandidate(
                slug=f"blank-requested-reviewer-{pr.number}",
                headline=f"PR #{pr.number} carries a blank requested-reviewer entry",
                detail=f"'{pr.title}' ({pr.url}) lists an empty requested-reviewer login -- not a real login, excluded.",
                confidence=0.0,
                evidence=[pr.url],
            ))

        if not reviewers:
            if not has_blank:
                excluded.append(GapCandidate(
                    slug=f"no-requested-reviewer-{pr.number}",
                    headline=f"PR #{pr.number} merged with no requested reviewer on record",
                    detail=f"'{pr.title}' ({pr.url}) named no requested reviewer at all -- no solicitation was ever made.",
                    confidence=0.0,
                    evidence=[pr.url],
                ))
            continue

        if pr.merged_at is None:
            excluded.append(GapCandidate(
                slug=f"no-merged-timestamp-{pr.number}",
                headline=f"PR #{pr.number} reads merged but carries no merge timestamp",
                detail=f"'{pr.title}' ({pr.url}) reads state=merged but carries no merged_at -- a malformed record, not an unresolved seam.",
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        commenters = _commenters_on(pr.number, review_comments)
        age_hours = (now - pr.merged_at).total_seconds() / 3600.0

        for reviewer in reviewers:
            if reviewer in commenters:
                excluded.append(GapCandidate(
                    slug=f"reviewer-commented-{pr.number}-{reviewer}",
                    headline=f"PR #{pr.number}'s requested reviewer @{reviewer} did leave a review comment",
                    detail=f"'{pr.title}' ({pr.url}) requested @{reviewer}, who left at least one review comment on it. Working as intended.",
                    confidence=0.0,
                    evidence=[pr.url],
                ))
                continue

            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"merged-pr-requested-reviewer-never-reviewed-{pr.number}-{reviewer}",
                headline=f"PR #{pr.number} merged without @{reviewer}'s requested review ever landing a comment",
                detail=(
                    f"'{pr.title}' ({pr.url}) named @{reviewer} as a requested reviewer, merged "
                    f"{pr.merged_at.isoformat()} ({age_hours:.1f}h before this scan), and no review "
                    f"comment from @{reviewer} appears anywhere in the read-so-far history on this PR."
                ),
                confidence=confidence,
                evidence=[pr.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    pulls_path: Path | None = None,
    review_comments_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListPullRequests`/`ListReviewCommentsInARepository` read and these two
    loaders are swapped for real reads. The detection logic does not
    change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    pulls = load_pull_requests(pulls_path)
    review_comments = load_review_comments(review_comments_path)
    surfaced, excluded = compute_gaps(pulls, review_comments, now=now)
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
