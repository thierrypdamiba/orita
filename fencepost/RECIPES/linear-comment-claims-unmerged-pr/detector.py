"""The seventy-first real seam recipe: a comment left on a Linear issue
claims a pull request shipped ("ships/includes/merges/via #N"), but the
named PR is not actually merged.

The Linear source's third and final `claims-X` leg, alongside
`linear-comment-claims-unfixed-issue` (task 600, the sixty-eighth real
recipe, the closing-keyword leg against the issue tracker) and
`linear-comment-claims-open-milestone` (task 602, the seventieth real
recipe, the milestone-claim leg against the milestone tracker). That
second recipe's own docstring named this exact boundary before anyone
built it -- "A third leg, `linear-comment-claims-unmerged-pr`, remains
open for a future hour -- this recipe closes one cell of that grid, not
all three." This recipe is that future hour, built. With this recipe
shipped, the claims-X grid (ten sources -- mention, tweet, issue-comment,
review-comment, milestone, readme, release, commit, slack-message,
linear-comment -- times three targets -- open-milestone, unfixed-issue,
unmerged-pr) has exactly one genuinely open cell left:
`slack-message-claims-unmerged-pr`. `commit-claims-unfixed-issue` and
`commit-claims-unmerged-pr` remain the two structurally-unfillable cells
task 599's own history already named -- `commit-closes-keyword-issue-
still-open` and `commit-closes-keyword-pr-still-open` already cover that
identical semantic space under a different recipe name, so filling those
two cells a second time under the `claims-X` name would be the same fact
asserted twice, not a new one.

This is the Linear-side twin of `review-comment-claims-unmerged-pr` (task
585, the fifty-fifth real recipe, the GitHub review-comment leg of the
identical PR-claim check) -- same seam shape (an inbound "shipped it"
claim against the PR tracker's own state), a different surface entirely.
Reuses `seam_engine.pr_claims.claimed_pr_numbers` verbatim -- the same
shared "ships/includes/merges/via #N" grammar `release-claims-unmerged-
pr`, `merged-pr-never-released`, `tweet-claims-unmerged-pr`, `mention-
claims-unmerged-pr`, `milestone-claims-unmerged-pr`, and `review-comment-
claims-unmerged-pr` already import from there -- rather than a seventh
independently retyped copy of the identical pattern.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`comments.json`,
`pulls.json`), shaped like what a real `SearchIssueComments`/
`ListPullRequests` read would return. `ListPullRequests` is already
cleared on `SCOPES.md`'s oath table under the `github` row, used by nearly
every recipe in this engine that reads the PR tracker. `SearchIssueComments`
is the same scope `linear-comment-claims-unfixed-issue` (task 600) and
`linear-comment-claims-open-milestone` (task 602) already cleared through
`seam_engine.recipes.validate_recipe`'s oath -- this recipe asks for
nothing new, and `linear+github` is not a new toolkit pair either -- both
of this recipe's own Linear siblings already proposed it. See `SCOPES.md`'s
own WIP note for the `linear` toolkit: the-hand gateway holds a real,
live, upstream `arcade-linear` connection today, but exposes zero
Linear-capable tools on the live gateway -- the identical "connected
upstream, not wired into the gateway" shape `SCOPES.md`'s Gmail/Calendar
and Slack WIP notes already document for two other toolkits.

The seam: a `ships #N`/`includes #N`/`merges #N`/`via #N` claim phrase
inside a Linear issue comment names a pull request by number. If that PR
does not exist at all, it is excluded here -- that broken reference
belongs to a future Linear-side dangling-reference recipe, not this one.
If it exists and is merged, the claim was simply true -- excluded, named
not hidden. If it exists and is NOT merged (still open, or closed without
merging), a comment already sitting on a Linear issue disagrees with
GitHub's own record, and nothing on either platform ever compares the
two -- GitHub never auto-merges anything off a Linear comment's own text
regardless of what it says. This never grades or blames whoever left the
comment -- CONTRIBUTING.md's "No grading, ever" law, same as every recipe
in this engine: the headline names the gap between two records, not a
person's error.

Confidence is age-gated by the comment's own `created_at`, holding
`linear-comment-claims-open-milestone`'s own 0.85/0.5 bar exactly -- NOT
`review-comment-claims-unmerged-pr`'s 0.55/0.85 editable-surface bar. A
Linear issue comment, like a Slack channel message, a tweet, or a mention,
is posted once and stands; unlike a GitHub review comment, it is not a
surface its own author can quietly edit out from under the claim, so the
"may simply not have caught up yet" grace window that justifies review-
comment-claims-unmerged-pr's higher floor does not apply here -- the
identical "posted once and stands" reasoning linear-comment-claims-open-
milestone's own docstring already gives for holding slack-message-claims-
open-milestone's bar exactly rather than re-deriving one of its own. A
claim checked within 24 hours of posting might still be a race (the PR
actually merging moments after the comment went out) rather than a
settled overclaim (0.5, below the confidence bar, shown as a weighed
coincidence, not hidden). At or past 24 hours with the named PR still
unmerged, it is unambiguous (flat 0.85). The check itself is objective:
the claimed PR's own live `merged`/`state` fields, verified against
`ListPullRequests`, not a guess about which tracker the commenter meant.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "linear_comment_claims_unmerged_pr"
DEFAULT_COMMENTS_FIXTURE = _FIXTURE_DIR / "comments.json"
DEFAULT_PULLS_FIXTURE = _FIXTURE_DIR / "pulls.json"

# A claim checked within this window of the comment's own created_at may
# just be a race rather than a genuine, settled public overclaim -- the
# identical bar linear-comment-claims-open-milestone/slack-message-claims-
# open-milestone hold themselves to.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Comment:
    id: str
    issue_identifier: str
    author: str
    text: str
    created_at: datetime
    url: str


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    merged: bool
    url: str


def _load_rows(path: Path) -> list[Any]:
    """Refuses a syntactically valid but non-list payload with a named
    error, the same guard every sibling detector's own `_load_rows`
    holds."""
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_comments(path: Path | None = None) -> list[Comment]:
    rows = _load_rows(path or DEFAULT_COMMENTS_FIXTURE)
    return [
        Comment(
            id=r["id"], issue_identifier=r["issue_identifier"], author=r["author"],
            text=r["text"], created_at=_parse_ts(r["ts"]), url=r["url"],
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
    comments: list[Comment], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed PR is excluded, named not hidden, the
    moment it names no real PR at all, or the PR it names is already
    merged -- everything left over (a shipped-it claim the PR tracker
    itself contradicts) is surfaced, aged into a confidence score rank()
    can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for comment in comments:
        numbers = _claimed_pr_numbers(comment.text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{comment.id}",
                headline=f"{comment.issue_identifier}'s comment {comment.id} names no ships/includes/merges/via PR claim",
                detail=f"'{comment.text}' carries no claim-phrase reference. No seam here.",
                confidence=0.0,
                evidence=[comment.url],
            ))
            continue

        # dict.fromkeys dedupes, order-preserving: a comment naming the
        # same #N twice must not produce two identical GapCandidates that
        # tie each other out of rank()'s SEPARATION_MARGIN, the same
        # dedup discipline review-comment-claims-unmerged-pr's own
        # compute_gaps already holds (task 442).
        for number in dict.fromkeys(numbers):
            pr = _find_pull(number, pulls)
            if pr is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-pr-not-found-{comment.id}-{number}",
                    headline=f"{comment.issue_identifier}'s comment {comment.id} claims #{number} shipped, which doesn't exist",
                    detail=f"'{comment.text}' claims #{number} shipped, but no such PR exists. No seam here.",
                    confidence=0.0,
                    evidence=[comment.url],
                ))
                continue

            if pr.merged:
                excluded.append(GapCandidate(
                    slug=f"claim-true-{comment.id}-{number}",
                    headline=f"{comment.issue_identifier}'s comment {comment.id}'s claim about #{number} holds",
                    detail=f"'{comment.text}' claims #{number} ('{pr.title}') shipped; PR #{number} is merged. No seam here.",
                    confidence=0.0,
                    evidence=[comment.url, pr.url],
                ))
                continue

            age_hours = (now - comment.created_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"linear-comment-claims-unmerged-pr-{comment.id}-{number}",
                headline=f"{comment.issue_identifier}'s comment {comment.id} claims #{number} shipped, but #{number} never merged",
                detail=(
                    f"'{comment.text}' (posted {comment.created_at.isoformat()} on "
                    f"{comment.issue_identifier}, {age_hours:.1f}h ago) claims #{number} "
                    f"('{pr.title}') shipped; the PR's real state is '{pr.state}', "
                    f"merged={pr.merged}."
                ),
                confidence=confidence,
                evidence=[comment.url, pr.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    comments_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the-hand's gateway carries a live
    `SearchIssueComments`/`ListPullRequests` read for a connected Linear
    workspace and these two loaders are swapped for real calls. The
    detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    comments = load_comments(comments_path)
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
