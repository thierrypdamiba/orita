"""The eighty-fourth real seam recipe: a Linear issue comment invokes a
real "milestone #N" claim phrase, but no milestone with that number
exists at all.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`comments.json`,
`milestones.json`), shaped like what a real `SearchIssueComments`/
`ListMilestones` read would return. `ListMilestones` already sits on
`SCOPES.md`'s cleared oath table under the `github` row, used by every
milestone-claim recipe already in this engine. `SearchIssueComments` is
the same scope `linear-comment-claims-unfixed-issue` (task 600) and
`linear-comment-claims-open-milestone` (task ~602) already cleared
through `seam_engine.recipes.validate_recipe`'s oath (it matches the
allowed `Search*` prefix and contains none of the forbidden write words)
-- this recipe asks Arcade for nothing new. See `SCOPES.md`'s own WIP
note for the `linear` toolkit: the-hand gateway holds a real, live,
upstream `arcade-linear` connection today, but exposes zero
Linear-capable tools on the live gateway -- the identical "connected
upstream, not wired into the gateway" shape `SCOPES.md`'s Gmail/Calendar
and Slack WIP notes already document for two other toolkits.

`linear-comment-claims-open-milestone` was the first to pair a Linear
issue comment with `ListMilestones`, and its own docstring drew the line
precisely: a claimed milestone number that names no real milestone at
all is excluded there, named not hidden -- "that broken reference
belongs to a future Linear-side dangling-reference recipe, not this
one." This recipe is that seam, on the one surface that named it -- the
Linear-sourced sibling of `commit-claims-dangling-milestone` (task 649,
the seventy-sixth real recipe), `issue-comment-claims-dangling-milestone`
(task 865, the eighty-first), `review-comment-claims-dangling-milestone`
(task 866, the eighty-second), and `slack-message-claims-dangling-
milestone` (task 867, the eighty-third), which closed the identical seam
for a commit message, an issue/PR timeline comment, a pull request's own
inline review comment, and a Slack channel message respectively.
Deliberately reuses `seam_engine.milestone_claims.claimed_milestone_
numbers` verbatim -- the same shared grammar all four of those recipes
already import -- rather than a thirteenth independently retyped copy of
the identical pattern.

Not `linear-comment-dangling-reference`'s seam wearing a new name: that
recipe (task 600's own sibling, the ninth dangling-reference-family leg)
watches a bare same-repo `#N` posted inside a Linear issue comment
against BOTH the issue list and the PR list -- GitHub's shared issue/PR
number sequence -- and never once opens `ListMilestones`. A milestone
lives in its own, separate number space that issues and pull requests
never touch, so a `#N` that resolves cleanly as an issue could still be a
dangling MILESTONE claim, and a `#N` that is a real milestone could just
as easily collide with a real issue number. Confusing the two spaces
would be exactly the false-positive failure Ogun's law calls fatal -- so
this recipe reads `claimed_milestone_numbers`'s own "milestone #N" phrase
grammar, never the bare-`#N` grammar `linear-comment-dangling-reference`
already owns.

The claim stays narrow, the same no-grading law every sibling holds: a
comment that merely mentions a bare `#N` in passing ("blocked on #4105,
unrelated") makes no milestone claim at all, and is excluded, not
guessed into either bucket -- that bare shape is `linear-comment-
dangling-reference`'s own seam, not this one's. A claimed milestone
number that DOES resolve to a real milestone is excluded too, named not
hidden, regardless of whether that milestone is open or closed --
whether the claim is TRUE is `linear-comment-claims-open-milestone`'s
own seam, not this one's; this recipe only ever asks whether the name
resolves to anything at all.

Confidence is flat (0.8), not age-gated -- mirrors `commit-claims-
dangling-milestone`'s, `issue-comment-claims-dangling-milestone`'s,
`review-comment-claims-dangling-milestone`'s, and `slack-message-claims-
dangling-milestone`'s own reasoning rather than `linear-comment-claims-
open-milestone`'s 24-hour edit-grace bar. That bar exists because an
OPEN milestone could close at any moment, so a fresh claim about it
might just be a race the comment hasn't caught up to yet; a milestone
number that does not exist right now will not spontaneously start
existing later no matter how long the comment sits, so there is no grace
period that means anything here.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "linear_comment_claims_dangling_milestone"
DEFAULT_COMMENTS_FIXTURE = _FIXTURE_DIR / "comments.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# Flat, not age-gated -- see the module docstring. Mirrors
# commit-claims-dangling-milestone's/issue-comment-claims-dangling-
# milestone's/review-comment-claims-dangling-milestone's/slack-message-
# claims-dangling-milestone's own _DANGLING_CONFIDENCE exactly (0.8): a
# nonexistent milestone number will not spontaneously start existing,
# whatever the age of the comment naming it.
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
class Comment:
    id: str
    issue_identifier: str
    author: str
    text: str
    created_at: datetime
    url: str


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    url: str


def load_comments(path: Path | None = None) -> list[Comment]:
    rows = _load_rows(path or DEFAULT_COMMENTS_FIXTURE)
    return [
        Comment(
            id=r["id"], issue_identifier=r["issue_identifier"], author=r["author"],
            text=r.get("text") or "",
            created_at=_parse_ts(r["ts"]), url=r["url"],
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
    comments: list[Comment], milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A comment with no text at all is never examined
    at all -- it claims nothing, so there is no seam to weigh. A comment
    naming no 'milestone #N' claim phrase is excluded, named not hidden.
    A claimed milestone is excluded, named not hidden, the moment it
    names a real milestone (open or closed, this recipe does not care
    which) -- everything left over (a claimed milestone number with no
    real milestone behind it at all) is surfaced at a flat confidence.

    `now` is accepted, unused -- kept for interface parity with every
    other recipe's own `compute_gaps(..., now=...)` shape (`run_recipe_
    scan` always threads one through), the identical "unused today, kept
    for the shape" choice `slack-message-claims-dangling-milestone/
    detector.py` already makes and explains for the identical reason:
    this recipe's confidence is flat, not age-gated, so there is nothing
    here for `now` to weigh against."""
    del now  # unused today; kept for interface parity, see docstring above.
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for comment in sorted(comments, key=lambda c: c.id):
        if not comment.text:
            continue

        numbers = _claimed_milestone_numbers(comment.text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{comment.id}",
                headline=f"{comment.issue_identifier}'s comment {comment.id} names no milestone claim",
                detail=f"'{comment.text}' ({comment.url}) carries no 'milestone #N' claim phrase. No seam here.",
                confidence=0.0,
                evidence=[comment.url],
            ))
            continue

        # dict.fromkeys dedupes, order-preserving: a comment naming the
        # same #N twice must not produce two identical GapCandidates that
        # tie each other out of rank()'s SEPARATION_MARGIN, the same
        # guard every dangling-milestone sibling already holds.
        for number in dict.fromkeys(numbers):
            milestone = _find_milestone(number, milestones)
            if milestone is not None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-exists-{comment.id}-{number}",
                    headline=f"{comment.issue_identifier}'s comment {comment.id}'s claimed milestone #{number} is real",
                    detail=(
                        f"'{comment.text}' ({comment.url}) claims milestone #{number} "
                        f"('{milestone.title}', state '{milestone.state}'); the milestone "
                        "exists. Whether the claim itself is TRUE is a different recipe's "
                        "seam (linear-comment-claims-open-milestone), not this one's. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[comment.url, milestone.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"linear-comment-claims-dangling-milestone-{comment.id}-{number}",
                headline=f"{comment.issue_identifier}'s comment {comment.id} claims milestone #{number}, which doesn't exist",
                detail=(
                    f"'{comment.text}' ({comment.url}) claims milestone #{number}, but no "
                    "milestone with that number exists at all. Linear renders the number as "
                    "plain text regardless; nothing on either platform ever checks a "
                    "'milestone #N' claim phrase posted to an issue comment against the "
                    "real milestone tracker."
                ),
                confidence=_DANGLING_CONFIDENCE,
                evidence=[comment.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    comments_path: Path | None = None,
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest
    WIP marker this recipe carries until the-hand's gateway carries a
    live `SearchIssueComments`/`ListMilestones` read for a connected
    Linear workspace and these two loaders are swapped for real calls.
    The detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    comments = load_comments(comments_path)
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
