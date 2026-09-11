"""The hundred-tenth real seam recipe: the repository's own one-line
description names a "ships/includes/merges/via #N" claim about a pull
request, but the named PR never actually merged.

The fifth leg opened on this surface, alongside `repo-description-
dangling-reference` (task 916, the tenth leg of the dangling-reference
family), `repo-description-claims-unfixed-issue` (task 1405, the
hundred-seventh), `repo-description-claims-dangling-milestone` (task
1406, the hundred-eighth), and `repo-description-claims-open-milestone`
(task 1407, the hundred-ninth) -- the last of the two legs that same
task's own docstring flagged as still missing from this surface's full
five-leg set. This one closes it: `repo-description` now carries every
`claims-X` leg the `readme`, `release`, and `tweet` surfaces already
carry.

The PR-side twin of `repo-description-claims-open-milestone` (a
`milestone #N` claim) and `repo-description-claims-unfixed-issue` (a
closing-keyword claim), applied to the sibling `claims-unmerged-pr` shape
`readme-claims-unmerged-pr`, `release-claims-unmerged-pr`, and
`tweet-claims-unmerged-pr` already carry on their own three surfaces.
Confirmed live before writing this file: grepped every `claims-unmerged-
pr`-suffixed slug under `RECIPES/` -- fourteen existing entries, none
`repo-description-`, a genuine one-leg gap.

Deliberately reuses `seam_engine.pr_claims.claimed_pr_numbers` verbatim --
the same shared grammar every other `claims-unmerged-pr` sibling already
imports from there -- rather than a fifteenth independently retyped copy
of the identical pattern. Also reuses `repo-description-claims-open-
milestone`'s own `load_description` shape verbatim (a `GetRepository`
whole-file read, `description` may be JSON `null`) rather than a second,
slightly different copy of that loader drifting apart from its sibling.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`repository.json`,
`pulls.json`), shaped like what a read-only `GetRepository` and
`ListPullRequests` call would actually return. Both scopes already sit on
`SCOPES.md`'s cleared oath table under the `github` row -- this recipe
asks Arcade for nothing new.

The seam: a ships/includes/merges/via #N claim phrase inside the
repository's own description names a PR by number. If that PR does not
exist at all, it is excluded here -- a broken reference is `repo-
description-dangling-reference`'s own seam, not this one's. If it exists
and is merged, the claim was simply true -- excluded, named not hidden.
If it exists and is NOT merged (still open, or closed without merging),
the description permanently visible in search results and above the
repo's own README disagrees with the pull-request tracker's real state:
that is the gap.

Confidence is deliberately NOT age-gated, the same reasoning `repo-
description-claims-open-milestone`'s and `repo-description-claims-
unfixed-issue`'s own docstrings already gave for this exact same field: a
`GetRepository` call returns the description CURRENT right now, not a
change history, so there is no per-claim "when was this written"
timestamp to weigh a staleness window against. There is also no race to
guard against here: the description is read live, right now, so a claim
it currently makes and the PR's currently-unmerged state are both true at
the same instant the scan runs. A flat 0.85 on every surfaced claim is
the honest confidence for an unambiguous, non-fuzzy, same-instant
contradiction -- the same number `repo-description-claims-open-
milestone` and `repo-description-claims-unfixed-issue` both already use
for the identical live-read reasoning on this surface (`repo-description-
claims-dangling-milestone`'s own 0.8 is a different case: a broken
reference, not a same-instant state contradiction). A repository carrying
no description at all (GitHub allows this) is excluded outright, named
not hidden -- there is no claim to have broken.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "repo_description_claims_unmerged_pr"
DEFAULT_REPOSITORY_FIXTURE = _FIXTURE_DIR / "repository.json"
DEFAULT_PULLS_FIXTURE = _FIXTURE_DIR / "pulls.json"

# Flat confidence for a surfaced claim -- see module docstring for why no
# age-gate applies here, the same reasoning repo-description-claims-open-
# milestone and repo-description-claims-unfixed-issue already gave for
# this exact same live-read field.
_SURFACED_CONFIDENCE = 0.85


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
    description: str | None, pulls: list[PullRequest]
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A `None` description is excluded
    outright -- there is no claim to have broken. Otherwise, a claimed PR
    is excluded, named not hidden, the moment it names no real PR at all,
    or the PR it names is already merged -- everything left over (a
    ships/includes/merges/via claim the PR tracker itself contradicts) is
    surfaced at a flat confidence (see module docstring for why no
    age-gate applies)."""
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

    numbers = _claimed_pr_numbers(description)
    if not numbers:
        excluded.append(GapCandidate(
            slug="no-claim-phrase-repo-description",
            headline="The repo description names no ships/includes/merges/via PR claim",
            detail="The repository's own description carries no PR claim-phrase reference. No seam here.",
            confidence=0.0,
            evidence=[],
        ))
        return surfaced, excluded

    seen: set[int] = set()
    for number in numbers:
        if number in seen:
            continue
        seen.add(number)

        pr = _find_pull(number, pulls)
        if pr is None:
            excluded.append(GapCandidate(
                slug=f"claimed-pr-not-found-repo-description-{number}",
                headline=f"The repo description claims #{number} shipped, which doesn't exist",
                detail=f"The repository description claims #{number} shipped, but no "
                       f"such PR exists here. No seam here (see repo-description-dangling-reference).",
                confidence=0.0,
                evidence=[],
            ))
            continue

        if pr.merged:
            excluded.append(GapCandidate(
                slug=f"claim-true-repo-description-{number}",
                headline=f"The repo description's claim about #{number} holds",
                detail=f"The repository description claims #{number} ('{pr.title}') shipped; "
                       f"the PR is merged. No seam here.",
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        surfaced.append(GapCandidate(
            slug=f"repo-description-claims-unmerged-pr-{number}",
            headline=f"The repo description claims #{number} shipped, but #{number} never merged",
            detail=(
                f"The repository's own description claims #{number} ('{pr.title}') shipped; "
                f"the PR's real state is '{pr.state}', merged={pr.merged}."
            ),
            confidence=_SURFACED_CONFIDENCE,
            evidence=[pr.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    repository_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `GetRepository`/`ListPullRequests` read for a connected account and
    these two loaders are swapped for real calls. The detection logic
    does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    description = load_description(repository_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(description, pulls)
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
