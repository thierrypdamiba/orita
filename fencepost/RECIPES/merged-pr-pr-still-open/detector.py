"""Twenty-sixth real seam recipe: a merged pull request's own body names a
GitHub closing keyword for ANOTHER pull request that is still open, rather
than an issue.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before this
one: this module only ever reads two local fixture files (`pulls.json`,
`prs.json`), both shaped like what `ListPullRequests` would return (the
referencing PR merged; the target PR did not). One scope, already cleared
on SCOPES.md's oath table -- this recipe asks Arcade for nothing new.

The seam: `merged-pr-issue-still-open` (the second real recipe) proved that
a merged PR's own closing-keyword promise can silently never fire -- but it
explicitly, deliberately, only ever checked the number against the repo's
ISSUE set. GitHub's real auto-close trigger does not care which record type
the named number belongs to: a merged PR's own body carrying `closes #N` /
`fixes #N` / `resolves #N` (present OR past tense) makes the identical
promise whether #N resolves to an issue OR another pull request. That is a
second, entirely unwatched half of the same seam -- and the last quarter of
a 2x2 matrix three siblings already cover three-quarters of:

    source \\ target      issue                          PR
    commit              commit-closes-keyword-           commit-closes-keyword-
                         issue-still-open                pr-still-open
    merged PR body      merged-pr-issue-still-open       merged-pr-pr-still-open (this one)

`commit-closes-keyword-pr-still-open` proved the identical shift (issue set
-> PR set) on the commit side; this recipe is that exact shift applied to
the merged-PR side, closing the matrix's last open cell.

`CLOSING_KEYWORD_RE` is imported from `seam_engine.closing_keywords` (task
394) -- the one real source several recipes already bind to -- rather than
retyped a seventh time. `tools/duplicate_regex_check.py` exists precisely
to catch a recipe that promises reuse in its docstring but retypes the
pattern anyway; this recipe imports for real, not just in prose.

A referencing PR naming a target PR number that does not exist in this
fixture's PR set at all is excluded, not surfaced -- a broken link, not a
broken promise, the identical `dangling-issue-reference`-shaped seam every
sibling in this family already carves out. A referencing PR naming its OWN
number is excluded too -- a PR cannot meaningfully promise to close itself,
and GitHub's own UI does not treat a self-reference as a closing trigger at
all, so surfacing it here would be a false gap, not a real one. A
referencing PR naming an already-resolved target -- merged, or closed
without merging -- is excluded: either way, whatever that PR promised is
done being tracked under that number, the promise held (matches
`commit-closes-keyword-pr-still-open`'s own `_RESOLVED_STATES` reasoning,
applied to the merged-PR source instead of a commit).

Confidence is age-gated on how long the referencing PR has sat merged while
the target PR stays open -- the identical 0.55-under-24h / 0.85-at-or-
past-24h shape `merged-pr-issue-still-open` uses on the issue side, no
deviation: nothing about checking a PR number instead of an issue number
changes how quickly GitHub's real auto-close trigger would have fired or
how long a grace period a human re-checking it deserves.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "merged_pr_pr_still_open"
DEFAULT_PULLS_FIXTURE = _FIXTURE_DIR / "pulls.json"
DEFAULT_PRS_FIXTURE = _FIXTURE_DIR / "prs.json"

# A promised close under this age may just be lagging automation, or nobody
# has re-checked yet -- not yet a gap. Matches merged-pr-issue-still-open's
# own bar exactly.
_STALE_HOURS = 24.0

# A target PR counts as "resolved" here whether it merged or was closed
# without merging -- either way, whatever it promised is done being tracked
# under that number. Matches commit-closes-keyword-pr-still-open's own
# `_RESOLVED_STATES` reasoning, applied to the same shared number space.
_RESOLVED_STATES = ("closed",)


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class MergedPull:
    id: str
    title: str
    number: int
    body: str
    merged_at: datetime
    url: str


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


def load_pulls(path: Path | None = None) -> list[MergedPull]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [
        MergedPull(
            id=r["id"], title=r["title"], number=r["number"], body=r["body"],
            merged_at=_parse_ts(r["merged_at"]), url=r["url"],
        )
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


def _closing_refs(body: str) -> list[int]:
    """Every PR/issue number a real GitHub closing keyword names in `body`,
    de-duplicated, first-seen order -- same contract as
    `commit-closes-keyword-pr-still-open/detector.py`'s own `_closing_refs`."""
    seen: list[int] = []
    for m in CLOSING_KEYWORD_RE.finditer(body):
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
    pulls: list[MergedPull], prs: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. One candidate per (referencing PR, target PR) pair: a PR
    naming several closing keywords for several different PR numbers makes
    its own separate promise to each, checked on its own merits. A
    self-reference, a nonexistent target, or an already-resolved target is
    excluded and named, not silently dropped."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for pull in pulls:
        refs = _closing_refs(pull.body)
        if not refs:
            excluded.append(GapCandidate(
                slug=f"no-closing-keyword-{pull.number}",
                headline=f"PR #{pull.number} names no closing keyword",
                detail=f"'{pull.title}' merged with no closes/fixes/resolves reference. No seam here.",
                confidence=0.0,
                evidence=[pull.url],
            ))
            continue

        for number in refs:
            if number == pull.number:
                excluded.append(GapCandidate(
                    slug=f"self-reference-{pull.number}",
                    headline=f"PR #{pull.number} names itself as its own closing target",
                    detail=f"'{pull.title}' names #{number}, its own number. Not a real promise.",
                    confidence=0.0,
                    evidence=[pull.url],
                ))
                continue

            target = _find_pr(number, prs)
            if target is None:
                excluded.append(GapCandidate(
                    slug=f"nonexistent-target-{pull.number}-{number}",
                    headline=f"PR #{pull.number} names #{number}, which does not exist in this repo",
                    detail=(
                        f"'{pull.title}' promises to close #{number}, but no such pull request "
                        "exists. A broken link, not a broken promise."
                    ),
                    confidence=0.0,
                    evidence=[pull.url],
                ))
                continue

            if target.state in _RESOLVED_STATES:
                how = "merged" if target.merged else "closed without merging"
                excluded.append(GapCandidate(
                    slug=f"already-resolved-{pull.number}-{number}",
                    headline=f"PR #{pull.number}'s promise to close #{number} already held",
                    detail=f"'{pull.title}' names #{number}, which is already {how}. Working as intended.",
                    confidence=0.0,
                    evidence=[pull.url, target.url],
                ))
                continue

            age_hours = (now - pull.merged_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.55
            surfaced.append(GapCandidate(
                slug=f"merged-pr-pr-still-open-{pull.number}-{number}",
                headline=f"PR #{pull.number} promised to close #{number}, but #{number} is still open",
                detail=(
                    f"'{pull.title}' merged {pull.merged_at.isoformat()} ({age_hours:.1f}h ago) "
                    f"naming #{number} ('{target.title}'); the pull request still reads open."
                ),
                confidence=confidence,
                evidence=[pull.url, target.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    pulls_path: Path | None = None,
    prs_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListPullRequests` read and these loaders are swapped for real reads.
    The detection logic does not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    pulls = load_pulls(pulls_path)
    prs = load_prs(prs_path)
    surfaced, excluded = compute_gaps(pulls, prs, now=now)
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
