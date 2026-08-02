"""Thirty-fifth real seam recipe: README.md itself claims a milestone
shipped ("milestone #N"), but the named milestone is not actually closed.

The third leg of the "claims-open-milestone" family alongside
`release-claims-open-milestone` (task 385, a release's own body) and
`tweet-claims-open-milestone` (a tweet's own text) -- same shape, a
different place the town writes a permanent, public "shipped it" claim.
This time the claim lives in the flagship's own front door: the README a
stranger reads first, the one document every other doctrine check in this
repo already treats as a load-bearing public record (`readme-credited-
not-thanked`, `contributor-thanked-not-credited`).

Deliberately reuses `seam_engine.milestone_claims.claimed_milestone_numbers`
verbatim -- the same shared grammar `release-claims-open-milestone` and
`tweet-claims-open-milestone` already import from there (task 389
centralized what had been two independently retyped copies) -- rather than
a fourth copy of the identical pattern drifting apart from the other three.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`readme.json`,
`milestones.json`), shaped like what a read-only `GetFileContents` call on
this repo's own README and `ListMilestones` would actually return. Both
scopes already sit on `SCOPES.md`'s cleared oath table -- this recipe asks
Arcade for nothing new.

The seam: a `milestone #N` claim phrase inside README.md names a
milestone by number. If that milestone does not exist at all, it is
excluded here -- a broken reference is `dangling-issue-reference`'s own
seam (over issues/PRs), not this one's (over milestones). If it exists and
is closed, the claim was simply true -- excluded, named not hidden. If it
exists and is still open, the README's own permanent public record
disagrees with reality: that is the gap.

Confidence is deliberately NOT age-gated, unlike both siblings in this
family. `release-claims-open-milestone` and `tweet-claims-open-milestone`
each weigh a claim against how long ago the claiming artifact (the release,
the tweet) was itself published, because a claim checked moments after
publication might just be racing the milestone's own close event. A
`GetFileContents` read of README.md carries no equivalent "when was this
line written" timestamp at all -- the same absence `readme-credited-not-
thanked`'s own docstring already named for its own README read (a content
read returns CURRENT text, not a change history). There is also no race to
guard against here: unlike a tweet or a release, which are point-in-time
publications that predate the moment they're checked, a README is being
read live, right now -- if it currently claims a milestone shipped and
that milestone is currently open, both halves of the disagreement are
true at the same instant this scan runs. A flat 0.85 on every surfaced
claim is the honest confidence for an unambiguous, non-fuzzy, same-instant
contradiction -- no staleness window to weigh it against.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "readme_claims_open_milestone"
DEFAULT_README_FIXTURE = _FIXTURE_DIR / "readme.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# Flat confidence for a surfaced claim -- see module docstring for why no
# age-gate applies here, unlike this family's other two members.
_SURFACED_CONFIDENCE = 0.85


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_readme(path: Path | None = None) -> str:
    """Load the whole-file `{"path": ..., "content": ...}` shape a
    `GetFileContents` call returns, refusing a syntactically valid but
    wrong-shaped payload with a named error -- same discipline as
    `readme-credited-not-thanked`'s own `load_readme`."""
    p = path or DEFAULT_README_FIXTURE
    data = json.loads(p.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{p}: expected a JSON object, got {type(data).__name__}")
    content = data.get("content")
    if not isinstance(content, str):
        raise ValueError(f"{p}: expected a string 'content' field")
    return content


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
    readme_content: str, milestones: list[Milestone]
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed milestone is excluded, named not hidden,
    the moment it names no real milestone at all, or the milestone it
    names is already closed -- everything left over (a shipped-it claim
    the milestone tracker itself contradicts) is surfaced at a flat
    confidence (see module docstring for why no age-gate applies)."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    numbers = _claimed_milestone_numbers(readme_content)
    if not numbers:
        excluded.append(GapCandidate(
            slug="no-claim-phrase-readme",
            headline="README.md names no milestone claim",
            detail="README.md carries no 'milestone #N' claim phrase. No seam here.",
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
                slug=f"claimed-milestone-not-found-readme-{number}",
                headline=f"README.md claims milestone #{number}, which doesn't exist",
                detail=f"README.md claims milestone #{number} shipped, but no such milestone exists. No seam here.",
                confidence=0.0,
                evidence=[],
            ))
            continue

        if milestone.state == "closed":
            excluded.append(GapCandidate(
                slug=f"claim-true-readme-{number}",
                headline=f"README.md's claim about milestone #{number} holds",
                detail=f"README.md claims milestone #{number} ('{milestone.title}') shipped; the milestone is closed. No seam here.",
                confidence=0.0,
                evidence=[milestone.url],
            ))
            continue

        surfaced.append(GapCandidate(
            slug=f"readme-claims-open-milestone-{number}",
            headline=f"README.md claims milestone #{number} shipped, but it's still open",
            detail=(
                f"README.md claims milestone #{number} ('{milestone.title}') shipped; "
                f"the milestone's real state is '{milestone.state}'."
            ),
            confidence=_SURFACED_CONFIDENCE,
            evidence=[milestone.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    readme_path: Path | None = None,
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `GetFileContents` read and these two loaders are swapped for real
    calls. The detection logic does not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    readme_content = load_readme(readme_path)
    milestones = load_milestones(milestones_path)
    surfaced, excluded = compute_gaps(readme_content, milestones)
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
