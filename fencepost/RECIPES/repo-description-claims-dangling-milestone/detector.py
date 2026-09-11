"""The hundred-eighth real seam recipe: the repository's own one-line
description names a "milestone #N" that doesn't exist at all.

The milestone-side twin of `repo-description-claims-unfixed-issue` (task
1405, the hundred-seventh recipe) and the third leg opened on this text
surface, alongside `repo-description-dangling-reference` (task 916, the
tenth leg of the dangling-reference family, which reads the description
only against the shared GitHub issue/PR number sequence -- a different
number space from a milestone). Every other permanent public text
surface that carries a `claims-dangling-milestone` sibling already has
thirteen: `commit-claims-dangling-milestone`, `email-claims-dangling-
milestone`, `issue-body-claims-dangling-milestone`, `issue-comment-
claims-dangling-milestone`, `linear-comment-claims-dangling-milestone`,
`mention-claims-dangling-milestone`, `milestone-claims-dangling-
milestone`, `readme-claims-dangling-milestone`, `release-claims-
dangling-milestone`, `review-comment-claims-dangling-milestone`,
`slack-message-claims-dangling-milestone`, `tweet-claims-dangling-
milestone`, and `calendar-event-claims-dangling-milestone` -- but the
repo description, the one text every visitor sees in search results and
on the repo's own GitHub homepage before README ever loads, had never
been checked for this claim shape. Confirmed live before writing this
file: grepped every `claims-dangling-milestone`-suffixed slug under
`RECIPES/` -- thirteen existing entries, none of them `repo-
description-`, a genuine one-leg gap on the same field task 1405's own
docstring already proved was worth opening (`GetRepository`'s
`description`), on the one leg `repo-description-claims-unfixed-issue`
and `repo-description-dangling-reference` between them still left
uncovered.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`repository.json`,
`milestones.json`), shaped like what a read-only `GetRepository` and
`ListMilestones` call would actually return -- the identical two-loader
shape `readme-claims-dangling-milestone` (the eighty-eighth) already
established for this exact leg on a different surface. Both scopes
already sit on `SCOPES.md`'s cleared oath table under the `github` row
-- this recipe asks Arcade for nothing new.

Deliberately reuses `seam_engine.milestone_claims.claimed_milestone_
numbers` verbatim -- the same shared grammar every `claims-dangling-
milestone` sibling already imports, negation check included -- rather
than a fourteenth independently retyped copy of the identical pattern.

The seam: a "milestone #N" claim phrase inside the repository's own
description names a milestone by number. If that milestone exists at
all, it is excluded here -- open or closed, whether the claim about it
is TRUE is a different recipe's remit, not this one's (no such recipe
exists yet for this surface; the same boundary `readme-claims-dangling-
milestone`'s own docstring drew against its own sibling
`readme-claims-open-milestone` applies here in spirit, not as an actual
gap this recipe leaves open on this surface). If it does not exist at
all, the repo description's own permanent, above-the-fold claim is
surfaced. No self-claim exclusion is needed: unlike a milestone's own
description (which can name its own number, the exact case `milestone-
claims-dangling-milestone`'s own docstring guards against), a repo
description carries no milestone number of its own to collapse into.

Confidence is flat (0.8), not age-gated -- mirrors every prior claims-
dangling-milestone sibling's own reasoning exactly, and the same
no-staleness-window reasoning `repo-description-claims-unfixed-issue`'s
own docstring already gave for this exact field: a `GetRepository` call
returns the description CURRENT right now, not a change history, so
there is no per-claim timestamp to weigh an age-gate against, and a
milestone number that does not exist right now will not spontaneously
start existing later, so no grace period would mean anything here
either. A repository carrying no description at all (GitHub allows this)
is excluded outright, named not hidden -- there is no claim to have
broken.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "repo_description_claims_dangling_milestone"
DEFAULT_REPOSITORY_FIXTURE = _FIXTURE_DIR / "repository.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# Flat, not age-gated -- see the module docstring. Mirrors every prior
# claims-dangling-milestone sibling's own _DANGLING_CONFIDENCE exactly
# (0.8).
_DANGLING_CONFIDENCE = 0.8


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
    `repo-description-claims-unfixed-issue`'s own `load_description`
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
    outright -- there is no claim to have broken. A description with no
    "milestone #N" claim phrase at all is named as an exclusion rather
    than returning two silent empties. A claimed number that resolves to
    a real milestone is excluded at 0.0, open or closed alike; everything
    left over (a milestone number the repo description names but the
    tracker has never heard of) is surfaced at a flat confidence (see
    module docstring for why no age-gate applies)."""
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

    for n in dict.fromkeys(numbers):
        target = _find_milestone(n, milestones)
        if target is not None:
            excluded.append(GapCandidate(
                slug=f"claimed-milestone-exists-repo-description-{n}",
                headline=f"The repo description's claimed milestone #{n} is real",
                detail=(
                    f"The repository description claims milestone #{n} "
                    f"('{target.title}', state '{target.state}'); the milestone "
                    "exists. No seam here."
                ),
                confidence=0.0,
                evidence=[target.url],
            ))
            continue

        surfaced.append(GapCandidate(
            slug=f"repo-description-claims-dangling-milestone-{n}",
            headline=f"The repo description claims milestone #{n}, which doesn't exist",
            detail=(
                f"The repository's own description claims milestone #{n}, but "
                "no milestone with that number exists at all. The repo "
                "description is the one text every visitor sees before README "
                "ever loads, and nothing had ever checked its milestone claims "
                "against the real milestone tracker."
            ),
            confidence=_DANGLING_CONFIDENCE,
            evidence=[],
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
