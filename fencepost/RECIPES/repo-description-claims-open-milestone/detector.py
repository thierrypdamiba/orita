"""The hundred-ninth real seam recipe: the repository's own one-line
description names a "milestone #N shipped" claim phrase, but the named
milestone is still open.

The fourth leg opened on this surface, alongside `repo-description-
dangling-reference` (task 916, the tenth leg of the dangling-reference
family), `repo-description-claims-unfixed-issue` (task 1405, the
hundred-seventh recipe) and `repo-description-claims-dangling-milestone`
(task 1406, the hundred-eighth). The milestone-side twin of
`repo-description-claims-unfixed-issue`, applied to the sibling
`claims-open-milestone` shape instead: not "does milestone #N exist at
all" (that is `repo-description-claims-dangling-milestone`'s own seam)
but "the description claims milestone #N SHIPPED, and it has not."
Thirteen other permanent public text surfaces already carry this exact
leg -- `readme-claims-open-milestone`, `release-claims-open-milestone`,
`tweet-claims-open-milestone`, `milestone-claims-open-milestone`,
`issue-body-claims-open-milestone`, `issue-comment-claims-open-milestone`,
`review-comment-claims-open-milestone`, `mention-claims-open-milestone`,
`slack-message-claims-open-milestone`, `linear-comment-claims-open-
milestone`, `email-claims-open-milestone`, `calendar-event-claims-open-
milestone`, `commit-claims-open-milestone` -- but the repo description
had never been checked for this claim shape. Confirmed live before
writing this file: grepped every `claims-open-milestone`-suffixed slug
under `RECIPES/` -- thirteen existing entries, none `repo-description-`,
a genuine one-leg gap, and the last of the two legs (alongside
`claims-unmerged-pr`) this surface is still missing from the full
five-leg set every other surface in the family carries.

Deliberately reuses `seam_engine.milestone_claims.claimed_milestone_
numbers` verbatim -- the same shared grammar `repo-description-claims-
dangling-milestone` already imports from there -- rather than a
fourteenth independently retyped copy of the identical pattern.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`repository.json`,
`milestones.json`), shaped like what a read-only `GetRepository` and
`ListMilestones` call would actually return. Both scopes already sit on
`SCOPES.md`'s cleared oath table under the `github` row -- this recipe
asks Arcade for nothing new.

The seam: a "milestone #N" claim phrase inside the repository's own
description names a milestone by number. If that milestone does not
exist at all, it is excluded here -- a broken reference is
`repo-description-claims-dangling-milestone`'s own seam, not this one's.
If it exists and is closed, the claim was simply true -- excluded, named
not hidden. If it exists and is still open, the description permanently
visible in search results and above the repo's own README disagrees with
the milestone tracker's real state: that is the gap.

Confidence is deliberately NOT age-gated, the same reasoning
`repo-description-claims-unfixed-issue`'s own docstring already gave for
this exact same field: a `GetRepository` call returns the description
CURRENT right now, not a change history, so there is no per-claim "when
was this written" timestamp to weigh a staleness window against. There is
also no race to guard against here: the description is read live, right
now, so a claim it currently makes and the milestone's currently-open
state are both true at the same instant the scan runs. A flat 0.85 on
every surfaced claim is the honest confidence for an unambiguous,
non-fuzzy, same-instant contradiction -- the same number `repo-
description-claims-unfixed-issue` already uses for the identical
live-read reasoning on this surface (`repo-description-claims-dangling-
milestone`'s own 0.8 is a different case: a broken reference, not a
same-instant state contradiction). A repository carrying no description
at all (GitHub allows this) is excluded outright, named not hidden --
there is no claim to have broken.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "repo_description_claims_open_milestone"
DEFAULT_REPOSITORY_FIXTURE = _FIXTURE_DIR / "repository.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# Flat confidence for a surfaced claim -- see module docstring for why no
# age-gate applies here, the same reasoning repo-description-claims-
# unfixed-issue already gave for this exact same live-read field.
_SURFACED_CONFIDENCE = 0.85


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    url: str


def _load_rows(path: Path) -> list[Any]:
    """Refuses a syntactically valid but non-list payload with a named
    error, the same guard every sibling detector's own `_load_rows`
    holds."""
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_description(path: Path | None = None) -> str | None:
    """Load the whole-file `{"full_name": ..., "description": ..., "url":
    ...}` shape a `GetRepository` call returns, refusing a syntactically
    valid but wrong-shaped payload with a named error -- same discipline
    every sibling `repo-description-*` recipe's own `load_description`
    already holds. `description` may be JSON `null` (a real, common
    GitHub value for a minimal repo) -- returned as `None`, not coerced
    into an empty string, so the caller can exclude it explicitly rather
    than silently treating it as claim-free."""
    p = path or DEFAULT_REPOSITORY_FIXTURE
    data = json.loads(p.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{p}: expected a JSON object, got {type(data).__name__}")
    if "description" not in data:
        raise ValueError(f"{p}: expected a 'description' field")
    description = data["description"]
    if description is not None and not isinstance(description, str):
        raise ValueError(f"{p}: expected 'description' to be a string or null")
    return description


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
    description: str | None, milestones: list[Milestone]
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A `None` description is excluded
    outright -- there is no claim to have broken. Otherwise, a claimed
    milestone is excluded, named not hidden, the moment it names no real
    milestone at all, or the milestone it names is already closed --
    everything left over (a shipped-it claim the milestone tracker itself
    contradicts) is surfaced at a flat confidence (see module docstring
    for why no age-gate applies)."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    if description is None:
        excluded.append(GapCandidate(
            slug="no-description",
            headline="This repository carries no description",
            detail="GetRepository's own description field reads null. No seam here.",
            confidence=0.0,
            evidence=[],
        ))
        return surfaced, excluded

    numbers = _claimed_milestone_numbers(description)
    if not numbers:
        excluded.append(GapCandidate(
            slug="no-claim-phrase-repo-description",
            headline="The repo description names no milestone claim",
            detail="The repository's own description carries no 'milestone #N' claim phrase. No seam here.",
            confidence=0.0,
            evidence=[],
        ))
        return surfaced, excluded

    seen: set[int] = set()
    for number in numbers:
        if number in seen:
            continue
        seen.add(number)

        milestone = _find_milestone(number, milestones)
        if milestone is None:
            excluded.append(GapCandidate(
                slug=f"claimed-milestone-not-found-repo-description-{number}",
                headline=f"The repo description claims milestone #{number}, which doesn't exist",
                detail=f"The repository description claims milestone #{number} shipped, but no "
                       f"such milestone exists here. No seam here (see repo-description-claims-dangling-milestone).",
                confidence=0.0,
                evidence=[],
            ))
            continue

        if milestone.state == "closed":
            excluded.append(GapCandidate(
                slug=f"claim-true-repo-description-{number}",
                headline=f"The repo description's claim about milestone #{number} holds",
                detail=f"The repository description claims milestone #{number} ('{milestone.title}') "
                       f"shipped; the milestone is closed. No seam here.",
                confidence=0.0,
                evidence=[milestone.url],
            ))
            continue

        surfaced.append(GapCandidate(
            slug=f"repo-description-claims-open-milestone-{number}",
            headline=f"The repo description claims milestone #{number} shipped, but it's still open",
            detail=(
                f"The repository's own description claims milestone #{number} "
                f"('{milestone.title}') shipped; the milestone's real state is "
                f"'{milestone.state}'."
            ),
            confidence=_SURFACED_CONFIDENCE,
            evidence=[milestone.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    repository_path: Path | None = None,
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `GetRepository`/`ListMilestones` read for a connected account and
    these two loaders are swapped for real calls. The detection logic
    does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    description = load_description(repository_path)
    milestones = load_milestones(milestones_path)
    surfaced, excluded = compute_gaps(description, milestones)
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
