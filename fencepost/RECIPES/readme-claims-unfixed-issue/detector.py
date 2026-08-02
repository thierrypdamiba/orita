"""Thirty-sixth real seam recipe: README.md itself names a real GitHub
closing keyword against an issue ("fixes #N" / "closes #N" / "resolves
#N", both tenses), but the named issue is still open.

The issue-side twin of `readme-claims-open-milestone` (task 491, a
`milestone #N` claim) -- README's own `claims-X` family had a milestone
leg and no issue leg, unlike both siblings in the wider `claims-*`
family, which each carry all three: `release-claims-open-milestone` +
`release-claims-unfixed-issue` (task 382), and `tweet-claims-open-
milestone` + `tweet-claims-unfixed-issue`. This recipe closes that
missing leg for README the same way `release-claims-unfixed-issue`
closed it for a release body: the identical closing-keyword grammar,
checked against a different permanent public record.

Deliberately reuses `seam_engine.closing_keywords.closing_keyword_numbers`
verbatim -- the same shared grammar `commit-closes-keyword-issue-still-
open`, `issue-closed-never-released`, and `release-claims-unfixed-issue`
already import from there (task 394 centralized what had been three
independently retyped copies) -- rather than a fifth copy of the
identical pattern drifting apart from the other four.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`readme.json`,
`issues.json`), shaped like what a read-only `GetFileContents` call on
this repo's own README and `ListIssues` would actually return. Both
scopes already sit on `SCOPES.md`'s cleared oath table -- this recipe
asks Arcade for nothing new.

The seam: a real closing-keyword phrase inside README.md names an issue
by number. If that issue does not exist at all, it is excluded here -- a
broken reference is `dangling-issue-reference`'s own seam, not this
one's. If it exists and is closed, the claim was simply true -- excluded,
named not hidden. If it exists and is still open, README's own permanent
public record disagrees with reality: that is the gap. "closing #N"
(present participle, Iron Rule #8's own prescribed safe phrasing) never
matches either tense -- proven live, not just claimed.

Confidence is deliberately NOT age-gated, the same reasoning
`readme-claims-open-milestone`'s own docstring already gave for its own
README read: a `GetFileContents` call returns README's CURRENT text, not
a change history, so there is no per-claim "when was this line written"
timestamp to weigh a staleness window against -- unlike
`release-claims-unfixed-issue`, which ages a claim against the release's
own publish time. There is also no race to guard against here: a README
is read live, right now, so a claim it currently makes and the issue's
currently-open state are both true at the same instant the scan runs. A
flat 0.85 on every surfaced claim is the honest confidence for an
unambiguous, non-fuzzy, same-instant contradiction -- no staleness window
to weigh it against.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "readme_claims_unfixed_issue"
DEFAULT_README_FIXTURE = _FIXTURE_DIR / "readme.json"
DEFAULT_ISSUES_FIXTURE = _FIXTURE_DIR / "issues.json"

# Flat confidence for a surfaced claim -- see module docstring for why no
# age-gate applies here, the same reasoning readme-claims-open-milestone
# already gave for its own README read.
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
    readme_content: str, issues: list[Issue]
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed issue is excluded, named not hidden,
    the moment it names no real issue at all, or the issue it names is
    already closed -- everything left over (a fix-claim the issue tracker
    itself contradicts) is surfaced at a flat confidence (see module
    docstring for why no age-gate applies)."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    numbers = _closing_keyword_numbers(readme_content)
    if not numbers:
        excluded.append(GapCandidate(
            slug="no-claim-phrase-readme",
            headline="README.md names no fixes/closes/resolves issue claim",
            detail="README.md carries no closing-keyword reference. No seam here.",
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
                slug=f"claimed-issue-not-found-readme-{number}",
                headline=f"README.md claims fixing #{number}, which doesn't exist",
                detail=f"README.md claims #{number} fixed, but no such issue exists. No seam here (see dangling-issue-reference).",
                confidence=0.0,
                evidence=[],
            ))
            continue

        if issue.state == "closed":
            excluded.append(GapCandidate(
                slug=f"claim-true-readme-{number}",
                headline=f"README.md's claim about #{number} holds",
                detail=f"README.md claims #{number} ('{issue.title}') fixed; the issue is closed. No seam here.",
                confidence=0.0,
                evidence=[issue.url],
            ))
            continue

        surfaced.append(GapCandidate(
            slug=f"readme-claims-unfixed-issue-{number}",
            headline=f"README.md claims #{number} fixed, but #{number} is still open",
            detail=(
                f"README.md claims #{number} ('{issue.title}') fixed; "
                f"the issue's real state is '{issue.state}'."
            ),
            confidence=_SURFACED_CONFIDENCE,
            evidence=[issue.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    readme_path: Path | None = None,
    issues_path: Path | None = None,
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
    issues = load_issues(issues_path)
    surfaced, excluded = compute_gaps(readme_content, issues)
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
