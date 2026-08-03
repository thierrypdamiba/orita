"""Thirty-eighth real seam recipe (ROADMAP.md #499): an issue labeled
'good first issue' -- an explicit invitation -- that no pull request has
ever named through a real GitHub closing keyword.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads two local fixture files
(`issues.json`, `pulls.json`), shaped like what `ListIssues`/
`ListPullRequests` would actually return. Both scopes already sit on
SCOPES.md's cleared oath table -- this recipe asks Arcade for nothing new.

The seam: a `good first issue` label is a promise GitHub lets a maintainer
make -- "this one's easy, come help" -- but nothing in the API ever checks
whether the invitation was answered. `ListIssues` alone shows the label;
`ListPullRequests` alone shows what a PR claims to close; only holding
both at once, and asking whether ANY pull request (open, closed, or
merged -- an abandoned attempt still counts as someone noticing) ever
named the issue via a real closing keyword, shows whether the shelf item
was ever actually picked up. This is the mirror question
`stale-branch-no-pr` (task 485) already asks for a branch that never
became a PR at all, aimed instead at the one label whose entire purpose
is to be picked up by a stranger -- and the same real live gap the town's
own issue #7 ("Good first issue: write a seam recipe nobody's built yet")
asks a mortal to close.

Reuses `seam_engine.closing_keywords.closing_keyword_numbers` verbatim --
the same shared grammar `commit-closes-keyword-issue-still-open`,
`issue-closed-never-released`, and `release-claims-unfixed-issue` already
import from there -- rather than a fifth independently retyped copy of the
identical closing-keyword regex.

Confidence is age-gated on how long the labeled issue has sat open with
zero PR reference, not flat -- see `recipe.json`'s `confidence_notes` for
the full reasoning behind the 168-hour (7-day) bar, deliberately longer
than the `*-still-open` family's 24h: this measures whether anyone has
STARTED work, a slower human cadence than whether a promise already made
broke.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.closing_keywords import closing_keyword_numbers
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "good_first_issue_never_referenced" / "issues.json"
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "good_first_issue_never_referenced" / "pulls.json"

# A good-first-issue younger than this may simply not have been found by a
# contributor yet -- not yet a gap. Longer than the *-still-open family's
# 24h bar on purpose: this asks whether anyone has started, a slower human
# cadence than whether an existing promise already broke.
_STALE_HOURS = 168.0

_GOOD_FIRST_ISSUE_LABEL = "good first issue"


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Issue:
    number: int
    title: str
    state: str
    labels: list[str]
    created_at: datetime
    url: str


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    body: str
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [
        Issue(
            number=r["number"],
            title=r["title"],
            state=r["state"],
            labels=list(r.get("labels", [])),
            created_at=_parse_ts(r["created_at"]),
            url=r["url"],
        )
        for r in rows
    ]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [
        PullRequest(
            number=r["number"],
            title=r["title"],
            state=r["state"],
            body=r.get("body") or "",
            url=r["url"],
        )
        for r in rows
    ]


def _is_good_first_issue(issue: Issue) -> bool:
    return any(label.strip().lower() == _GOOD_FIRST_ISSUE_LABEL for label in issue.labels)


def _referenced_issue_numbers(pulls: list[PullRequest]) -> set[int]:
    """Every issue number named via a real closing keyword in ANY pull
    request's own body -- open, closed, or merged. An abandoned or
    rejected attempt still counts as someone having noticed the
    invitation; this recipe asks whether the shelf item was ever picked
    up, not whether picking it up succeeded."""
    referenced: set[int] = set()
    for pr in pulls:
        referenced.update(closing_keyword_numbers(pr.body))
    return referenced


def compute_gaps(
    issues: list[Issue], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. An issue not carrying the 'good first issue' label is
    not this recipe's concern at all -- not even named in `excluded`,
    mirroring `contributor-thanked-not-credited`'s "the non-match is the
    subject's own shape, not a comparison that was actually attempted"
    rule, not `merged-pr-issue-still-open`'s "name every non-match too"
    one, because a differently-labeled issue was never a candidate to
    begin with."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    referenced = _referenced_issue_numbers(pulls)

    for issue in sorted(issues, key=lambda i: i.number):
        if not _is_good_first_issue(issue):
            continue

        if issue.state != "open":
            excluded.append(GapCandidate(
                slug=f"not-open-{issue.number}",
                headline=f"Issue #{issue.number} ('{issue.title}') already reads closed",
                detail=(
                    f"Issue #{issue.number} is closed. Whether a PR claimed it or a "
                    "maintainer closed it by hand, the invitation is resolved -- no "
                    "seam here."
                ),
                confidence=0.0,
                evidence=[issue.url],
            ))
            continue

        if issue.number in referenced:
            excluded.append(GapCandidate(
                slug=f"already-referenced-{issue.number}",
                headline=f"Issue #{issue.number} ('{issue.title}') is already named by a PR",
                detail=(
                    f"Issue #{issue.number} is named via a real closing keyword in at "
                    "least one pull request's own body. The invitation was answered, "
                    "whatever became of that PR -- no seam here."
                ),
                confidence=0.0,
                evidence=[issue.url],
            ))
            continue

        age_hours = (now - issue.created_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"good-first-issue-never-referenced-{issue.number}",
            headline=(
                f"Issue #{issue.number} ('{issue.title}') is labeled 'good first issue', "
                "no pull request has ever named it"
            ),
            detail=(
                f"Issue #{issue.number} ('{issue.title}') has carried the "
                f"'good first issue' label for {age_hours:.1f}h "
                f"(opened {issue.created_at.isoformat()}) and stays open. No pull "
                "request, open, closed, or merged, has ever named it via a real "
                "GitHub closing keyword ('closes #N'/'fixes #N'/'resolves #N', "
                "either tense). GitHub's own label renders the invitation but "
                "checks nothing else about it -- no reminder, no staleness flag, "
                "nothing surfaced anywhere else in the API."
            ),
            confidence=confidence,
            evidence=[issue.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    issues_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListIssues`/`ListPullRequests` read and these two loaders are swapped
    for real calls. The detection logic does not change when that
    happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    issues = load_issues(issues_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(issues, pulls, now=now)
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
