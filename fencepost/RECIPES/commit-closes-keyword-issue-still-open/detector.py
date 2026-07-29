"""Eighth real seam recipe: a commit already on the repository's default
branch names a GitHub closing keyword for an issue that is still open.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before this
one: this module only ever reads two local fixture files (`commits.json`,
`issues.json`), shaped like what `ListRepoCommits`/`ListIssues` would
return. Both scopes already sit on SCOPES.md's cleared oath table -- this
recipe asks Arcade for nothing new.

The seam: `merged-pr-issue-still-open` and `issue-closed-pr-still-open`
both watch a PULL REQUEST's own closing-keyword promise. But GitHub's
auto-close trigger does not require a PR at all -- a closing keyword
(`closes #N` / `fixes #N` / `resolves #N`, present OR past tense) fires the
moment a commit carrying it lands on the repository's DEFAULT branch,
whether that commit arrived via a merged PR or a direct push. This town's
own operating model is mostly the second shape: gods commit straight to
`main` (`git -c user.name="<God>" ...`), not through PRs -- exactly the
workflow neither PR-based recipe was ever built to watch. `ListRepoCommits`
already returns default-branch history (the same assumption `scan.py`'s own
`fetch_github_activity` and `dangling-issue-reference`'s detector both
already make about the same tool), so every commit this recipe sees is one
whose closing keyword, if it has one, really did have a live trigger.
When the named issue is STILL open well after that commit landed, the
keyword's promise silently never fired -- a broken close nobody is
watching for, because nothing about a commit message gets a second look
once it's pushed (`dangling-issue-reference`'s own docstring makes the
identical point about a different failure mode of the same fact).

This recipe deliberately reuses `tools/closing_keyword_guard.py`'s own
grammar shape (`close[sd]?|fix(?:e[sd])?|resolve[sd]?`, both tenses) rather
than `merged-pr-issue-still-open`'s narrower `closes?|fixes?|resolves?`
(present tense only) -- that module already proved, live, on this repo's
own history (task 184: issues #1 and #2 closed themselves on a past-tense
"closed #1"/"fixes #2" push), that GitHub's real commit-message parser
accepts past tense too. `CLOSING_KEYWORD_RE` is imported from
`seam_engine.closing_keywords` (task 394), not retyped locally -- this
recipe's own first version defined its own copy, with a comment promising
to "mirror" the tools/ grammar, and two later recipes retyped a third and
fourth copy of the identical pattern with the identical unenforced
promise. `seam_engine.closing_keywords` is now the one real source all
three import from, closing the drift risk this docstring's own comment
used to only assert.

A commit naming a closing keyword for an issue number that does not exist
in this fixture's issue set at all is excluded, not surfaced -- that is
`dangling-issue-reference`'s seam (a broken link), not this one's (a
promise that should have fired but the target already existed). A commit
using a present-participle phrasing ("closing #N") never matches at all --
Iron Rule #8's own prescribed safe form, proven here to actually be safe,
not just recommended.

Confidence is age-gated on how long the commit carrying the promise has
sat on the default branch while the named issue stays open -- see
`recipe.json`'s `confidence_notes` for the full reasoning behind the 24h
bar.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "commit_closes_keyword_issue_still_open"
DEFAULT_COMMITS_FIXTURE = _FIXTURE_DIR / "commits.json"
DEFAULT_ISSUES_FIXTURE = _FIXTURE_DIR / "issues.json"

# A promise under this age may not have had time to auto-close yet, or
# nobody has re-checked -- not yet a gap.
_STALE_HOURS = 24.0


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
            closed_at=_parse_ts(r["closed_at"]) if r.get("closed_at") else None,
            url=r["url"],
        )
        for r in rows
    ]


def _closing_refs(message: str) -> list[int]:
    """Every issue number a real GitHub closing keyword names in `message`,
    de-duplicated, first-seen order -- same contract as
    `closing_keyword_guard.find_closing_refs`."""
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
    `compute_gaps`. One candidate per (commit, referenced issue) pair: a
    commit naming several closing keywords for several different issues
    makes its own separate promise to each, and each is checked on its own
    merits. A referenced issue that is closed, or that does not exist in
    this fixture's issue set at all, is excluded and named, not silently
    dropped -- a nonexistent target is `dangling-issue-reference`'s seam,
    not this recipe's own."""
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
                        f"'{commit.message}' promises to close #{number}, but no such issue exists. "
                        "A broken link, not a broken promise -- dangling-issue-reference's seam, not this one's."
                    ),
                    confidence=0.0,
                    evidence=[commit.url],
                ))
                continue

            if issue.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"already-closed-{commit.sha}-{number}",
                    headline=f"Commit {commit.sha}'s promise to close #{number} already held",
                    detail=f"'{commit.message}' names #{number}, which is already closed. Working as intended.",
                    confidence=0.0,
                    evidence=[commit.url, issue.url],
                ))
                continue

            age_hours = (now - commit.ts).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"commit-closes-keyword-issue-still-open-{commit.sha}-{number}",
                headline=f"Commit {commit.sha} promised to close #{number}; it's still open",
                detail=(
                    f"'{commit.message}' ({commit.url}) landed on the default branch "
                    f"{commit.ts.isoformat()} ({age_hours:.1f}h before this scan) naming a real "
                    f"GitHub closing keyword for #{number} ('{issue.title}'). The issue still reads open."
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
