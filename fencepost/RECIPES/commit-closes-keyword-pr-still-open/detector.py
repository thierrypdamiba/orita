"""Twenty-fifth real seam recipe: a commit already on the repository's
default branch names a GitHub closing keyword for a PULL REQUEST that is
still open (or open-and-unmerged) rather than an issue.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before this
one: this module only ever reads two local fixture files (`commits.json`,
`prs.json`), shaped like what `ListRepoCommits`/`ListPullRequests` would
return. Both scopes already sit on SCOPES.md's cleared oath table -- this
recipe asks Arcade for nothing new.

The seam: `commit-closes-keyword-issue-still-open` (task 388, the eighth
real recipe) proved that a commit's own closing keyword can silently never
fire -- but it explicitly, deliberately, only ever checked the number
against the repo's ISSUE set. GitHub's real auto-close trigger does not
care which record type the named number belongs to: a commit carrying
`closes #N` / `fixes #N` / `resolves #N` (present OR past tense) that
lands on the default branch fires the identical mechanism whether #N
resolves to an issue OR a pull request -- against a PR the same keyword is
GitHub's documented auto-*merge*-adjacent trigger (the PR is expected to
close, merged or not, the moment the referencing commit reaches the
default branch the PR itself targets). That is a second, entirely
unwatched half of the same seam: a commit names a real PR number with a
real closing keyword, and that PR is still sitting open days later,
unmerged, its own promise never having fired -- the exact shape the issue-
side sibling's own docstring named as future work by scoping itself to
issues only ("this recipe explicitly only checks issue numbers").

This recipe is that PR-side twin, built the same way task 400's
`duplicate-pr-still-open` was built as `duplicate-issue-still-open`'s own
twin: same fixture shape (one sibling fixture directory, swap the target
record type), same shared-module import discipline, same test rigor.
`CLOSING_KEYWORD_RE` is imported from `seam_engine.closing_keywords` (task
394) -- the one real source three recipes already bind to -- rather than
retyped a sixth time. `tools/duplicate_regex_check.py` exists precisely to
catch a recipe that promises reuse in its docstring but retypes the
pattern anyway; this recipe imports for real, not just in prose.

A commit naming a closing keyword for a PR number that does not exist in
this fixture's PR set at all is excluded, not surfaced -- a broken link,
not a broken promise, the identical `dangling-issue-reference`-shaped seam
`commit-closes-keyword-issue-still-open` already carves out on its own
side. A commit naming an already-resolved PR -- merged OR closed without
merging -- is excluded too: either way, whatever that PR promised is done
being tracked under that number, the promise held (this mirrors
`duplicate-pr-still-open`'s own `_RESOLVED_STATES` reasoning: a PR that
closed without merging is just as settled, for this purpose, as one that
merged). A commit using the present-participle phrasing ("closing #N")
never matches at all -- Iron Rule #8's own prescribed safe form, proven
safe here on the PR side exactly as it already was on the issue side.

Confidence is age-gated on how long the commit carrying the promise has
sat on the default branch while the named PR stays open -- the identical
0.5-under-24h / 0.85-at-or-past-24h shape `commit-closes-keyword-issue-
still-open` uses, no deviation: the PR's own resolution state (open, not
merged) is exactly as unambiguous a signal as an issue's own `state`
field, and nothing about checking a PR number instead of an issue number
changes how quickly GitHub's real auto-close trigger would have fired or
how long a grace period a human re-checking it deserves. See
`recipe.json`'s `confidence_notes` for the full reasoning.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "commit_closes_keyword_pr_still_open"
DEFAULT_COMMITS_FIXTURE = _FIXTURE_DIR / "commits.json"
DEFAULT_PRS_FIXTURE = _FIXTURE_DIR / "prs.json"

# A promise under this age may not have had time to auto-close/auto-merge
# yet, or nobody has re-checked -- not yet a gap. Matches
# `commit-closes-keyword-issue-still-open`'s own bar exactly.
_STALE_HOURS = 24.0

# A PR counts as "resolved" here whether it merged or was closed without
# merging -- either way, whatever it promised is done being tracked under
# that number, so a commit naming it is orphaned the same way in both
# cases. Matches `duplicate-pr-still-open`'s own `_RESOLVED_STATES`
# reasoning, applied to the same shared issue/PR number space.
_RESOLVED_STATES = ("closed",)


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
class PullRequest:
    number: int
    title: str
    state: str
    merged: bool
    merged_at: datetime | None
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


def load_prs(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PRS_FIXTURE)
    return [
        PullRequest(
            number=r["number"], title=r["title"], state=r["state"], merged=r["merged"],
            merged_at=_parse_ts(r["merged_at"]) if r.get("merged_at") else None,
            url=r["url"],
        )
        for r in rows
    ]


def _closing_refs(message: str) -> list[int]:
    """Every PR/issue number a real GitHub closing keyword names in
    `message`, de-duplicated, first-seen order -- same contract as
    `commit-closes-keyword-issue-still-open/detector.py`'s own
    `_closing_refs`."""
    seen: list[int] = []
    for m in CLOSING_KEYWORD_RE.finditer(message):
        n = int(m.group(1))
        if n not in seen:
            seen.append(n)
    return seen


def _find_pr(number: int, prs: list[PullRequest]) -> PullRequest | None:
    for pr in prs:
        if pr.number == number:
            return pr
    return None


def compute_gaps(
    commits: list[Commit], prs: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. One candidate per (commit, referenced PR) pair: a
    commit naming several closing keywords for several different PR
    numbers makes its own separate promise to each, and each is checked on
    its own merits. A referenced PR that already resolved (merged or
    closed without merging), or that does not exist in this fixture's PR
    set at all, is excluded and named, not silently dropped -- a
    nonexistent target is this recipe's own dangling-reference seam, not a
    promise that should have fired but the target already existed."""
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
            pr = _find_pr(number, prs)
            if pr is None:
                excluded.append(GapCandidate(
                    slug=f"nonexistent-target-{commit.sha}-{number}",
                    headline=f"Commit {commit.sha} names #{number}, which does not exist in this repo",
                    detail=(
                        f"'{commit.message}' promises to close #{number}, but no such pull request "
                        "exists. A broken link, not a broken promise."
                    ),
                    confidence=0.0,
                    evidence=[commit.url],
                ))
                continue

            if pr.state in _RESOLVED_STATES:
                how = "merged" if pr.merged else "closed without merging"
                excluded.append(GapCandidate(
                    slug=f"already-resolved-{commit.sha}-{number}",
                    headline=f"Commit {commit.sha}'s promise to close #{number} already held",
                    detail=f"'{commit.message}' names #{number}, which is already {how}. Working as intended.",
                    confidence=0.0,
                    evidence=[commit.url, pr.url],
                ))
                continue

            age_hours = (now - commit.ts).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"commit-closes-keyword-pr-still-open-{commit.sha}-{number}",
                headline=f"Commit {commit.sha} promised to close #{number}; it's still open",
                detail=(
                    f"'{commit.message}' ({commit.url}) landed on the default branch "
                    f"{commit.ts.isoformat()} ({age_hours:.1f}h before this scan) naming a real "
                    f"GitHub closing keyword for #{number} ('{pr.title}'). The pull request still reads open."
                ),
                confidence=confidence,
                evidence=[commit.url, pr.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    commits_path: Path | None = None,
    prs_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListRepoCommits`/`ListPullRequests` read and these loaders are swapped
    for real reads. The detection logic does not change when that
    happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    commits = load_commits(commits_path)
    prs = load_prs(prs_path)
    surfaced, excluded = compute_gaps(commits, prs, now=now)
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
