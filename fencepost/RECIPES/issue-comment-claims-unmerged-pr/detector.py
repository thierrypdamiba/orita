"""The sixtieth real seam recipe. An issue or pull request's own ordinary
TIMELINE comment (not an inline review comment, not the opening body)
invokes a real "ships/includes/merges/via #N" claim phrase against a
pull request, but the named PR never actually merged.

The ninth leg the claims-X family has grown on the issue-comment side,
and the third of the timeline-comment surface's own three claim types.
`issue-comment-claims-unfixed-issue` (task 590, the fifty-eighth real
recipe) and `issue-comment-claims-open-milestone` (task 591, the
fifty-ninth real recipe) already proved the timeline-comment surface
carries the unfixed-issue and open-milestone legs; both recipes' own
README named this exact remaining cell as "the one remaining leg" before
anyone built it. This recipe is that leg, the direct sibling of
`review-comment-claims-unmerged-pr` (task 585, the fifty-fifth real
recipe) applied to the timeline-comment surface instead of the inline
review-comment one. With this recipe shipped, the claims-X grid's
issue-comment row stands complete at 3/3 (unfixed-issue, open-milestone,
unmerged-pr), the eighth of the grid's seven-then-eight sources to reach
full coverage.

**The seam it watches:** an issue or pull request's own ordinary
conversation comment invokes a real "ships/includes/merges/via #N" claim
phrase against a PR number -- "this also ships #901 while we're in
here", "I think this merges #903 too" -- but PR #N is not actually
merged (still open, or closed without merging). GitHub never merges
anything off an ordinary timeline comment's own text -- it has never
once, in GitHub's history, honored a closing keyword or a claim phrase
typed into a conversation comment on either an issue or a pull request
(GitHub shares one issue-comments endpoint between the two, which is why
this recipe's own `issue_number` field can name either object) -- so a
false claim here is exactly as durable as its two timeline-comment
siblings' false claims: nothing was ever going to catch it regardless of
what happens to the PR.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`issue_comments.json`,
`pulls.json`), shaped like what a live read of an issue/PR's ordinary
timeline comments and `ListPullRequests` would actually return.
`ListPullRequests` already sits on `SCOPES.md`'s cleared oath table, used
by nearly every recipe in this engine that reads the PR tracker -- but
per `SCOPES.md`'s own WIP note on `issue-comment-dangling-reference`,
checked live again this hour via `tools/gateway_toolset_check.py`'s own
search against this hour's real the-hand tool list: **no read-only tool
shaped like "list issue/PR comments" is exposed anywhere on the-hand
gateway today.** This recipe's own `recipe.json` declares only the one
scope that IS already cleared (`ListPullRequests`) -- it does not invent
or claim a second scope the Oath never swore to;
`seam_engine.recipes.validate_recipe`'s own check 3/3 would refuse that
on sight regardless. `source: "fixture"` in `run_recipe_scan`'s own
output is the honest WIP marker, the identical shape both timeline-
comment siblings and the Gmail/Calendar note already carry for a
different toolkit or surface: the day a live tool for ordinary issue/PR
comments appears, only the fixture loader swaps for a real call -- the
detection logic does not change one line.

Deliberately reuses `seam_engine.pr_claims.claimed_pr_numbers` verbatim
-- the same shared grammar `review-comment-claims-unmerged-pr`,
`release-claims-unmerged-pr`, `merged-pr-never-released`, `tweet-claims-
unmerged-pr`, `mention-claims-unmerged-pr`, and `milestone-claims-
unmerged-pr` already import from there -- rather than a seventh
independently retyped copy of the identical pattern.

The seam: a claim phrase ("ships #N" / "includes #N" / "merges #N" /
"via #N", case-insensitive) inside a timeline comment names a PR by
number. If that PR does not exist at all, it is excluded here, named not
hidden -- that broken reference is `issue-comment-dangling-reference`'s
own seam, not this one's. If it exists and is merged, the claim was
simply true -- excluded, named not hidden. A comment with no body at all
is never examined, the identical "not a claim at all" exclusion
`issue-comment-claims-open-milestone.compute_gaps` already makes for a
body-free comment.

Confidence is age-gated off the comment's own `updated_at`, mirroring
`issue-comment-claims-open-milestone`'s and `review-comment-claims-
unmerged-pr`'s own 0.55/0.85 bar rather than `mention-claims-unmerged-
pr`'s/`tweet-claims-unmerged-pr`'s 0.5/0.85 one: an ordinary timeline
comment, like a review comment or an issue/PR body, is a text surface
its own author can still edit at any time, unlike a mention or a tweet,
which is posted once and stands. 0.55 within 24 hours of the comment's
own last update (the claim, or the comment carrying it, may simply not
have caught up yet); 0.85 at or past 24 hours (nobody is coming back to
fix it). See `recipe.json`'s `confidence_notes` for the full reasoning.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "issue_comment_claims_unmerged_pr"
DEFAULT_ISSUE_COMMENTS_FIXTURE = _FIXTURE_DIR / "issue_comments.json"
DEFAULT_PULLS_FIXTURE = _FIXTURE_DIR / "pulls.json"

# A claim checked within this many hours of the comment's own updated_at
# may simply not have caught up yet -- the same editable-text-surface
# grace window issue-comment-claims-open-milestone's own
# _EDIT_GRACE_WINDOW_HOURS already holds, applied here to the PR leg of
# the claims-X grid instead of the milestone leg.
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
class IssueComment:
    id: int
    issue_number: int
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


def load_issue_comments(path: Path | None = None) -> list[IssueComment]:
    rows = _load_rows(path or DEFAULT_ISSUE_COMMENTS_FIXTURE)
    return [
        IssueComment(
            id=r["id"], issue_number=r["issue_number"],
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
    comments: list[IssueComment], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A comment with no body at all is never examined
    at all -- it claims nothing about a second record, so there is no
    seam to weigh. A comment naming no claim phrase is excluded, named
    not hidden. A claimed PR is excluded, named not hidden, the moment it
    names no real PR at all, or the PR it names is already merged --
    everything left over (a shipped-it claim the PR tracker itself
    contradicts) is surfaced, aged into a confidence score rank() can
    honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for c in sorted(comments, key=lambda c: c.id):
        if not c.body:
            continue

        numbers = _claimed_pr_numbers(c.body)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{c.id}",
                headline=f"Comment #{c.id} (on #{c.issue_number}'s own thread) names no ships/includes/merges/via PR claim",
                detail=f"'{c.body}' ({c.url}) carries no claim-phrase reference. No seam here.",
                confidence=0.0,
                evidence=[c.url],
            ))
            continue

        # dict.fromkeys dedupes, order-preserving: a comment naming the
        # same #N twice must not produce two identical GapCandidates that
        # tie each other out of rank()'s SEPARATION_MARGIN.
        for number in dict.fromkeys(numbers):
            pr = _find_pull(number, pulls)
            if pr is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-pr-not-found-{c.id}-{number}",
                    headline=f"Comment #{c.id} (on #{c.issue_number}'s own thread) claims #{number} shipped, which doesn't exist",
                    detail=f"'{c.body}' ({c.url}) claims #{number} shipped, but no such PR exists. "
                           f"No seam here (a broken reference is a dangling-reference recipe's own seam).",
                    confidence=0.0,
                    evidence=[c.url],
                ))
                continue

            if pr.merged:
                excluded.append(GapCandidate(
                    slug=f"claim-true-{c.id}-{number}",
                    headline=f"Comment #{c.id}'s claim about #{number} holds",
                    detail=f"'{c.body}' ({c.url}) claims #{number} shipped; PR #{number} "
                           f"('{pr.title}') is merged. No seam here.",
                    confidence=0.0,
                    evidence=[c.url, pr.url],
                ))
                continue

            confidence = _confidence_for(c.updated_at, now=now)
            age_hours = (now - c.updated_at).total_seconds() / 3600.0
            surfaced.append(GapCandidate(
                slug=f"issue-comment-claims-unmerged-pr-{c.id}-{number}",
                headline=f"Comment #{c.id} (on #{c.issue_number}'s own thread) claims #{number} shipped, but #{number} never merged",
                detail=(
                    f"'{c.body}' ({c.url}, last updated {c.updated_at.isoformat()}, "
                    f"{age_hours:.1f}h ago) claims #{number} ('{pr.title}') shipped; the "
                    f"PR's real state is '{pr.state}', merged={pr.merged}. GitHub never "
                    f"merges anything off an ordinary timeline comment's own text regardless "
                    f"-- this claim was never going to resolve itself."
                ),
                confidence=confidence,
                evidence=[c.url, pr.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    issue_comments_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    read-only issue/PR-comments tool for a connected account and these two
    loaders are swapped for real calls. The detection logic does not
    change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    comments = load_issue_comments(issue_comments_path)
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
