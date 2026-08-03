"""Thirty-seventh real seam recipe: README.md itself names a real
"ships/includes/merges/via #N" claim about a pull request, but the named
PR never actually merged.

The PR-side twin of `readme-claims-open-milestone` (task 491, a
`milestone #N` claim) and `readme-claims-unfixed-issue` (task 492, a
closing-keyword claim) -- README's own `claims-X` family had a milestone
leg and an issue leg but no PR leg, unlike both siblings in the wider
`claims-*` family, which each carry all three: `release-claims-open-
milestone` + `release-claims-unfixed-issue` + `release-claims-unmerged-pr`,
and `tweet-claims-open-milestone` + `tweet-claims-unfixed-issue` +
`tweet-claims-unmerged-pr`. This recipe closes the last missing leg for
README the same way `release-claims-unmerged-pr` and `tweet-claims-
unmerged-pr` closed it for a release body and a tweet: the identical
ships/includes/merges/via #N grammar, checked against a third permanent
public record.

Deliberately reuses `seam_engine.pr_claims.claimed_pr_numbers` verbatim --
the same shared grammar `release-claims-unmerged-pr`, `merged-pr-never-
released`, and `tweet-claims-unmerged-pr` already import from there --
rather than a fourth independently typed copy of the identical pattern
drifting apart from the other three.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`readme.json`,
`pulls.json`), shaped like what a read-only `GetFileContents` call on
this repo's own README and `ListPullRequests` would actually return. Both
scopes already sit on `SCOPES.md`'s cleared oath table -- this recipe
asks Arcade for nothing new.

The seam: a ships/includes/merges/via #N claim phrase inside README.md
names a PR by number. If that PR does not exist at all, it is excluded
here -- a broken reference is `dangling-issue-reference`'s own seam, not
this one's. If it exists and is merged, the claim was simply true --
excluded, named not hidden. If it exists and is NOT merged (still open,
or closed without merging), README's own permanent public record
disagrees with reality: that is the gap.

Confidence is deliberately NOT age-gated, the same reasoning `readme-
claims-open-milestone`'s and `readme-claims-unfixed-issue`'s own
docstrings already gave for their own README reads: a `GetFileContents`
call returns README's CURRENT text, not a change history, so there is no
per-claim "when was this line written" timestamp to weigh a staleness
window against -- unlike `release-claims-unmerged-pr` and `tweet-claims-
unmerged-pr`, which each age a claim against their own record's publish
time. There is also no race to guard against here: a README is read
live, right now, so a claim it currently makes and the PR's currently-
unmerged state are both true at the same instant the scan runs. A flat
0.85 on every surfaced claim is the honest confidence for an unambiguous,
non-fuzzy, same-instant contradiction -- no staleness window to weigh it
against.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "readme_claims_unmerged_pr"
DEFAULT_README_FIXTURE = _FIXTURE_DIR / "readme.json"
DEFAULT_PULLS_FIXTURE = _FIXTURE_DIR / "pulls.json"

# Flat confidence for a surfaced claim -- see module docstring for why no
# age-gate applies here, the same reasoning readme-claims-open-milestone
# and readme-claims-unfixed-issue already gave for their own README reads.
_SURFACED_CONFIDENCE = 0.85


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    merged: bool
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
    `readme-claims-open-milestone`'s and `readme-claims-unfixed-issue`'s
    own `load_readme`."""
    p = path or DEFAULT_README_FIXTURE
    data = json.loads(p.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{p}: expected a JSON object, got {type(data).__name__}")
    content = data.get("content")
    if not isinstance(content, str):
        raise ValueError(f"{p}: expected a string 'content' field")
    return content


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
    readme_content: str, pulls: list[PullRequest]
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed PR is excluded, named not hidden, the
    moment it names no real PR at all, or the PR it names is already
    merged -- everything left over (a ships/includes/merges/via claim the
    PR tracker itself contradicts) is surfaced at a flat confidence (see
    module docstring for why no age-gate applies)."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    numbers = _claimed_pr_numbers(readme_content)
    if not numbers:
        excluded.append(GapCandidate(
            slug="no-claim-phrase-readme",
            headline="README.md names no ships/includes/merges/via PR claim",
            detail="README.md carries no PR claim-phrase reference. No seam here.",
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
                slug=f"claimed-pr-not-found-readme-{number}",
                headline=f"README.md claims #{number} shipped, which doesn't exist",
                detail=f"README.md claims #{number} shipped, but no such PR exists. No seam here (see dangling-issue-reference).",
                confidence=0.0,
                evidence=[],
            ))
            continue

        if pr.merged:
            excluded.append(GapCandidate(
                slug=f"claim-true-readme-{number}",
                headline=f"README.md's claim about #{number} holds",
                detail=f"README.md claims #{number} ('{pr.title}') shipped; the PR is merged. No seam here.",
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        surfaced.append(GapCandidate(
            slug=f"readme-claims-unmerged-pr-{number}",
            headline=f"README.md claims #{number} shipped, but #{number} never merged",
            detail=(
                f"README.md claims #{number} ('{pr.title}') shipped; "
                f"the PR's real state is '{pr.state}', merged={pr.merged}."
            ),
            confidence=_SURFACED_CONFIDENCE,
            evidence=[pr.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    readme_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest
    WIP marker this recipe carries until the Hand's gateway carries a
    live `GetFileContents` read and these two loaders are swapped for
    real calls. The detection logic does not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    readme_content = load_readme(readme_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(readme_content, pulls)
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
