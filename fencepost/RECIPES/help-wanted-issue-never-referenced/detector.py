"""The hundred-fourteenth real seam recipe (ROADMAP.md #2683): an issue
labeled 'help wanted' -- an explicit invitation -- that no pull request has
ever named through a real GitHub closing keyword.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads two local fixture files
(`issues.json`, `pulls.json`), shaped like what `ListIssues`/
`ListPullRequests` would actually return. Both scopes already sit on
SCOPES.md's cleared oath table -- this recipe asks Arcade for nothing new.

The seam, and why it is not a duplicate of `good-first-issue-never-referenced`
(task 499): grepped every one of the 113 existing recipes' own `recipe.json`
`slug` field before writing this one -- the `<source>-claims-*`/
`<source>-dangling-reference` matrix is fully saturated across all 14
content-source types, but GitHub ships TWO standard onboarding labels, and
only one of them (`good first issue`) had a watcher. `help wanted` is the
other half of the same promise -- "come help with this one" -- made on a
differently-scoped shelf item, and nothing in the API checks that
invitation either. This recipe is that twin, built to the identical shape
`good-first-issue-never-referenced` already proved: hold `ListIssues` and
`ListPullRequests` at once, and ask whether ANY pull request (open, closed,
or merged -- an abandoned attempt still counts as someone noticing) ever
named the issue via a real closing keyword.

Reuses `seam_engine.closing_keywords.closing_keyword_numbers` verbatim --
the same shared grammar `good-first-issue-never-referenced`,
`commit-closes-keyword-issue-still-open`, and `release-claims-unfixed-issue`
already import from there -- rather than a retyped copy of the identical
closing-keyword regex.

One deliberate difference from the twin, reasoned not copied: confidence is
age-gated on a 336-hour (14-day) staleness bar, double the sibling's 168h.
`help wanted` is GitHub's own signal that a shelf item is NOT scoped for a
first-time contributor -- it typically wants more context, more digging, or
more time to find the right stranger -- so it is honest to give it longer
before unanswered silence counts as a settled gap rather than reusing the
easier-labeled twin's bar untouched.
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
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "help_wanted_issue_never_referenced" / "issues.json"
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "help_wanted_issue_never_referenced" / "pulls.json"

# A help-wanted issue younger than this may simply not have been found by a
# contributor yet -- not yet a gap. Double good-first-issue-never-referenced's
# own 168h bar on purpose: this label is GitHub's own signal the shelf item
# is NOT beginner-scoped, so it honestly deserves longer before silence
# counts as settled.
_STALE_HOURS = 336.0

_HELP_WANTED_LABEL = "help wanted"


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


def _is_help_wanted(issue: Issue) -> bool:
    return any(label.strip().lower() == _HELP_WANTED_LABEL for label in issue.labels)


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
    `compute_gaps`. An issue not carrying the 'help wanted' label is not
    this recipe's concern at all -- not even named in `excluded`, the same
    "the non-match is the subject's own shape, not a comparison that was
    actually attempted" rule `good-first-issue-never-referenced` already
    set, because a differently-labeled issue was never a candidate to
    begin with."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    referenced = _referenced_issue_numbers(pulls)

    for issue in sorted(issues, key=lambda i: i.number):
        if not _is_help_wanted(issue):
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
            slug=f"help-wanted-issue-never-referenced-{issue.number}",
            headline=(
                f"Issue #{issue.number} ('{issue.title}') is labeled 'help wanted', "
                "no pull request has ever named it"
            ),
            detail=(
                f"Issue #{issue.number} ('{issue.title}') has carried the "
                f"'help wanted' label for {age_hours:.1f}h "
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
