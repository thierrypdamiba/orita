"""The eighty-first real seam recipe: an issue or pull request's own
ordinary TIMELINE comment (not an inline review comment, not the opening
body) invokes a real "milestone #N" claim phrase, but no milestone with
that number exists at all.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`issue_comments.json`,
`milestones.json`), shaped like what a live read of an issue/PR's ordinary
timeline comments and `ListMilestones` would actually return.
`ListMilestones` already sits on `SCOPES.md`'s cleared oath table -- but
per `SCOPES.md`'s own WIP note on `issue-comment-dangling-reference`,
checked live again this hour via `tools/gateway_toolset_check.py`: no
read-only tool shaped like "list issue/PR comments" is exposed anywhere on
the-hand gateway today. This recipe's own `recipe.json` declares only the
one scope that IS already cleared (`ListMilestones`) -- it does not invent
or claim a second scope the Oath never swore to.
`seam_engine.recipes.validate_recipe`'s own check 3/3 would refuse that on
sight regardless. `source: "fixture"` in `run_recipe_scan`'s own output is
the honest WIP marker, the identical shape `issue-comment-dangling-
reference`, `issue-comment-claims-unfixed-issue`, and `issue-comment-
claims-open-milestone` all already carry: the day a live tool for ordinary
issue/PR comments appears, only the fixture loader swaps for a real call
-- the detection logic does not change one line.

`issue-comment-claims-open-milestone` (task 559, the fifty-ninth real
recipe) was the first to pair an issue/PR timeline comment with
`ListMilestones`, and its own docstring drew the line precisely: a claimed
milestone number that names no real milestone at all is excluded there,
named not hidden, "as belonging to a future milestone-side dangling-
reference recipe's own seam, not this one's." This recipe is that seam,
on the one surface that named it -- the issue-comment-sourced sibling of
`commit-claims-dangling-milestone` (task 649, the seventy-sixth real
recipe), which closed the identical seam for a commit message. Deliberately
reuses `seam_engine.milestone_claims.claimed_milestone_numbers` verbatim --
the same shared grammar both those recipes already import -- rather than a
ninth independently retyped copy of the identical pattern.

Not `issue-comment-dangling-reference`'s seam wearing a new name: that
recipe watches a bare `#N` against GitHub's shared issue/PR number
sequence and never opens `ListMilestones` at all. A milestone lives in its
own, separate number space, so a `#N` that resolves cleanly as a real
issue could still be a dangling *milestone* claim, and conflating the two
spaces would misfire exactly the way Ogun's law calls fatal.

The claim stays narrow, the same no-grading law every sibling holds: a
comment that merely mentions a bare `#N` in passing ("see #47 for
context") makes no milestone claim at all, and is excluded, not guessed
into either bucket -- that bare shape is `issue-comment-dangling-
reference`'s own seam, not this one's. A claimed milestone number that
DOES resolve to a real milestone is excluded too, named not hidden,
regardless of whether that milestone is open or closed -- whether the
claim is TRUE is `issue-comment-claims-open-milestone`'s own seam, not
this one's; this recipe only ever asks whether the name resolves to
anything at all. A comment with no body at all is never examined, the
identical "not a claim at all" exclusion every timeline-comment sibling
already makes for a body-free comment.

Confidence is flat (0.8), not age-gated -- mirrors `commit-claims-
dangling-milestone`'s own reasoning rather than `issue-comment-claims-
open-milestone`'s 24-hour edit-grace bar. That bar exists because an OPEN
milestone could close at any moment, so a fresh claim about it might just
be a race the comment hasn't caught up to yet; a milestone number that
does not exist right now will not spontaneously start existing later no
matter how long the comment sits, so there is no grace period that means
anything here. This holds even though a comment (unlike a commit message)
stays editable forever: the editability of the SURFACE has no bearing on
whether the milestone NUMBER it names exists, which is the only thing
this recipe ever asks.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "issue_comment_claims_dangling_milestone"
DEFAULT_ISSUE_COMMENTS_FIXTURE = _FIXTURE_DIR / "issue_comments.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# Flat, not age-gated -- see the module docstring. Mirrors
# commit-claims-dangling-milestone's own _DANGLING_CONFIDENCE exactly
# (0.8): a nonexistent milestone number will not spontaneously start
# existing, whatever the age or editability of the surface naming it.
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


def compute_gaps(
    comments: list[IssueComment], milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A comment with no body at all is never examined at
    all -- it claims nothing, so there is no seam to weigh. A comment
    naming no 'milestone #N' claim phrase is excluded, named not hidden. A
    claimed milestone is excluded, named not hidden, the moment it names a
    real milestone (open or closed, this recipe does not care which) --
    everything left over (a claimed milestone number with no real
    milestone behind it at all) is surfaced at a flat confidence.

    `now` is accepted, unused -- kept for interface parity with every
    other recipe's own `compute_gaps(..., now=...)` shape (`run_recipe_
    scan` always threads one through), the identical "unused today, kept
    for the shape" choice `commit-claims-dangling-milestone/detector.py`
    already makes and explains for the identical reason: this recipe's
    confidence is flat, not age-gated, so there is nothing here for `now`
    to weigh against."""
    del now  # unused today; kept for interface parity, see docstring above.
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
        # tie each other out of rank()'s SEPARATION_MARGIN, the same guard
        # issue-comment-claims-open-milestone and commit-claims-dangling-
        # milestone already hold.
        for number in dict.fromkeys(numbers):
            milestone = _find_milestone(number, milestones)
            if milestone is not None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-exists-{c.id}-{number}",
                    headline=f"Comment #{c.id}'s claimed milestone #{number} is real",
                    detail=(
                        f"'{c.body}' ({c.url}) claims milestone #{number} "
                        f"('{milestone.title}', state '{milestone.state}'); the milestone "
                        "exists. Whether the claim itself is TRUE is a different recipe's "
                        "seam (issue-comment-claims-open-milestone), not this one's. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[c.url, milestone.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"issue-comment-claims-dangling-milestone-{c.id}-{number}",
                headline=f"Comment #{c.id} (on #{c.issue_number}'s own thread) claims milestone #{number}, which doesn't exist",
                detail=(
                    f"'{c.body}' ({c.url}) claims milestone #{number}, but no milestone with "
                    "that number exists at all. GitHub renders the number as a clickable link "
                    "regardless; nothing on GitHub's side ever checks a 'milestone #N' claim "
                    "phrase against the real milestone tracker."
                ),
                confidence=_DANGLING_CONFIDENCE,
                evidence=[c.url],
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
