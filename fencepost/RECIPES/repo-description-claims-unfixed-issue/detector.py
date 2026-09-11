"""The hundred-seventh real seam recipe: the repository's own one-line
description names a real GitHub closing keyword against an issue ("fixes
#N" / "closes #N" / "resolves #N", both tenses), but the named issue is
still open.

The issue-side twin of `repo-description-dangling-reference` (task 916,
the tenth leg of the dangling-reference family), applied to the sibling
`claims-unfixed-issue` shape instead: not "does #N exist at all" but "the
description claims #N is FIXED, and it is not." Every other permanent
public text surface already carries this leg -- `readme-claims-unfixed-
issue`, `release-claims-unfixed-issue`, `tweet-claims-unfixed-issue`,
`milestone-claims-unfixed-issue`, `issue-body-claims-unfixed-issue`,
`issue-comment-claims-unfixed-issue`, `review-comment-claims-unfixed-
issue`, `mention-claims-unfixed-issue`, `slack-message-claims-unfixed-
issue`, `linear-comment-claims-unfixed-issue`, `email-claims-unfixed-
issue`, `calendar-event-claims-unfixed-issue` -- but the repo description,
the one text every visitor sees in search results and on the repo's own
GitHub homepage before README ever loads, had only ever been checked for
a DANGLING reference, never for this different, sibling claim. Confirmed
live before writing this file: grepped every recipe.json's own `slug`
under `RECIPES/` for the `repo-description-` prefix -- exactly one
existing entry, `repo-description-dangling-reference`, a genuine one-leg
gap on a surface every other claims-unfixed-issue sibling already covers
from its own family.

Deliberately reuses `seam_engine.closing_keywords.closing_keyword_numbers`
verbatim -- the same shared grammar every sibling above already imports
from there -- rather than a fourteenth independently-retyped copy of the
identical pattern.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`repository.json`,
`issues.json`), shaped like what a read-only `GetRepository` and
`ListIssues` call would actually return. Both scopes already sit on
`SCOPES.md`'s cleared oath table under the `github` row -- this recipe
asks Arcade for nothing new.

The seam: a real closing-keyword phrase inside the repository's own
description names an issue by number. If that issue does not exist at
all, it is excluded here -- a broken reference is `repo-description-
dangling-reference`'s own seam, not this one's. If it exists and is
closed, the claim was simply true -- excluded, named not hidden. If it
exists and is still open, the description permanently visible in search
results and above the repo's own README disagrees with the issue
tracker's real state: that is the gap. "closing #N" (present participle,
Iron Rule #8's own prescribed safe phrasing) never matches either tense --
proven live, not just claimed.

Confidence is deliberately NOT age-gated, the same reasoning
`repo-description-dangling-reference`'s own docstring already gave for
this exact same field: a `GetRepository` call returns the description
CURRENT right now, not a change history, so there is no per-claim "when
was this written" timestamp to weigh a staleness window against -- unlike
`milestone-claims-unfixed-issue`, which ages a claim against the
milestone's own `updated_at` because a milestone object actually carries
one. There is also no race to guard against here: the description is
read live, right now, so a claim it currently makes and the issue's
currently-open state are both true at the same instant the scan runs. A
flat 0.85 on every surfaced claim is the honest confidence for an
unambiguous, non-fuzzy, same-instant contradiction -- no staleness window
to weigh it against. A repository carrying no description at all (GitHub
allows this; a null field is common on brand-new or minimal repos) is
excluded outright, named not hidden -- there is no claim to have broken.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.closing_keywords import closing_keyword_numbers as _closing_keyword_numbers
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "repo_description_claims_unfixed_issue"
DEFAULT_REPOSITORY_FIXTURE = _FIXTURE_DIR / "repository.json"
DEFAULT_ISSUES_FIXTURE = _FIXTURE_DIR / "issues.json"

# Flat confidence for a surfaced claim -- see module docstring for why no
# age-gate applies here, the same reasoning repo-description-dangling-
# reference already gave for this exact same live-read field.
_SURFACED_CONFIDENCE = 0.85


@dataclass
class Issue:
    number: int
    title: str
    state: str
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_description(path: Path | None = None) -> str | None:
    """Load the whole-file `{"full_name": ..., "description": ..., "url":
    ...}` shape a `GetRepository` call returns, refusing a syntactically
    valid but wrong-shaped payload with a named error -- same discipline
    `repo-description-dangling-reference`'s own `load_description` already
    holds. `description` may be JSON `null` (a real, common GitHub value
    for a minimal repo) -- returned as `None`, not coerced into an empty
    string, so the caller can exclude it explicitly rather than silently
    treating it as claim-free."""
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


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [
        Issue(number=r["number"], title=r["title"], state=r["state"], url=r["url"])
        for r in rows
    ]


def _find_issue(number: int, issues: list[Issue]) -> Issue | None:
    for issue in issues:
        if issue.number == number:
            return issue
    return None


def compute_gaps(
    description: str | None, issues: list[Issue]
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A `None` description is excluded
    outright -- there is no claim to have broken. Otherwise, a claimed
    issue is excluded, named not hidden, the moment it names no real issue
    at all, or the issue it names is already closed -- everything left
    over (a fix-claim the issue tracker itself contradicts) is surfaced at
    a flat confidence (see module docstring for why no age-gate applies)."""
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

    numbers = _closing_keyword_numbers(description)
    if not numbers:
        excluded.append(GapCandidate(
            slug="no-claim-phrase-repo-description",
            headline="The repo description names no fixes/closes/resolves issue claim",
            detail="The repository's own description carries no closing-keyword reference. No seam here.",
            confidence=0.0,
            evidence=[],
        ))
        return surfaced, excluded

    seen: set[int] = set()
    for number in numbers:
        if number in seen:
            continue
        seen.add(number)

        issue = _find_issue(number, issues)
        if issue is None:
            excluded.append(GapCandidate(
                slug=f"claimed-issue-not-found-repo-description-{number}",
                headline=f"The repo description claims fixing #{number}, which doesn't exist",
                detail=f"The repository description claims #{number} fixed, but no such "
                       f"issue exists here. No seam here (see repo-description-dangling-reference).",
                confidence=0.0,
                evidence=[],
            ))
            continue

        if issue.state == "closed":
            excluded.append(GapCandidate(
                slug=f"claim-true-repo-description-{number}",
                headline=f"The repo description's claim about #{number} holds",
                detail=f"The repository description claims #{number} ('{issue.title}') fixed; the issue is closed. No seam here.",
                confidence=0.0,
                evidence=[issue.url],
            ))
            continue

        surfaced.append(GapCandidate(
            slug=f"repo-description-claims-unfixed-issue-{number}",
            headline=f"The repo description claims #{number} fixed, but #{number} is still open",
            detail=(
                f"The repository's own description claims #{number} ('{issue.title}') "
                f"fixed; the issue's real state is '{issue.state}'."
            ),
            confidence=_SURFACED_CONFIDENCE,
            evidence=[issue.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    repository_path: Path | None = None,
    issues_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `GetRepository`/`ListIssues` read for a connected account and these
    two loaders are swapped for real calls. The detection logic does not
    change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    description = load_description(repository_path)
    issues = load_issues(issues_path)
    surfaced, excluded = compute_gaps(description, issues)
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
