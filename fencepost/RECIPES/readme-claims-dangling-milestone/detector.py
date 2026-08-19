"""The eighty-eighth real seam recipe: README.md's own text claims a
"milestone #N" that doesn't exist at all.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads TWO local fixture files (`readme.json`,
`milestones.json`), shaped like what a single `GetFileContents` read of
this repo's own README and a single `ListMilestones` call would actually
return -- the identical two-loader shape `readme-claims-open-milestone`
(the sixty-third real recipe) already established for this surface. Both
scopes already sit on `SCOPES.md`'s cleared oath table under the
`github` row; this recipe asks Arcade for nothing new, and its
`toolkit` stays `github`-only.

`milestone-claims-open-milestone`'s own docstring drew the line for this
whole family: a claimed milestone number that names no real milestone at
all was excluded there, named not hidden -- "a broken reference is
`milestone-body-dangling-reference`'s own seam, not this one's." Task
870 checked that deferral live and found it had never actually been
built for the milestone number space at all: `milestone-body-dangling-
reference` watches a bare `#N` against the shared GitHub issue/PR number
sequence and never opens `ListMilestones`. It named the five sources
still uncovered rather than absorbing them silently -- `mention`,
`milestone`, `readme`, `release`, `tweet` -- and closed the first.
`milestone-claims-dangling-milestone` (task 871) closed the second.
This recipe is the third: the README-sourced sibling of `commit-claims-
dangling-milestone` (task 649, the seventy-sixth), `issue-comment-
claims-dangling-milestone` (task 865, the eighty-first), `review-
comment-claims-dangling-milestone` (task 866, the eighty-second),
`slack-message-claims-dangling-milestone` (task 867, the eighty-third),
`linear-comment-claims-dangling-milestone` (task 868, the eighty-
fourth), `mention-claims-dangling-milestone` (task 870, the eighty-
sixth), and `milestone-claims-dangling-milestone` (task 871, the
eighty-seventh). `release` and `tweet` remain open, correctly, for a
future hour.

The README deserved this door before the others did, and did not get
it. `readme-dangling-reference` (the fifty-seventh) already reads
README.md for a bare `#N` -- but strictly against the shared issue/PR
number sequence, never once opening `ListMilestones`. A milestone lives
in its own, separate number space, so a claimed `milestone #N` that
resolves cleanly as a real ISSUE number would read as perfectly fine to
that recipe while naming no milestone at all; conflating the two number
spaces is exactly the false positive Ògún's law calls fatal. README is
also the one surface where a broken claim costs the most: it is the
repo's own front door, the first thing a stranger reads, and the least
often reproofread.

Deliberately reuses `seam_engine.milestone_claims.claimed_milestone_
numbers` verbatim -- the same shared grammar every `*-claims-dangling-
milestone` sibling already imports, negation check included -- rather
than an eighth independently retyped copy of the identical pattern.

This recipe and `readme-claims-open-milestone` are exact inverses on one
surface, and the boundary between them is the whole point: there, a
claimed number that resolves to no real milestone is EXCLUDED at 0.0 and
a claim contradicted by a still-open milestone is surfaced; here, the
resolution failure is the seam itself and a claimed number that DOES
resolve is excluded at 0.0, regardless of whether that milestone is open
or closed. Whether a real milestone's claim is TRUE is that recipe's
remit, not this one's; this one only ever asks whether the name resolves
to anything at all.

No self-claim exclusion appears here, and its absence is deliberate
rather than an oversight: the milestone-sourced sibling needs one
because a milestone's own description can name its own number, but
README.md carries no milestone number of its own, so there is no second
record for it to collapse into. A README with no `milestone #N` claim
phrase at all produces no surfaced candidate -- there is no claim to
have broken -- and says so as a named exclusion, the same shape
`readme-claims-open-milestone.compute_gaps` already holds for this
surface.

Confidence is flat (0.8), not age-gated -- mirrors every prior claims-
dangling-milestone sibling's own reasoning, and lands in the same place
`readme-claims-open-milestone`'s own docstring reached by a different
road. A `GetFileContents` read returns current text, not a change
history, so there is no per-claim timestamp to weigh a staleness window
against in the first place; and even if there were, a milestone number
that does not exist right now will not spontaneously start existing
later, so no grace period would mean anything here.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "readme_claims_dangling_milestone"
DEFAULT_README_FIXTURE = _FIXTURE_DIR / "readme.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# Flat, not age-gated -- see the module docstring. Mirrors every prior
# claims-dangling-milestone sibling's own _DANGLING_CONFIDENCE exactly
# (0.8): a nonexistent milestone number will not spontaneously start
# existing, whatever the age of the README naming it.
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


def load_readme(path: Path | None = None) -> str:
    """Load the whole-file `{"path": ..., "content": ...}` shape a
    `GetFileContents` call returns, refusing a syntactically valid but
    wrong-shaped payload with a named error -- same discipline as
    `readme-claims-open-milestone`'s own `load_readme`, which this
    recipe shares a surface with."""
    p = path or DEFAULT_README_FIXTURE
    data = json.loads(Path(p).read_text())
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
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A README carrying no `milestone #N`
    claim phrase at all is named as an exclusion rather than returning
    two silent empties, the identical shape `readme-claims-open-
    milestone.compute_gaps` already holds for this surface. A claimed
    number that resolves to a real milestone is excluded at 0.0, open or
    closed alike -- whether that claim is TRUE is `readme-claims-open-
    milestone`'s own seam, this recipe's exact inverse on the same
    surface, not this one's."""
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

    # dict.fromkeys dedupes, order-preserving: a README naming the same
    # "milestone #N" twice must not produce two identical GapCandidates
    # that tie each other out of rank()'s SEPARATION_MARGIN, the same
    # guard every dangling-milestone sibling already holds.
    for n in dict.fromkeys(numbers):
        target = _find_milestone(n, milestones)
        if target is not None:
            excluded.append(GapCandidate(
                slug=f"claimed-milestone-exists-readme-{n}",
                headline=f"README.md's claimed milestone #{n} is real",
                detail=(
                    f"README.md claims milestone #{n} ('{target.title}', state "
                    f"'{target.state}'); the milestone exists. Whether the claim "
                    "itself is TRUE is a different recipe's seam "
                    "(readme-claims-open-milestone), not this one's. No seam here."
                ),
                confidence=0.0,
                evidence=[target.url],
            ))
            continue

        surfaced.append(GapCandidate(
            slug=f"readme-claims-dangling-milestone-{n}",
            headline=f"README.md claims milestone #{n}, which doesn't exist",
            detail=(
                f"README.md claims milestone #{n}, but no milestone with that "
                "number exists at all. Nothing on either platform ever checks a "
                "'milestone #N' claim phrase written into the repo's own front "
                "door against the real milestone tracker -- readme-dangling-"
                "reference reads README.md only against the shared issue/PR "
                "number sequence, which is a different number space."
            ),
            confidence=_DANGLING_CONFIDENCE,
            evidence=[],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    readme_path: Path | None = None,
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest
    WIP marker this recipe carries until the-hand's gateway carries a
    live `GetFileContents` + `ListMilestones` read for a connected
    account and these two loaders are swapped for real calls. The
    detection logic does not change one line when that happens."""
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
