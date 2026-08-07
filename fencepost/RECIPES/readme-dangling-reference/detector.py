"""The fifty-seventh real seam recipe: README.md's own text counts on an
issue or pull request that isn't actually there.

Eight recipes already watch this exact seam on eight other text surfaces
-- `dangling-issue-reference` (commit messages, task 368),
`mention-dangling-reference` (X mentions, task 388),
`release-note-dangling-reference` (release notes, task 401),
`issue-body-dangling-reference` (issue/PR bodies, task 402),
`milestone-body-dangling-reference` (milestone descriptions, task 520),
`own-tweet-dangling-reference` (the town's own tweets, task 527),
`review-comment-dangling-reference` (inline review comments, task 534),
and `issue-comment-dangling-reference` (timeline comments, task 581) -- but
none of them ever reads README.md itself, even though README is the one
surface the claims-X family checked from all three angles
(`readme-claims-open-milestone`, `readme-claims-unfixed-issue`,
`readme-claims-unmerged-pr`) before any other source did. Every one of
those three claims-X recipes only ever examines the numbers sitting
inside a milestone/fixes/ships CLAIM PHRASE -- a README can also mention
`#N` in ordinary prose (background, credit, a passing remark) with no
claim phrase anywhere nearby, and nothing before this recipe ever checked
whether THAT number actually exists. README is the repo's own front
door, read first by every stranger who lands here -- exactly the kind of
permanent, public, rarely-reproofread surface `dangling-issue-reference`'s
own docstring first named this blind spot on.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads three local fixture files (`readme.json`,
`issues.json`, `pulls.json`), shaped like what a read-only `GetFileContents`
call on this repo's own README, `ListIssues`, and `ListPullRequests` would
actually return. All three scopes already sit on SCOPES.md's cleared oath
table under the `github` row -- this recipe asks Arcade for nothing new.

The seam: `#N` inside README.md's own text is checked against BOTH the
issue list and the PR list, the same "one shared number sequence"
discipline every sibling dangling-reference recipe already holds itself
to -- checking only one would misfire on a perfectly good reference to a
merged PR. A cross-repo `owner/repo#N` reference is never even extracted
as a candidate -- that names a different repo's own number space on
purpose. This recipe imports `seam_engine.references.referenced_numbers`
rather than writing a ninth copy of the same extraction regex -- the
identical "one law, not a ninth copy of it" discipline this engine has
already paid for on the same shared pattern eight times over.

Confidence is deliberately NOT age-gated, unlike most of this recipe's own
dangling-reference siblings (which weigh a flat score or an edit-grace
window against a timestamped artifact). A `GetFileContents` read of
README.md returns CURRENT text, not a change history -- the identical
absence `readme-claims-open-milestone`'s own docstring already named for
its own README read -- and there is no race to guard against either: a
README is read live, right now, so a claim it currently makes and the
issue/PR tracker's currently-known numbers are both true at the same
instant this scan runs. This recipe mirrors `readme-claims-open-milestone`'s
own flat 0.85 bar exactly, not the dangling-reference family's more common
flat 0.8 -- the higher confidence belongs to the SOURCE surface (a live
README read carries no staleness uncertainty at all), not to the shape of
the check.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.references import referenced_numbers as _referenced_numbers
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "readme_dangling_reference"
DEFAULT_README_FIXTURE = _FIXTURE_DIR / "readme.json"
DEFAULT_ISSUES_FIXTURE = _FIXTURE_DIR / "issues.json"
DEFAULT_PULLS_FIXTURE = _FIXTURE_DIR / "pulls.json"

# Flat, not age-gated -- see module docstring for why this mirrors
# readme-claims-open-milestone's own bar, not the dangling-reference
# family's more common 0.8.
_DANGLING_CONFIDENCE = 0.85


def _load_rows(path: Path) -> list[Any]:
    """Refuses a syntactically valid but non-list payload with a named
    error, the same guard every sibling detector's own `_load_rows` holds."""
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


@dataclass
class Issue:
    number: int
    title: str
    state: str
    url: str


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    url: str


def load_readme(path: Path | None = None) -> str:
    """Load the whole-file `{"path": ..., "content": ...}` shape a
    `GetFileContents` call returns, refusing a syntactically valid but
    wrong-shaped payload with a named error -- same discipline as
    `readme-claims-open-milestone`'s own `load_readme`."""
    p = path or DEFAULT_README_FIXTURE
    data = json.loads(p.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{p}: expected a JSON object, got {type(data).__name__}")
    content = data.get("content")
    if not isinstance(content, str):
        raise ValueError(f"{p}: expected a string 'content' field")
    return content


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [Issue(number=r["number"], title=r["title"], state=r["state"], url=r["url"]) for r in rows]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [PullRequest(number=r["number"], title=r["title"], state=r["state"], url=r["url"]) for r in rows]


def compute_gaps(
    readme_content: str, issues: list[Issue], pulls: list[PullRequest]
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A README with no `#N` reference at all
    is never examined -- it claims nothing about a second record, so there
    is no seam to weigh, the identical "not an invite at all" exclusion
    every dangling-reference sibling already makes."""
    known_numbers = {i.number for i in issues} | {p.number for p in pulls}

    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    # dict.fromkeys dedupes, order-preserving: README naming the same #N
    # twice must not produce two identical GapCandidates that tie each
    # other out of rank()'s SEPARATION_MARGIN, the same fix task 442 made
    # for release-note-dangling-reference's own extraction.
    for n in dict.fromkeys(_referenced_numbers(readme_content)):
        if n in known_numbers:
            excluded.append(GapCandidate(
                slug=f"readme-ref-matched-{n}",
                headline=f"README.md's reference to #{n} matches a real issue or PR",
                detail=f"README.md references #{n}; a real issue or pull request #{n} "
                       f"exists in this repo. No seam here.",
                confidence=0.0,
                evidence=[],
            ))
            continue

        surfaced.append(GapCandidate(
            slug=f"readme-dangling-reference-{n}",
            headline=f"README.md references #{n}, but no issue or PR #{n} exists here",
            detail=f"README.md references #{n}; ListIssues + ListPullRequests found no "
                   f"issue or pull request with that number in this repo. Likely a typo, "
                   f"a reference to something deleted, or a number meant for a different "
                   f"repo, left standing in the repo's own front door.",
            confidence=_DANGLING_CONFIDENCE,
            evidence=[],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    readme_path: Path | None = None,
    issues_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `GetFileContents`/`ListIssues`/`ListPullRequests` read for a connected
    account and these three loaders are swapped for real reads. The
    detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    readme_content = load_readme(readme_path)
    issues = load_issues(issues_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(readme_content, issues, pulls)
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
