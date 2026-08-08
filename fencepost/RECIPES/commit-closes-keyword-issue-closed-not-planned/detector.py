"""The sixty-second real seam recipe: a commit's own closing keyword
credited itself with fixing an issue that closed for an unrelated reason.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before this
one: this module only ever reads two local fixture files (`commits.json`,
`issues.json`), shaped like what `ListRepoCommits`/`ListIssues` would
return. Both scopes already sit on SCOPES.md's cleared oath table -- the
identical pair `commit-closes-keyword-issue-still-open` already uses -- this
recipe asks Arcade for nothing new.

The seam: `commit-closes-keyword-issue-still-open` (the eighth real recipe)
watches a commit's closing keyword ("fixes/closes/resolves #N") against an
issue that is STILL OPEN -- the promise never fired at all. This recipe
watches the opposite mechanical branch, one none of the sixty-one recipes
shipped before it ever reads: the named issue really did close, so a naive
check ("is #N closed yet?") would call the promise kept and move on. But a
real GitHub issue carries a second field alongside `state` that no recipe in
this repository has ever looked at -- `state_reason`, one of `"completed"`,
`"not_planned"`, or `null`. An issue can read `state=closed` for a reason
that has nothing to do with anyone's fix landing: a maintainer declines it,
marks it a duplicate, or closes it as out of scope, and GitHub records that
choice as `state_reason="not_planned"`, not `"completed"`. When a commit's
own permanent message says "fixes #N" and #N's own record shows it closed
`not_planned`, the commit's claim is false in exactly the way that matters
-- nobody fixed anything -- even though every check this repo has shipped
so far, which only ever asks "open or closed," would read it as a promise
kept and never look twice. The commit message cannot be edited once pushed
(the same immutability `own-tweet-dangling-reference`'s docstring already
leans on for a different surface), so the false credit sits in the
repository's own permanent history indefinitely, with nothing on GitHub's
side that would ever flag the mismatch -- closing an issue as `not_planned`
does not touch, retract, or annotate any commit that once named it.

This is a genuinely different axis from the family `test_recipe_ordinal_
doctrine.py`'s own history already calls saturated (the claims-X grid, 7
sources x 3 claim types = 21/21) and from the dangling-reference family (9
legs, all reading whether a `#N` target EXISTS). Neither of those eighteen
siblings, nor `commit-closes-keyword-issue-still-open`/`-pr-still-open`,
nor either `*-claims-unfixed-issue` leg, ever reads `state_reason` --
every one of them treats `state == "closed"` as sufficient proof a claim
resolved. This recipe's surfaced set and `commit-closes-keyword-issue-
still-open`'s surfaced set are provably disjoint: that recipe only ever
fires when `issue.state == "open"`; this one only ever fires when
`issue.state == "closed" and issue.state_reason == "not_planned"`. The
same commit/issue pair can never appear in both recipes' output at once.

Reuses `seam_engine.closing_keywords.CLOSING_KEYWORD_RE` verbatim rather
than a tenth independently typed copy of the same grammar -- the identical
discipline every sibling in this family already holds itself to.

A referenced issue number that does not exist in this fixture's issue set
at all is excluded as a dangling reference -- `dangling-issue-reference`'s
own seam, not this one's. A referenced issue that is still open is
excluded too -- `commit-closes-keyword-issue-still-open`'s own seam, not
this one's; this recipe never re-litigates that branch. A closed issue
with `state_reason="completed"` is excluded as the ordinary, unremarkable
case -- the promise actually held. A closed issue with no `state_reason`
at all (a legacy record, or one this fixture simply never populated) is
excluded as unproven, not guessed into either bucket -- the same "malformed
is not evidence" discipline `unblocked-issue-still-open`'s own
`blocker-closed-no-timestamp` branch already holds for a missing
timestamp, applied here to a missing reason instead. A closed issue with
some OTHER, unrecognized `state_reason` value is excluded and named
separately again, rather than folded into either "completed" or
"not_planned" by assumption.

Confidence is age-gated on how long the issue has sat closed `not_planned`
while the commit's own message still credits it -- see `recipe.json`'s
`confidence_notes` for the full reasoning behind reusing this family's
common 24-hour bar rather than inventing a new number.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.closing_keywords import CLOSING_KEYWORD_RE
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "commit_closes_keyword_issue_closed_not_planned"
DEFAULT_COMMITS_FIXTURE = _FIXTURE_DIR / "commits.json"
DEFAULT_ISSUES_FIXTURE = _FIXTURE_DIR / "issues.json"

# A mismatch under this age may not have been noticed yet -- not yet a gap.
# Matches commit-closes-keyword-issue-still-open's and every sibling
# *-still-open/complete recipe's own 24-hour bar rather than inventing a
# new number for a structurally similar family.
_STALE_HOURS = 24.0

# The only `state_reason` value that means the closing keyword's own claim
# actually held.
_COMPLETED = "completed"
_NOT_PLANNED = "not_planned"


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Commit:
    sha: str
    message: str
    url: str
    ts: datetime
    author: str


@dataclass
class Issue:
    number: int
    title: str
    state: str
    state_reason: str | None
    closed_at: datetime | None
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_commits(path: Path | None = None) -> list[Commit]:
    rows = _load_rows(path or DEFAULT_COMMITS_FIXTURE)
    return [
        Commit(sha=r["sha"], message=r["message"], url=r["url"], ts=_parse_ts(r["ts"]), author=r["author"])
        for r in rows
    ]


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [
        Issue(
            number=r["number"], title=r["title"], state=r["state"],
            state_reason=r.get("state_reason"),
            closed_at=_parse_ts(r["closed_at"]) if r.get("closed_at") else None,
            url=r["url"],
        )
        for r in rows
    ]


def _closing_refs(message: str) -> list[int]:
    """Every issue number a real GitHub closing keyword names in `message`,
    de-duplicated, first-seen order -- same contract as
    `commit-closes-keyword-issue-still-open`'s own `_closing_refs`."""
    seen: list[int] = []
    for m in CLOSING_KEYWORD_RE.finditer(message):
        n = int(m.group(1))
        if n not in seen:
            seen.append(n)
    return seen


