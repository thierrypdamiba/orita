"""The eighty-second real seam recipe: a pull request's own inline code
review comment invokes a real "milestone #N" claim phrase, but no
milestone with that number exists at all.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files
(`review_comments.json`, `milestones.json`), shaped like what
`ListReviewCommentsInARepository` and `ListMilestones` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table
(`ListReviewCommentsInARepository` live since `review-comment-dangling-
reference`, the forty-fourth real recipe; `ListMilestones` used by every
`*-claims-open-milestone` sibling) -- this recipe asks Arcade for
nothing new.

`review-comment-claims-open-milestone` (task 588, the fifty-sixth real
recipe) was the first to pair a review comment with `ListMilestones`, and
its own docstring drew the line precisely: a claimed milestone number
that names no real milestone at all is excluded there, named not hidden
-- "that broken reference belongs to a dangling-reference recipe's own
seam (over issues/PRs), not this one's (over milestones; no
review-comment-side milestone-dangling-reference recipe exists yet
either -- a genuinely separate future seam)." This recipe is that seam,
on the one surface that named it -- the review-comment-sourced sibling of
`commit-claims-dangling-milestone` (task 649, the seventy-sixth real
recipe) and `issue-comment-claims-dangling-milestone` (task 865, the
eighty-first), which closed the identical seam for a commit message and
an issue/PR timeline comment respectively. Deliberately reuses
`seam_engine.milestone_claims.claimed_milestone_numbers` verbatim -- the
same shared grammar both those recipes already import -- rather than a
ninth independently retyped copy of the identical pattern.

Not `review-comment-dangling-reference`'s seam wearing a new name: that
recipe (task 502, the forty-fourth real recipe) watches a bare `#N`
inside a review comment against BOTH the issue list and the PR list --
GitHub's shared issue/PR number sequence -- and never once opens
`ListMilestones`. A milestone lives in its own, separate number space
that issues and pull requests never touch, so a `#N` that resolves
cleanly as an issue could still be a dangling MILESTONE claim, and a
`#N` that is a real milestone could just as easily collide with a real
issue number. Confusing the two spaces would be exactly the false-
positive failure Ogun's law calls fatal -- so this recipe reads
`claimed_milestone_numbers`'s own "milestone #N" phrase grammar, never
the bare-`#N` grammar `review-comment-dangling-reference` already owns.

The claim stays narrow, the same no-grading law every sibling holds: a
review comment that merely mentions a bare `#N` in passing ("same root
cause as #501") makes no milestone claim at all, and is excluded, not
guessed into either bucket -- that bare shape is `review-comment-
dangling-reference`'s own seam, not this one's. A claimed milestone
number that DOES resolve to a real milestone is excluded too, named not
hidden, regardless of whether that milestone is open or closed --
whether the claim is TRUE is `review-comment-claims-open-milestone`'s
own seam, not this one's; this recipe only ever asks whether the name
resolves to anything at all. A review comment with no body at all is
never examined, the identical "not a claim at all" exclusion every
sibling claims-X recipe already makes for a body-free comment.

Confidence is flat (0.8), not age-gated -- mirrors `commit-claims-
dangling-milestone`'s and `issue-comment-claims-dangling-milestone`'s own
reasoning rather than `review-comment-claims-open-milestone`'s 24-hour
edit-grace bar. That bar exists because an OPEN milestone could close at
any moment, so a fresh claim about it might just be a race the comment
hasn't caught up to yet; a milestone number that does not exist right now
will not spontaneously start existing later no matter how long the
comment sits, so there is no grace period that means anything here. This
holds even though a review comment (like an issue/PR comment) stays
editable forever: the editability of the SURFACE has no bearing on
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "review_comment_claims_dangling_milestone"
DEFAULT_REVIEW_COMMENTS_FIXTURE = _FIXTURE_DIR / "review_comments.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# Flat, not age-gated -- see the module docstring. Mirrors
# commit-claims-dangling-milestone's and issue-comment-claims-dangling-
# milestone's own _DANGLING_CONFIDENCE exactly (0.8): a nonexistent
# milestone number will not spontaneously start existing, whatever the
# age or editability of the surface naming it.
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


def compute_gaps(
    comments: list[ReviewComment], milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A review comment with no body at all is never
    examined at all -- it claims nothing, so there is no seam to weigh. A
    comment naming no 'milestone #N' claim phrase is excluded, named not
    hidden. A claimed milestone is excluded, named not hidden, the moment
    it names a real milestone (open or closed, this recipe does not care
    which) -- everything left over (a claimed milestone number with no
    real milestone behind it at all) is surfaced at a flat confidence.

    `now` is accepted, unused -- kept for interface parity with every
    other recipe's own `compute_gaps(..., now=...)` shape (`run_recipe_
    scan` always threads one through), the identical "unused today, kept
    for the shape" choice `commit-claims-dangling-milestone/detector.py`
    and `issue-comment-claims-dangling-milestone/detector.py` already make
    and explain for the identical reason: this recipe's confidence is
    flat, not age-gated, so there is nothing here for `now` to weigh
    against."""
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
                headline=f"Review comment #{c.id} (on PR #{c.pull_request_number}) names no milestone claim",
                detail=f"'{c.body}' ({c.url}) carries no 'milestone #N' claim phrase. No seam here.",
                confidence=0.0,
                evidence=[c.url],
            ))
            continue

        # dict.fromkeys dedupes, order-preserving: a comment naming the
        # same #N twice must not produce two identical GapCandidates that
        # tie each other out of rank()'s SEPARATION_MARGIN, the same guard
        # issue-comment-claims-dangling-milestone and commit-claims-
        # dangling-milestone already hold.
        for number in dict.fromkeys(numbers):
            milestone = _find_milestone(number, milestones)
            if milestone is not None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-exists-{c.id}-{number}",
                    headline=f"Review comment #{c.id}'s claimed milestone #{number} is real",
                    detail=(
                        f"'{c.body}' ({c.url}) claims milestone #{number} "
                        f"('{milestone.title}', state '{milestone.state}'); the milestone "
                        "exists. Whether the claim itself is TRUE is a different recipe's "
                        "seam (review-comment-claims-open-milestone), not this one's. "
                        "No seam here."
                    ),
                    confidence=0.0,
                    evidence=[c.url, milestone.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"review-comment-claims-dangling-milestone-{c.id}-{number}",
                headline=f"Review comment #{c.id} (on PR #{c.pull_request_number}) claims milestone #{number}, which doesn't exist",
                detail=(
                    f"'{c.body}' ({c.url}) claims milestone #{number}, but no "
                    "milestone with that number exists at all. GitHub renders the number as a "
                    "clickable link regardless; nothing on GitHub's side ever checks a "
                    "'milestone #N' claim phrase against the real milestone tracker."
                ),
                confidence=_DANGLING_CONFIDENCE,
                evidence=[c.url],
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
