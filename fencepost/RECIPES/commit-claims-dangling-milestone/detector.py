"""The seventy-sixth real seam recipe: a commit's own message claims a
milestone ("milestone #N"), but no milestone with that number exists at
all.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads two local fixture files
(`commits.json`, `milestones.json`), shaped like what `ListRepoCommits`
and `ListMilestones` would actually return. Both scopes already sit on
SCOPES.md's cleared oath table under the `github` row -- this recipe asks
Arcade for nothing new.

`RECIPES/commit-claims-open-milestone/` (task 596, the sixty-sixth real
recipe) was the first to pair `ListRepoCommits` with `ListMilestones`, and
its own docstring drew the line precisely: a claimed milestone number that
names no real milestone at all is excluded there, named not hidden, "as
belonging to a future milestone-side dangling-reference recipe, not this
one." This recipe is that seam, on the one surface that named it: a
commit message is GitHub's own `#N` shorthand rendered as a clickable
link regardless of what number space it is meant to name, and nothing on
GitHub's side ever checks a claimed `milestone #N` phrase against the
real milestone tracker before rendering the link. `commit-claims-open-
milestone` already proved the "milestone #N" grammar reads cleanly off a
commit message; this recipe reads the same grammar for the orthogonal
question -- not "is it still open" but "does it exist at all."

This is not `dangling-issue-reference`'s own seam (the fourth real
recipe, task 368) wearing a new name. That recipe watches a bare `#N` --
GitHub's shared issue/PR number sequence -- and never once opens
`ListMilestones`; a milestone lives in its own, separate number space
that issues and pull requests never touch, so a `#N` that resolves
cleanly as an issue could still be a dangling MILESTONE claim, and a
`#N` that is a real milestone could just as easily collide with a real
issue number. Confusing the two spaces would be exactly the false-positive
failure Ogun's law calls fatal -- so this recipe reads `claimed_milestone_
numbers`'s own "milestone #N" phrase grammar (`seam_engine.milestone_
claims`, the same shared grammar eleven prior recipes already import,
`commit-claims-open-milestone` among them), never the bare-`#N` grammar
`dangling-issue-reference` and its own nine-legged family already own.
Nor is it `milestone-body-dangling-reference`'s seam (task 585, "the
fifth and final leg of the dangling-reference family") -- that recipe
reads a real milestone's own `description` field for a dangling
issue/PR reference, the exact reverse direction of the claim this recipe
reads: a commit claiming a milestone number, not a milestone's own body
claiming an issue number.

The claim stays narrow, the same no-grading law every sibling holds: a
commit that merely mentions a bare `#N` in passing ("see #47 for
context") makes no milestone claim at all, and is excluded, not guessed
into either bucket -- that bare shape is `dangling-issue-reference`'s own
seam, not this one's, the identical boundary `commit-claims-open-
milestone` already draws for itself. A claimed milestone number that DOES
resolve to a real milestone is excluded too, named not hidden, regardless
of whether that milestone is open or closed -- whether the claim is TRUE
is `commit-claims-open-milestone`'s own seam, not this one's; this recipe
only ever asks whether the name resolves to anything at all.

Confidence is flat, not age-gated, mirroring `dangling-issue-reference`'s
own reasoning rather than `commit-claims-open-milestone`'s 24-hour bar: a
milestone that does not exist right now will not spontaneously come into
existence later just because more time passes, so there is no "give it a
day, it might just be a race" grace period that means anything here --
unlike an OPEN milestone, which could close at any moment. A commit
message is also permanent the instant it is pushed, never revised the way
a release body, a tweet, or a comment can still be edited. See `dangling-
issue-reference/recipe.json`'s own `confidence_notes` for the identical
reasoning this recipe borrows rather than re-deriving.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "commit_claims_dangling_milestone"
DEFAULT_COMMITS_FIXTURE = _FIXTURE_DIR / "commits.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# Flat, not age-gated -- see the module docstring. Mirrors
# dangling-issue-reference's own _DANGLING_CONFIDENCE exactly (0.8): a
# commit message never gets a second chance to fix its own claim, and a
# nonexistent milestone number will not spontaneously start existing.
_DANGLING_CONFIDENCE = 0.8


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
class Commit:
    sha: str
    message: str
    url: str
    ts: datetime
    author: str


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    url: str


def load_commits(path: Path | None = None) -> list[Commit]:
    rows = _load_rows(path or DEFAULT_COMMITS_FIXTURE)
    return [
        Commit(
            sha=r["sha"], message=r["message"], url=r["url"],
            ts=_parse_ts(r["ts"]), author=r.get("author", "unknown"),
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
    commits: list[Commit], milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claim is excluded, named not hidden, the moment a
    commit makes no 'milestone #N' claim at all, or the milestone it names
    IS real (open or closed, this recipe does not care which) -- everything
    left over (a claimed milestone number with no real milestone behind it
    at all) is surfaced at a flat confidence.

    `now` is accepted, unused -- kept for interface parity with every
    other recipe's own `compute_gaps(..., now=...)` shape (`run_recipe_
    scan` always threads one through), the identical "unused today, kept
    for the shape" choice `dangling-issue-reference/detector.py` already
    makes and explains for the identical reason: this recipe's confidence
    is flat, not age-gated, so there is nothing here for `now` to weigh
    against."""
    del now  # unused today; kept for interface parity, see docstring above.
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for commit in sorted(commits, key=lambda c: c.sha):
        numbers = _claimed_milestone_numbers(commit.message)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{commit.sha}",
                headline=f"Commit {commit.sha} names no milestone claim",
                detail=(
                    f"'{commit.message}' ({commit.url}) carries no 'milestone #N' claim "
                    "phrase. No seam here."
                ),
                confidence=0.0,
                evidence=[commit.url],
            ))
            continue

        # dict.fromkeys dedupes, order-preserving: a commit message naming
        # the same milestone twice must not produce two identical
        # GapCandidates, the same guard commit-claims-open-milestone
        # already holds.
        for number in dict.fromkeys(numbers):
            milestone = _find_milestone(number, milestones)
            if milestone is not None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-exists-{commit.sha}-{number}",
                    headline=f"Commit {commit.sha}'s claimed milestone #{number} is real",
                    detail=(
                        f"'{commit.message}' ({commit.url}) claims milestone #{number} "
                        f"('{milestone.title}', state '{milestone.state}'); the milestone "
                        "exists. Whether the claim itself is TRUE is a different recipe's "
                        "seam (commit-claims-open-milestone), not this one's. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[commit.url, milestone.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"commit-claims-dangling-milestone-{commit.sha}-{number}",
                headline=f"Commit {commit.sha} claims milestone #{number}, which doesn't exist",
                detail=(
                    f"'{commit.message}' ({commit.url}) claims milestone #{number}, but no "
                    "milestone with that number exists at all. GitHub renders the number as a "
                    "clickable link regardless; nothing on GitHub's side ever checks a "
                    "'milestone #N' claim phrase against the real milestone tracker."
                ),
                confidence=_DANGLING_CONFIDENCE,
                evidence=[commit.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    commits_path: Path | None = None,
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListRepoCommits`/`ListMilestones` read and these two loaders are
    swapped for real reads. The detection logic does not change when that
    happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    commits = load_commits(commits_path)
    milestones = load_milestones(milestones_path)
    surfaced, excluded = compute_gaps(commits, milestones, now=now)
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
