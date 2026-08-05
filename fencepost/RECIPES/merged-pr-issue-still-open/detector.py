"""Second real seam recipe: a merged pull request said it would close an
issue, but the issue is still open.

RECIPES/example-release-vs-changelog/ has stood alone as the town's only
real recipe since ROADMAP.md #22 shipped the schema/validator. This recipe
exists to prove the other half of CONTRIBUTING.md's promise: that a second,
independently-written detector can sit beside the reference one and both
still clear `discover_recipes()`'s oath together (ROADMAP.md #108).

Read-only in spirit, MOCK ONLY in practice, same as the reference recipe:
this module only ever reads two local fixture files (`pulls.json`,
`issues.json`), shaped like what `ListPullRequests`/`ListIssues`/`GetIssue`
would return. All three scopes already sit on SCOPES.md's cleared oath
table -- this recipe asks Arcade for nothing new.

The seam: GitHub's own closing-keyword convention ("closes #N", "fixes #N",
"resolves #N", case-insensitive) is a promise a PR author makes in the PR
body. When that PR merges, GitHub auto-closes the referenced issue -- unless
something breaks the link (the issue was already closed and reopened, the
keyword was in a comment instead of the merged body, the automation simply
missed it). Whatever the cause, "merged, promised to close #N, #N still
open" is a real, unambiguous seam: it exists in neither the PR nor the issue
alone, only in holding both at once.

Confidence is age-gated, not flat, and the reasoning is the honest kind
Ogun's law asks for: a promised issue still open a few hours after merge is
not yet a gap (auto-close can lag, a human may simply not have looked yet);
still open a full day and more later is. `_STALE_HOURS = 24.0` is the one
number this recipe leans on, named here so a reviewer can see exactly what
it claims and why.

ROADMAP.md #429: as the oldest recipe in this family (task ~108), this
module's exclusion branch used to fold "the named issue does not exist at
all" and "the named issue exists and already closed" into one `issue is
None or issue.state == "closed"` check, one shared slug
(`issue-already-closed-...`), and one detail line that flatly claimed "it
already reads closed" even when no such issue was ever found. Every newer
sibling that solves this same referencing-record/target-record shape
already learned to split that: `merged-pr-pr-still-open/detector.py`'s
`nonexistent-target-...` vs `already-resolved-...`, `release-claims-
unfixed-issue/detector.py`, `release-claims-unmerged-pr/detector.py`. A
dangling reference (the number was never real) and a resolved promise (the
number was real and is now closed) are different facts about the world --
conflating them makes a false claim in the surviving branch's own words.
Split here too, now consistent with the rest of the family;
`issue-closed-pr-still-open/detector.py` carried the identical conflation
(`issue is None` folded into its own "still open" label) at the time this
paragraph was written, named here as a future task, not yet fixed.

ROADMAP.md #494: that forward pointer went stale without anyone circling
back to it -- `issue-closed-pr-still-open/detector.py` split its own
`issue is None` branch into a separate `nonexistent-target-...` slug at
task 430, the same hour this file's own note above still claimed the split
was undone. Both `test_issue_closed_pr_still_open_detector.py` (its own
"dangling reference" case, asserting `excluded[0].slug ==
"nonexistent-target-100-999"`) and this module's own sibling test
(`test_merged_pr_issue_still_open_detector.py`, the identical assertion)
have held that split for real ever since -- this paragraph is the only
place left still describing task 430's fix as future work. Corrected in
place, past tense, rather than left to mislead the next reader who trusts
a docstring over the code and tests sitting right below it.

ROADMAP.md #543: this file's own `_CLOSES_RE` used to be a private,
present-tense-only copy (`closes?|fix(?:es)?|resolves?`) that its own
comment admitted was "a subset... not the full spec it doesn't yet
implement." `commit-closes-keyword-issue-still-open/detector.py` (task
394) already proved, live, on this repo's own history (task 184: issues #1
and #2 closed themselves on a past-tense "closed #1"/"fixes #2" push),
that GitHub's real closing-keyword grammar fires on past tense exactly as
readily as present tense -- and a merged PR body is exactly as free to
write "This PR closed #42" as a commit message is. A PR that used past
tense to promise a close was invisible to this recipe: `_closed_issue_
numbers` never matched it, so a real "merged, promised, still open" gap
sat unsurfaced -- the opposite failure mode from Ogun's law (a false
negative, not a false positive), but still a real hole in the one thing
this recipe exists to watch. `seam_engine.closing_keywords.
CLOSING_KEYWORD_RE` (task 394) is the one real source for GitHub's full
nine-keyword grammar; this recipe now imports it instead of retyping a
narrower fourth copy, the same fix three siblings
(`commit-closes-keyword-issue-still-open`, `issue-closed-never-released`,
`release-claims-unfixed-issue`) already made.
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
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "merged_pr_issue_still_open" / "pulls.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "merged_pr_issue_still_open" / "issues.json"

# A promised close under this age may just be lagging automation, not a gap.
_STALE_HOURS = 24.0


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
class Issue:
    number: int
    title: str
    state: str
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(path.read_text())
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


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [Issue(number=r["number"], title=r["title"], state=r["state"], url=r["url"]) for r in rows]


def _closed_issue_numbers(body: str) -> list[int]:
    """Every issue number `body` names via a closing keyword, de-duplicated,
    first-seen order -- same discipline `commit-closes-keyword-issue-still-
    open/detector.py`'s `_closing_refs` already holds. A body naming the
    same number twice via two different keyword forms (e.g. "Closes #5 and
    also fixes #5") must not produce two identically-scored `GapCandidate`s
    for `rank()` to tie against itself (ROADMAP.md #444)."""
    seen: list[int] = []
    for n in CLOSING_KEYWORD_RE.findall(body):
        num = int(n)
        if num not in seen:
            seen.append(num)
    return seen


def _find_issue(number: int, issues: list[Issue]) -> Issue | None:
    for issue in issues:
        if issue.number == number:
            return issue
    return None


def compute_gaps(
    pulls: list[MergedPull], issues: list[Issue], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as `scan.compute_candidates`,
    `gmail_calendar.compute_gaps`, and the reference recipe's own
    `compute_gaps`. A PR is excluded, named not hidden, the moment it names
    no closing keyword at all, or the issue it names is already closed --
    everything left over (a still-open promise) is surfaced, aged into a
    confidence score rank() can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for pr in pulls:
        numbers = _closed_issue_numbers(pr.body)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-closing-keyword-{pr.number}",
                headline=f"PR #{pr.number} names no closing keyword",
                detail=f"'{pr.title}' merged with no closes/fixes/resolves reference. No seam here.",
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
                        f"'{pr.title}' promises to close #{number}, but no such issue "
                        "exists. A broken link, not a broken promise (see dangling-issue-reference)."
                    ),
                    confidence=0.0,
                    evidence=[pr.url],
                ))
                continue

            if issue.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"issue-already-closed-{pr.number}-{number}",
                    headline=f"PR #{pr.number}'s promised issue #{number} is already closed",
                    detail=f"'{pr.title}' promised to close #{number}; it already reads closed. No seam here.",
                    confidence=0.0,
                    evidence=[pr.url, issue.url],
                ))
                continue

            age_hours = (now - pr.merged_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.55
            surfaced.append(GapCandidate(
                slug=f"merged-pr-issue-still-open-{pr.number}-{number}",
                headline=f"PR #{pr.number} promised to close #{number}, but #{number} is still open",
                detail=(
                    f"'{pr.title}' merged {pr.merged_at.isoformat()} ({age_hours:.1f}h ago) "
                    f"naming #{number} ('{issue.title}'); the issue still reads open."
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
    """The manifest's `entrypoint`. Same output shape as
    `gmail_calendar.run_gmail_calendar_scan` and the reference recipe's own
    `run_recipe_scan` -- `source: "fixture"` is the honest WIP marker this
    recipe carries until the Hand's gateway carries live PR/issue scopes and
    these two loaders are swapped for real reads. The detection logic does
    not change when that happens."""
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
