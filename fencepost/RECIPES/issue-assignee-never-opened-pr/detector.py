"""The seventy-seventh real seam recipe: an issue's own assignee -- GitHub's
structured, private "you specifically are on the hook" field, distinct from
a public label's open call -- who never opened a pull request that actually
closes the issue they were assigned.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before this
one: this module only ever reads two local fixture files (`issues.json`,
`pulls.json`), shaped like what `ListIssues`/`ListPullRequests` would
actually return. Both scopes already sit on SCOPES.md's cleared oath table
-- this recipe asks Arcade for nothing new; it is only the first to read
`issues[].assignees` and `pulls[].author` together in one detector.

The seam: `good-first-issue-never-referenced` (task 499) already proved a
label field can name an unanswered public invitation, checked against
WHETHER any PR ever referenced the issue at all -- pure existence, no
identity. `merged-pr-requested-reviewer-never-reviewed` (task 597) already
proved a structured person-field can be checked for identity, but entirely
inside one pull request's own record (`requested_reviewers` vs its own
`review_comments`' authors). Neither reads `assignees`, and neither asks
whether the SAME PERSON GitHub asked is the one who actually showed up.
`assignees` is a genuinely untouched field across every one of the
seventy-six recipes before this one -- confirmed by grep, not assumed.
This recipe crosses those two proven moves: an issue's own `assignees`
list against every pull request's own `author` login, requiring both the
identity match AND a real closing-keyword reference to the specific issue
assigned, not just any PR from that person, and not just any PR closing
that issue.

Deliberately narrow, the same no-grading law every sibling holds: this
recipe never claims the assignee is slow, stuck, or dropped the ball --
assignment tracking on GitHub is famously loose (a maintainer's own
bulk-assign habit, a stale carry-over from a reorg) and a real human may be
working the issue entirely outside a pull request (a discussion, a design
doc, an in-person fix). The gap is narrower and honest: nothing in the
record itself shows the specific person asked ever opened the specific
channel (a PR naming this issue) GitHub's own tooling expects that promise
to travel through.
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
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "issue_assignee_never_opened_pr" / "issues.json"
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "issue_assignee_never_opened_pr" / "pulls.json"

# An assignment younger than this may simply be too fresh to judge --
# ListIssues carries no per-assignee assigned-at timestamp, only the
# issue's own created_at, so that is the honest clock available. Shorter
# than good-first-issue-never-referenced's 168h bar on purpose: a direct,
# private ask of one named person is a faster human cadence than a public
# label waiting for a stranger to even notice it.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Issue:
    number: int
    title: str
    state: str
    assignees: list[str]
    created_at: datetime
    url: str


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    author: str
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
            assignees=list(r.get("assignees", [])),
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
            author=r["author"],
            body=r.get("body") or "",
            url=r["url"],
        )
        for r in rows
    ]


def _issue_numbers_answered_by(login: str, pulls: list[PullRequest]) -> set[int]:
    """Every issue number `login` themself closed via a real closing
    keyword, across every PR they authored -- open, closed, or merged. A
    PR from someone else that happens to close the same issue never
    counts here; identity is the whole point of this recipe."""
    answered: set[int] = set()
    for pr in pulls:
        if pr.author != login:
            continue
        answered.update(closing_keyword_numbers(pr.body))
    return answered


def compute_gaps(
    issues: list[Issue], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. An issue carrying no assignees at all is not this
    recipe's concern at all -- not even named in `excluded`, the same
    "the non-match is the subject's own shape, not a comparison that was
    actually attempted" rule `good-first-issue-never-referenced` already
    holds for an unlabeled issue."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for issue in sorted(issues, key=lambda i: i.number):
        if not issue.assignees:
            continue

        if issue.state != "open":
            excluded.append(GapCandidate(
                slug=f"not-open-{issue.number}",
                headline=f"Issue #{issue.number} ('{issue.title}') already reads closed",
                detail=(
                    f"Issue #{issue.number} is closed. Whatever happened -- an "
                    "assignee's own PR, someone else's, or a fix outside a PR "
                    "entirely -- the working promise has resolved. No seam here."
                ),
                confidence=0.0,
                evidence=[issue.url],
            ))
            continue

        answered_by_assignee = False
        for login in issue.assignees:
            if issue.number in _issue_numbers_answered_by(login, pulls):
                answered_by_assignee = True
                break

        if answered_by_assignee:
            excluded.append(GapCandidate(
                slug=f"answered-by-assignee-{issue.number}",
                headline=f"Issue #{issue.number} ('{issue.title}') was answered by its own assignee",
                detail=(
                    f"At least one of issue #{issue.number}'s named assignees "
                    "opened a pull request naming it via a real closing keyword. "
                    "The specific person asked is the one who showed up -- no "
                    "seam here."
                ),
                confidence=0.0,
                evidence=[issue.url],
            ))
            continue

        age_hours = (now - issue.created_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
        assignee_list = ", ".join(issue.assignees)
        surfaced.append(GapCandidate(
            slug=f"issue-assignee-never-opened-pr-{issue.number}",
            headline=(
                f"Issue #{issue.number} ('{issue.title}') is assigned to "
                f"{assignee_list}, none of them has ever opened a pull request "
                "closing it"
            ),
            detail=(
                f"Issue #{issue.number} ('{issue.title}') has been open for "
                f"{age_hours:.1f}h with assignee(s) {assignee_list} on record "
                "(created " + issue.created_at.isoformat() + "). No pull request "
                "authored by any of them names this issue via a real GitHub "
                "closing keyword ('closes #N'/'fixes #N'/'resolves #N', either "
                "tense) -- someone else may have tried, or no one has, but the "
                "specific person GitHub says is on the hook has not opened the "
                "channel their own assignment expects. Nothing in the API ever "
                "flags this; only holding the assignee list and the PR author "
                "list at once shows it."
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
