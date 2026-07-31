"""Sixth real seam recipe: a still-open pull request names a GitHub closing
keyword for an issue that has since closed through some other route.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads two local fixture files (`pulls.json`,
`issues.json`), shaped like what `ListPullRequests`/`ListIssues`/`GetIssue`
would return. All three scopes already sit on SCOPES.md's cleared oath
table -- this recipe asks Arcade for nothing new.

The seam: `merged-pr-issue-still-open` (task 108) watches a PR that merged
and PROMISED to close an issue that then didn't. This recipe watches the
mirror case: a PR that is STILL OPEN (never merged, so GitHub's own
auto-close never had a trigger to fire on) names a closing keyword for an
issue that closed anyway, through a route that has nothing to do with this
PR -- a duplicate report, a manual close, a different PR that actually
shipped the fix. The open PR is now orphaned: whatever it set out to do,
the thing it named as its reason already happened without it. Neither the
PR alone nor the issue alone shows this -- only holding both at once does.

Confidence is age-gated on how long the issue has been closed while the PR
still sits open, not flat -- see `recipe.json`'s `confidence_notes` for the
full reasoning behind the 48-hour bar.

ROADMAP.md #430: named as still open by task 429's own closing note, this
module's exclusion branch used to fold "the named issue does not exist at
all" into the same `issue is None or issue.state != "closed"` check as "the
named issue exists and is still open" -- one shared `issue-still-open-...`
slug, and a detail line that claimed "the issue has not closed yet" even
when no such issue was ever found. Split here, the same way task 429 split
the identical conflation in `merged-pr-issue-still-open/detector.py`: a
dangling reference (the number was never real) and a genuinely-still-open
issue are different facts about the world.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "issue_closed_pr_still_open" / "pulls.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "issue_closed_pr_still_open" / "issues.json"

# GitHub's own closing-keyword vocabulary (a subset; the real full list also
# includes "close"/"closed"/"fix"/"fixed"/"resolve"/"resolved" -- these three
# base forms cover every fixture case here, mirroring
# `merged-pr-issue-still-open`'s own declared subset exactly).
_CLOSES_RE = re.compile(r"\b(?:closes?|fix(?:es)?|resolves?)\s+#(\d+)\b", re.IGNORECASE)

# An issue closed under this age may not have been noticed yet by whoever
# has the open PR -- not yet a gap.
_STALE_HOURS = 48.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class OpenPull:
    id: str
    title: str
    number: int
    body: str
    state: str
    opened_at: datetime
    url: str


@dataclass
class Issue:
    number: int
    title: str
    state: str
    closed_at: datetime | None
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_pulls(path: Path | None = None) -> list[OpenPull]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [
        OpenPull(
            id=r["id"], title=r["title"], number=r["number"], body=r["body"],
            state=r.get("state", "open"), opened_at=_parse_ts(r["opened_at"]), url=r["url"],
        )
        for r in rows
    ]


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [
        Issue(
            number=r["number"], title=r["title"], state=r["state"],
            closed_at=_parse_ts(r["closed_at"]) if r.get("closed_at") else None,
            url=r["url"],
        )
        for r in rows
    ]


def _named_issue_numbers(body: str) -> list[int]:
    return [int(n) for n in _CLOSES_RE.findall(body)]


def _find_issue(number: int, issues: list[Issue]) -> Issue | None:
    for issue in issues:
        if issue.number == number:
            return issue
    return None


def compute_gaps(
    pulls: list[OpenPull], issues: list[Issue], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. Only PRs still in the `open` state are considered at
    all (a merged or closed PR is exactly what `merged-pr-issue-still-open`
    already watches, not this recipe's seam). A PR is excluded, named not
    hidden, the moment it names no closing keyword, names an issue that is
    still open (no seam -- the ordinary, unremarkable case), or names an
    issue this fixture doesn't carry at all. Everything left over -- an
    open PR whose named issue already closed some other way -- is surfaced,
    aged into a confidence score `rank()` can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for pr in pulls:
        if pr.state != "open":
            continue

        numbers = _named_issue_numbers(pr.body)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-closing-keyword-{pr.number}",
                headline=f"PR #{pr.number} names no closing keyword",
                detail=f"'{pr.title}' is open with no closes/fixes/resolves reference. No seam here.",
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        for number in numbers:
            issue = _find_issue(number, issues)
            if issue is None:
                excluded.append(GapCandidate(
                    slug=f"nonexistent-target-{pr.number}-{number}",
                    headline=f"PR #{pr.number} names #{number}, which does not exist in this repo",
                    detail=(
                        f"'{pr.title}' names #{number}, but no such issue exists. "
                        "A broken link, not a resolved promise (see dangling-issue-reference)."
                    ),
                    confidence=0.0,
                    evidence=[pr.url],
                ))
                continue

            if issue.state != "closed" or issue.closed_at is None:
                excluded.append(GapCandidate(
                    slug=f"issue-still-open-{pr.number}-{number}",
                    headline=f"PR #{pr.number}'s named issue #{number} is still open",
                    detail=f"'{pr.title}' names #{number}; the issue has not closed yet. No seam here.",
                    confidence=0.0,
                    evidence=[pr.url, issue.url],
                ))
                continue

            age_hours = (now - issue.closed_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"issue-closed-pr-still-open-{pr.number}-{number}",
                headline=f"PR #{pr.number} names #{number}, which already closed without it",
                detail=(
                    f"'{pr.title}' (opened {pr.opened_at.isoformat()}) names #{number} "
                    f"('{issue.title}'), closed {issue.closed_at.isoformat()} "
                    f"({age_hours:.1f}h ago) through some other route. The PR still reads open."
                ),
                confidence=confidence,
                evidence=[pr.url, issue.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    pulls_path: Path | None = None,
    issues_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListPullRequests`/`ListIssues` read and these two loaders are swapped
    for real reads. The detection logic does not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    pulls = load_pulls(pulls_path)
    issues = load_issues(issues_path)
    surfaced, excluded = compute_gaps(pulls, issues, now=now)
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
