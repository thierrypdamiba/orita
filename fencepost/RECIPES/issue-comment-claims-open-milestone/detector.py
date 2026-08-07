"""The fifty-ninth real seam recipe. An issue or pull request's own
ordinary TIMELINE comment (not an inline review comment, not the opening
body) invokes a real "milestone #N" claim phrase, but the named
milestone is not actually closed.

The eighth leg the claims-X family has grown on the issue-comment side.
[`../issue-comment-claims-unfixed-issue/`](../issue-comment-claims-unfixed-issue/)
(the fifty-eighth real recipe) proved an issue or pull request's own
ordinary conversation thread is a genuinely distinct GitHub-native claim
surface worth watching for the issue-side leg; this recipe asks the
identical surface's milestone-side question, the direct sibling of
[`../review-comment-claims-open-milestone/`](../review-comment-claims-open-milestone/)
(the fifty-sixth real recipe), which already proved an inline review
comment could carry the same claim. Between the two, the timeline-comment
surface now covers two of the three claim types (unfixed-issue and
open-milestone); `issue-comment-claims-unmerged-pr` is the one remaining
leg.

**The seam it watches:** an issue or pull request's own ordinary
conversation comment invokes a real "milestone #N" claim phrase against a
milestone number -- "this also ships milestone #6001 while we're in
here", "I think this closes milestone #6003 too" -- but milestone #N is
not actually closed (still open). GitHub gives a milestone no auto-close-
style keyword of its own at all (the same reason
`milestone-closed-never-released/detector.py` invented the `milestone #N`
grammar in the first place) -- so a timeline comment naming a milestone
was never wired to anything on GitHub's side regardless of whether the
milestone ever closes.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`issue_comments.json`,
`milestones.json`), shaped like what a live read of an issue/PR's
ordinary timeline comments and `ListMilestones` would actually return.
`ListMilestones` already sits on `SCOPES.md`'s cleared oath table, used by
every `*-claims-open-milestone` sibling -- but per `SCOPES.md`'s own WIP
note on `issue-comment-dangling-reference`, checked live again this hour
via the identical `tools/gateway_toolset_check.py` search: **no read-only
tool shaped like "list issue/PR comments" is exposed anywhere on the-hand
gateway today.** This recipe's own `recipe.json` declares only the one
scope that IS already cleared (`ListMilestones`) -- it does not invent or
claim a second scope the Oath never swore to.
`seam_engine.recipes.validate_recipe`'s own check 3/3 would refuse that on
sight regardless. `source: "fixture"` in `run_recipe_scan`'s own output
is the honest WIP marker, the identical shape `issue-comment-dangling-
reference`, `issue-comment-claims-unfixed-issue`, and the Gmail/Calendar
note all already carry for a different toolkit or surface: the day a live
tool for ordinary issue/PR comments appears, only the fixture loader
swaps for a real call -- the detection logic does not change one line.

Deliberately reuses `seam_engine.milestone_claims.claimed_milestone_numbers`
verbatim -- the same shared grammar `milestone-closed-never-released`,
`release-claims-open-milestone`, `milestone-closed-not-tweeted`,
`tweet-claims-open-milestone`, `mention-claims-open-milestone`,
`readme-claims-open-milestone`, and `review-comment-claims-open-milestone`
already import from there -- rather than an eighth independently retyped
copy of the identical pattern.

The seam: a "milestone #N" claim phrase inside a timeline comment names a
milestone by number. If that milestone does not exist at all, it is
excluded here, named not hidden -- that broken reference belongs to a
future milestone-side dangling-reference recipe's own seam, not this
one's. If it exists and is closed, the claim was simply true -- excluded,
named not hidden. A comment with no body at all is never examined, the
identical "not a claim at all" exclusion `issue-comment-claims-unfixed-
issue.compute_gaps` already makes for a body-free comment.

Confidence is age-gated off the comment's own `updated_at`, mirroring
`issue-comment-claims-unfixed-issue`'s and `review-comment-claims-open-
milestone`'s own reasoning rather than `tweet-claims-open-milestone`'s /
`mention-claims-open-milestone`'s: an ordinary timeline comment, like a
review comment or an issue/PR body, is a text surface its own author can
still edit at any time, unlike a mention or a tweet, which is posted once
and stands. 0.55 within 24 hours of the comment's own last update (the
claim, or the comment carrying it, may simply not have caught up yet);
0.85 at or past 24 hours (nobody is coming back to fix it). See
`recipe.json`'s `confidence_notes` for the full reasoning.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "issue_comment_claims_open_milestone"
DEFAULT_ISSUE_COMMENTS_FIXTURE = _FIXTURE_DIR / "issue_comments.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# A claim checked within this many hours of the comment's own updated_at
# may simply not have caught up yet -- the same editable-text-surface
# grace window issue-comment-claims-unfixed-issue's own
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
class IssueComment:
    id: int
    issue_number: int
    body: str
    updated_at: datetime
    url: str


@dataclass
class Milestone:
    number: int
    title: str
    state: str
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
    comments: list[IssueComment], milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A comment with no body at all is never examined
    at all -- it claims nothing about a second record, so there is no
    seam to weigh, the identical "not an invite at all" exclusion
    `issue-comment-claims-unfixed-issue.compute_gaps` already makes for a
    body-free comment. A comment naming no "milestone #N" claim phrase is
    excluded, named not hidden. A claimed milestone is excluded, named not
    hidden, the moment it names no real milestone at all, or the
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
                headline=f"Comment #{c.id} (on #{c.issue_number}'s own thread) names no milestone claim",
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
                    headline=f"Comment #{c.id} (on #{c.issue_number}'s own thread) claims milestone #{number}, which doesn't exist",
                    detail=f"'{c.body}' ({c.url}) claims milestone #{number} shipped, but no such milestone exists. "
                           f"No seam here (a broken reference is a dangling-reference recipe's own seam).",
                    confidence=0.0,
                    evidence=[c.url],
                ))
                continue

            if milestone.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{c.id}-{number}",
                    headline=f"Comment #{c.id}'s claim about milestone #{number} holds",
                    detail=f"'{c.body}' ({c.url}) claims milestone #{number} ('{milestone.title}') shipped; "
                           f"the milestone is closed. No seam here.",
                    confidence=0.0,
                    evidence=[c.url, milestone.url],
                ))
                continue

            confidence = _confidence_for(c.updated_at, now=now)
            age_hours = (now - c.updated_at).total_seconds() / 3600.0
            surfaced.append(GapCandidate(
                slug=f"issue-comment-claims-open-milestone-{c.id}-{number}",
                headline=f"Comment #{c.id} (on #{c.issue_number}'s own thread) claims milestone #{number} shipped, but it's still open",
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
    issue_comments_path: Path | None = None,
    milestones_path: Path | None = None,
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
