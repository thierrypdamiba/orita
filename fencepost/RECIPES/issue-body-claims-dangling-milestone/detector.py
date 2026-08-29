"""The ninety-fifth real seam recipe: an issue or pull request's own OPENING
BODY names a "milestone #N" claim phrase, but no milestone with that number
exists at all.

The one surface the claims-dangling-milestone family had never grown a leg
for. `commit-claims-dangling-milestone`, `issue-comment-claims-dangling-
milestone`, `review-comment-claims-dangling-milestone`, `mention-claims-
dangling-milestone`, `milestone-claims-dangling-milestone`, `readme-claims-
dangling-milestone`, `release-claims-dangling-milestone`, `tweet-claims-
dangling-milestone`, `slack-message-claims-dangling-milestone`, and
`linear-comment-claims-dangling-milestone` all already check the identical
claim grammar against ten other text surfaces for a nonexistent milestone
number -- but none of them ever reads an issue or pull request's own
OPENING BODY, the exact surface `issue-body-dangling-reference` (the
twenty-fourth real recipe) and `issue-body-claims-open-milestone` (the
ninety-second) already established loaders for. `issue-body-claims-open-
milestone`'s own docstring drew this line precisely: a claimed milestone
number that names no real milestone at all is excluded there, named not
hidden, "issue-body-dangling-reference's own seam, not this one's" -- but
that recipe only ever watches a bare `#N` against GitHub's shared issue/PR
number sequence and never opens `ListMilestones` at all, so it was never
actually built for a `milestone #N` claim phrase either. This recipe is
the genuinely separate future seam both of those docstrings pointed at and
neither one closed -- the issue/PR-body-sourced sibling of `commit-claims-
dangling-milestone` (task 649, the seventy-sixth real recipe), which
closed the identical seam for a commit message.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`issues.json`,
`pulls.json`, the identical shape `issue-body-dangling-reference` and
`issue-body-claims-open-milestone` already established for this exact
surface) plus `milestones.json`, shaped like what `ListIssues`,
`ListPullRequests`, and `ListMilestones` would actually return. All three
scopes already sit on `SCOPES.md`'s cleared oath table -- this recipe asks
Arcade for nothing new; `source: "fixture"` in `run_recipe_scan`'s own
output is the honest MOCK ONLY marker CONTRIBUTING.md requires of every
recipe on the day it merges, not a claim the underlying scopes are
unavailable.

Deliberately reuses `seam_engine.milestone_claims.claimed_milestone_numbers`
verbatim -- the same shared grammar every other `*-claims-*-milestone`
sibling already imports from there -- and the exact `Issue`/`PullRequest`/
`Milestone` dataclass shape and `load_issues`/`load_pulls`/`load_milestones`
loaders `issue-body-claims-open-milestone` already established for this
surface, rather than a second, independently drifting copy of the same
three loaders.

The claim stays narrow, the same no-grading law every sibling holds: a
body that merely mentions a bare `#N` in passing ("see #5 for context")
makes no milestone claim at all, and is never examined -- that bare shape
is `issue-body-dangling-reference`'s own seam, not this one's. A claimed
milestone number that DOES resolve to a real milestone is excluded too,
named not hidden, regardless of whether that milestone is open or closed
-- whether the claim itself is TRUE is `issue-body-claims-open-milestone`'s
own seam, not this one's; this recipe only ever asks whether the name
resolves to anything at all. A body with no text at all is never
examined either, the identical "not a claim at all" exclusion every
sibling text-surface recipe already makes for a body-free record.

Confidence is flat (0.8), not age-gated -- mirrors `commit-claims-
dangling-milestone`'s and every other `*-claims-dangling-milestone`
sibling's own reasoning rather than `issue-body-claims-open-milestone`'s
24-hour edit-grace bar: a milestone number that does not exist right now
will not spontaneously start existing later no matter how long the body
sits, so there is no grace period that means anything here. This holds
even though an issue or PR body, like a timeline comment, stays editable
forever: the editability of the SURFACE has no bearing on whether the
milestone NUMBER it names exists, which is the only thing this recipe
ever asks. Both issues and pull requests are scanned as sources -- either
can claim a nonexistent milestone in its own opening body.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "issue_body_claims_dangling_milestone"
DEFAULT_ISSUES_FIXTURE = _FIXTURE_DIR / "issues.json"
DEFAULT_PULLS_FIXTURE = _FIXTURE_DIR / "pulls.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# Flat, not age-gated -- see the module docstring. Mirrors every other
# *-claims-dangling-milestone sibling's own _DANGLING_CONFIDENCE exactly
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
class Issue:
    number: int
    title: str
    state: str
    body: str
    updated_at: datetime
    url: str


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    body: str
    updated_at: datetime
    url: str


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    url: str


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [
        Issue(
            number=r["number"], title=r["title"], state=r["state"], body=r.get("body") or "",
            updated_at=_parse_ts(r["updated_at"]), url=r["url"],
        )
        for r in rows
    ]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [
        PullRequest(
            number=r["number"], title=r["title"], state=r["state"], body=r.get("body") or "",
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
    issues: list[Issue], pulls: list[PullRequest], milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling detector's
    own `compute_gaps`. A body with no "milestone #N" claim phrase at all is
    never examined -- it claims nothing about a second record, so there is
    no seam to weigh. Both issues and pull requests are scanned as sources.

    `now` is accepted, unused -- kept for interface parity with every other
    recipe's own `compute_gaps(..., now=...)` shape (`run_recipe_scan`
    always threads one through), the identical "unused today, kept for the
    shape" choice `commit-claims-dangling-milestone`'s and `issue-comment-
    claims-dangling-milestone`'s own detectors already make and explain for
    the identical reason: this recipe's confidence is flat, not age-gated,
    so there is nothing here for `now` to weigh against."""
    del now  # unused today; kept for interface parity, see docstring above.
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    _SOURCE_LABEL = {"issue": "Issue", "pr": "PR"}

    def _scan(source_kind: str, number: int, body: str, url: str) -> None:
        label = _SOURCE_LABEL[source_kind]
        if not body:
            return

        numbers = _claimed_milestone_numbers(body)
        if not numbers:
            return

        # dict.fromkeys dedupes, order-preserving: a body naming the same
        # #N twice must not produce two identical GapCandidates that tie
        # each other out of rank()'s SEPARATION_MARGIN, the same guard
        # every *-claims-dangling-milestone sibling already holds.
        for n in dict.fromkeys(numbers):
            milestone = _find_milestone(n, milestones)
            if milestone is not None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-exists-{source_kind}-{number}-{n}",
                    headline=f"{label} #{number}'s claimed milestone #{n} is real",
                    detail=(
                        f"'{body}' ({url}) claims milestone #{n} ('{milestone.title}', "
                        f"state '{milestone.state}'); the milestone exists. Whether the "
                        "claim itself is TRUE is a different recipe's seam "
                        "(issue-body-claims-open-milestone), not this one's. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[url, milestone.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"issue-body-claims-dangling-milestone-{source_kind}-{number}-{n}",
                headline=f"{label} #{number}'s own body claims milestone #{n}, which doesn't exist",
                detail=(
                    f"'{body}' ({url}) claims milestone #{n}, but no milestone with that "
                    "number exists at all. GitHub renders the number as a clickable link "
                    "regardless; nothing on GitHub's side ever checks a 'milestone #N' claim "
                    "phrase against the real milestone tracker."
                ),
                confidence=_DANGLING_CONFIDENCE,
                evidence=[url],
            ))

    for issue in issues:
        _scan("issue", issue.number, issue.body, issue.url)
    for pull in pulls:
        _scan("pr", pull.number, pull.body, pull.url)

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    issues_path: Path | None = None,
    pulls_path: Path | None = None,
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest
    MOCK ONLY marker CONTRIBUTING.md requires of every recipe on the day
    it merges, not a claim the underlying scopes are unavailable
    (`ListIssues`/`ListPullRequests`/`ListMilestones` are all live,
    cleared tools already)."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    issues = load_issues(issues_path)
    pulls = load_pulls(pulls_path)
    milestones = load_milestones(milestones_path)
    surfaced, excluded = compute_gaps(issues, pulls, milestones, now=now)
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