def _find_issue(number: int, issues: list[Issue]) -> Issue | None:
    for issue in issues:
        if issue.number == number:
            return issue
    return None


def compute_gaps(
    commits: list[Commit], issues: list[Issue], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. One candidate per (commit, referenced issue) pair, the
    identical per-pair contract `commit-closes-keyword-issue-still-open`
    already established: a commit naming several closing keywords for
    several different issues makes its own separate promise to each, and
    each is judged on its own merits. Every branch below is named, not
    silently folded into another -- a dangling target, a still-open
    target, an honestly-completed target, a target with no recorded
    reason, and a target with an unrecognized reason are five different
    facts about the world, and only the last-but-one -- closed
    `not_planned` -- is this recipe's own seam."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for commit in commits:
        refs = _closing_refs(commit.message)
        if not refs:
            excluded.append(GapCandidate(
                slug=f"no-closing-keyword-{commit.sha}",
                headline=f"Commit {commit.sha} names no closing keyword",
                detail=f"'{commit.message}' carries no close/fix/resolve #N promise. No seam here.",
                confidence=0.0,
                evidence=[commit.url],
            ))
            continue

        for number in refs:
            issue = _find_issue(number, issues)
            if issue is None:
                excluded.append(GapCandidate(
                    slug=f"nonexistent-target-{commit.sha}-{number}",
                    headline=f"Commit {commit.sha} names #{number}, which does not exist in this repo",
                    detail=(
                        f"'{commit.message}' credits #{number}, but no such issue exists. "
                        "A broken link, not a broken promise -- dangling-issue-reference's seam, not this one's."
                    ),
                    confidence=0.0,
                    evidence=[commit.url],
                ))
                continue

            if issue.state != "closed":
                excluded.append(GapCandidate(
                    slug=f"still-open-{commit.sha}-{number}",
                    headline=f"Commit {commit.sha}'s target #{number} is still open",
                    detail=(
                        f"'{commit.message}' names #{number}, which has not closed at all -- "
                        "commit-closes-keyword-issue-still-open's own seam, not this one's."
                    ),
                    confidence=0.0,
                    evidence=[commit.url, issue.url],
                ))
                continue

            if issue.state_reason == _COMPLETED:
                excluded.append(GapCandidate(
                    slug=f"closed-as-completed-{commit.sha}-{number}",
                    headline=f"Commit {commit.sha}'s claim on #{number} held -- closed as completed",
                    detail=f"'{commit.message}' names #{number}, which closed with state_reason=completed. Working as intended.",
                    confidence=0.0,
                    evidence=[commit.url, issue.url],
                ))
                continue

            if issue.state_reason is None:
                excluded.append(GapCandidate(
                    slug=f"state-reason-missing-{commit.sha}-{number}",
                    headline=f"Commit {commit.sha}'s target #{number} closed with no recorded reason",
                    detail=(
                        f"'{commit.message}' names #{number}, which reads closed but carries no "
                        "state_reason at all -- unproven, not guessed into either bucket."
                    ),
                    confidence=0.0,
                    evidence=[commit.url, issue.url],
                ))
                continue

            if issue.state_reason != _NOT_PLANNED:
                excluded.append(GapCandidate(
                    slug=f"state-reason-unrecognized-{commit.sha}-{number}",
                    headline=f"Commit {commit.sha}'s target #{number} closed with an unrecognized reason",
                    detail=(
                        f"'{commit.message}' names #{number}, which closed with "
                        f"state_reason={issue.state_reason!r} -- neither completed nor not_planned. "
                        "Not guessed into either bucket."
                    ),
                    confidence=0.0,
                    evidence=[commit.url, issue.url],
                ))
                continue

            if issue.closed_at is None:
                excluded.append(GapCandidate(
                    slug=f"no-closed-timestamp-{commit.sha}-{number}",
                    headline=f"Commit {commit.sha}'s target #{number} closed not_planned with no timestamp",
                    detail=(
                        f"'{commit.message}' names #{number}, which reads closed not_planned but "
                        "carries no close timestamp -- a malformed record, not an unresolved seam."
                    ),
                    confidence=0.0,
                    evidence=[commit.url, issue.url],
                ))
                continue

            age_hours = (now - issue.closed_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"commit-closes-keyword-issue-closed-not-planned-{commit.sha}-{number}",
                headline=f"Commit {commit.sha} credited itself with fixing #{number}, which closed not_planned",
                detail=(
                    f"'{commit.message}' ({commit.url}) names a real GitHub closing keyword for "
                    f"#{number} ('{issue.title}'), but that issue closed "
                    f"{issue.closed_at.isoformat()} ({age_hours:.1f}h before this scan) with "
                    "state_reason=not_planned, not completed. The commit's own claim of a fix "
                    "does not match the issue's own record of why it closed."
                ),
                confidence=confidence,
                evidence=[commit.url, issue.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    commits_path: Path | None = None,
    issues_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListRepoCommits` read and this one loader is swapped for a real read.
    The detection logic does not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    commits = load_commits(commits_path)
    issues = load_issues(issues_path)
    surfaced, excluded = compute_gaps(commits, issues, now=now)
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
