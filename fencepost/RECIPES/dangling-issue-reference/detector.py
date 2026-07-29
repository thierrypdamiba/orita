"""Fourth real seam recipe: a commit's own message counts on an issue or
pull request that isn't actually there.

`RECIPES/example-release-vs-changelog/`, `RECIPES/merged-pr-issue-still-open/`,
and `RECIPES/release-not-tweeted/` all compare two records that were each,
individually, real and complete -- the gap was in whether one echoed the
other. This recipe watches a narrower, meaner seam: a single record (a
commit message) making a factual claim about a SECOND record (an issue or
PR) that the second record then fails to back up at all. GitHub renders
`#12` in a commit message as a clickable link without ever checking it
resolves to anything real -- a typo, a deleted issue, or a number that
belonged to a different repo entirely all render identically, and the
commit log is permanent and never gets a second edit pass. Nobody reads
`git log` looking for broken links; this recipe does, on purpose.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads three local fixture files (`commits.json`,
`issues.json`, `pulls.json`), shaped like what `ListRepoCommits`,
`ListIssues`, and `ListPullRequests` would actually return. All three
scopes already sit on SCOPES.md's cleared oath table under the `github`
row -- this recipe asks Arcade for nothing new.

The seam: `#N` inside a commit message is GitHub's own shorthand for "issue
or pull request N in this repo" -- the two share one number sequence, so a
reference has to be checked against both lists, not just one, or a
reference to a merged PR would misfire as a false "dangling" gap (exactly
the crying-wolf failure Ogun's law calls fatal). A reference of the form
`owner/repo#N` names a DIFFERENT repo's own number space on purpose --
GitHub's own cross-repo shorthand -- and is never even extracted as a
candidate here; that is a seam for a recipe watching that other repo, not
a gap in this one.

The extraction regex and cross-repo exclusion this recipe first wrote now
live in `seam_engine.references` (task 389), not here -- this module
imports `referenced_numbers` rather than defining its own copy, so
`mention-dangling-reference/detector.py`'s identical need (task 388) reads
the same law instead of a second, independently-typed regex.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.references import referenced_numbers as _referenced_numbers
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_COMMITS_FIXTURE = _HERE.parents[1] / "fixtures" / "dangling_issue_reference" / "commits.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "dangling_issue_reference" / "issues.json"
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "dangling_issue_reference" / "pulls.json"

# `_referenced_numbers` is bound above, not redefined here --
# `seam_engine.references` (task 389) is the one real law describing what
# counts as a same-repo `#N` reference now. This was this recipe's OWN
# regex first (task 368); `mention-dangling-reference/detector.py` (task
# 388) copied it a second time with a claim of "not a second copy... drift
# apart" that the code did not actually back up. Task 389 made the claim
# true: both recipes import the identical function from here, so a future
# tightening of the grammar can no longer land in one detector and not the
# other by accident. The regex itself (`seam_engine.references.REF_RE`) no
# longer needs a module-level alias here -- nothing in this file calls it
# directly anymore, only through `_referenced_numbers`.

# Confidence for an unmatched reference. Flat, not age-gated like this
# engine's other two-list detectors (merged-pr-issue-still-open,
# release-not-tweeted) -- a commit message never gets a second chance to
# fix its own claim the way a PR body or a tweet timeline can catch up
# later, so there is no "give it 24 hours" grace period that means anything
# here. See recipe.json's `confidence_notes` for why 0.8, not higher.
_DANGLING_CONFIDENCE = 0.8


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _load_rows(path: Path) -> list[Any]:
    """Load a whole-file JSON list, refusing a syntactically valid but
    non-list payload with a named error instead of letting it reach a `for`
    loop unmarked. Mirrors `RECIPES/merged-pr-issue-still-open/detector.py`'s
    own `_load_rows` exactly -- the identical bug class, task 358/359's own
    fix, applied here from the start rather than found later."""
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


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
    url: str


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    url: str


def load_commits(path: Path | None = None) -> list[Commit]:
    rows = _load_rows(path or DEFAULT_COMMITS_FIXTURE)
    return [
        Commit(sha=r["sha"], message=r["message"], url=r["url"], ts=_parse_ts(r["ts"]), author=r.get("author", "unknown"))
        for r in rows
    ]


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [Issue(number=r["number"], title=r["title"], state=r["state"], url=r["url"]) for r in rows]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [PullRequest(number=r["number"], title=r["title"], state=r["state"], url=r["url"]) for r in rows]


def compute_gaps(
    commits: list[Commit], issues: list[Issue], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other detector in
    this engine. A commit with no `#N` reference at all is not examined --
    it never claims anything about a second record, so there is no seam to
    weigh, the same "not an invite at all" exclusion `gmail_calendar.
    compute_gaps` makes for a plain email. `now` is accepted, unused,
    for interface parity with every sibling recipe's `compute_gaps(..., *,
    now=...)` shape (a future confidence refinement -- e.g. a very old
    dangling reference is less actionable than a fresh one -- could use it
    without changing this function's signature again)."""
    del now  # unused today; kept for interface parity, see docstring

    known_numbers = {i.number for i in issues} | {p.number for p in pulls}

    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for c in commits:
        for n in _referenced_numbers(c.message):
            if n in known_numbers:
                excluded.append(GapCandidate(
                    slug=f"dangling-ref-matched-{c.sha}-{n}",
                    headline=f"Commit {c.sha}'s reference to #{n} matches a real issue or PR",
                    detail=f"'{c.message}' ({c.url}) references #{n}; a real issue or pull "
                           f"request #{n} exists in this repo. No seam here.",
                    confidence=0.0,
                    evidence=[c.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"dangling-issue-reference-{c.sha}-{n}",
                headline=f"Commit {c.sha} references #{n}, but no issue or PR #{n} exists here",
                detail=f"'{c.message}' ({c.url}) references #{n}; ListIssues + "
                       f"ListPullRequests found no issue or pull request with that number "
                       f"in this repo. Likely a typo, a reference to something deleted, "
                       f"or a number meant for a different repo, left standing in the "
                       f"permanent commit log.",
                confidence=_DANGLING_CONFIDENCE,
                evidence=[c.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    commits_path: Path | None = None,
    issues_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListRepoCommits`/`ListIssues`/`ListPullRequests` read for a connected
    account and these three loaders are swapped for real reads. The
    detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    commits = load_commits(commits_path)
    issues = load_issues(issues_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(commits, issues, pulls, now=now)
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
