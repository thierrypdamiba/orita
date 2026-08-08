"""The seventy-third real seam recipe: a commit's own message claims a
pull request shipped ("ships #N" / "includes #N" / "merges #N" / "via
#N"), but the named pull request never actually merged.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads two local fixture files
(`commits.json`, `pulls.json`), shaped like what `ListRepoCommits` and
`ListPullRequests` would actually return. Both scopes already sit on
SCOPES.md's cleared oath table under the `github` row -- this recipe asks
Arcade for nothing new.

Task 604's own note (ROADMAP.md #604) named `commit-claims-unfixed-issue`
and `commit-claims-unmerged-pr` together as "the two structurally
unfillable cells... already covered under the `commit-closes-keyword-*`
names," and closed the ten-source-by-three-target claims-X grid at 28/30
genuinely open cells on that basis (2 marked permanently unfillable).
Rechecking
that claim against the live code rather than trusting the prior task's
own prose (the identical discipline Iron Rule #1's own history and task
610's `thanks.py` fix both hold): it is exactly right for
`commit-claims-unfixed-issue` -- `issue-comment-claims-unfixed-issue` and
every sibling in that leg of the family key off
`seam_engine.closing_keywords.CLOSING_KEYWORD_RE`
(fix(es)/fixed/close(s)/closed/resolve(s)/resolved), the identical grammar
`commit-closes-keyword-issue-still-open` already reads off a commit
message, so a second recipe watching the same grammar on the same surface
would be a pure duplicate, not a new seam. But it does NOT hold for
`commit-claims-unmerged-pr`: `release-claims-unmerged-pr`,
`mention-claims-unmerged-pr`, `tweet-claims-unmerged-pr`,
`review-comment-claims-unmerged-pr`, `issue-comment-claims-unmerged-pr`,
`milestone-claims-unmerged-pr`, `readme-claims-unmerged-pr`,
`linear-comment-claims-unmerged-pr`, and `slack-message-claims-unmerged-pr`
all key off the structurally DIFFERENT `seam_engine.pr_claims.PR_CLAIM_RE`
grammar ("ships/includes/merges/via #N") -- a phrase GitHub's real
closing-keyword parser has never once recognized, on any surface,
commit messages included. `commit-closes-keyword-pr-still-open` (checked
directly against its own imports below) reads only `CLOSING_KEYWORD_RE`,
never `PR_CLAIM_RE` -- a commit message reading "Ships #941, closing out
the whole batch" makes exactly the claim `commit-claims-open-milestone`
already proved a commit can make about a milestone (the "Ships milestone
#N" grammar is the identical verb, applied to a milestone number instead
of a PR number), and nothing in this engine has ever checked it against
the pull-request tracker. The door task 604 read as shut was open the
whole time; it was only ever checked from one side. With this recipe
shipped, the claims-X grid stands at 29/30 genuinely open cells filled;
`commit-claims-unfixed-issue` remains the one real, permanently unfillable
cell -- its claim grammar and its surface are both already fully owned by
`commit-closes-keyword-issue-still-open`, no correction pending there.

This is the same axis `commit-claims-open-milestone` (the sixty-sixth
recipe) already opened, extended one cell further: a commit message is an
eighth surface the `*-claims-unmerged-pr` family had never read, in the
identical way a commit message was once an eighth surface the
`*-claims-open-milestone` family had never read before task 466. It
shares only the general *shape* of `commit-claims-open-milestone` -- a
single, permanent record's own claim about a second tracker, checked
against that tracker's real state -- but reads the PR-claim grammar and
`ListPullRequests` instead of the milestone-claim grammar and
`ListMilestones`.

The claim stays narrow on purpose, the same no-grading law every sibling
holds: this recipe never claims the author did anything wrong, or that
the PR will never merge. A commit message naming a PR the moment before
that PR actually merges is completely ordinary -- the two events can land
minutes apart in either order, and nothing on GitHub's side ever forces
them to agree. The gap only exists once the claim has sat unresolved for
a while with nothing in the record itself explaining why.

Only a real "ships/includes/merges/via #N" claim phrase is treated as a
claim about the PR tracker at all -- a commit message that merely
mentions a bare `#N` in passing ("see #945 for background") makes no
shipped-it promise, and is excluded, not guessed into either bucket; that
bare-`#N` shape is `dangling-issue-reference`'s own seam, not this one's.
A claimed PR number that names no real pull request at all is excluded
too, named not hidden -- a broken reference belongs to
`dangling-issue-reference`'s own seam, not this one. A claimed PR that IS
merged is excluded -- the claim was simply true, no seam here. Everything
left over -- a commit message claiming a PR shipped while the PR tracker
itself still reads unmerged -- is surfaced, aged into a confidence score
`rank()` can honestly weigh.

Confidence is age-gated on hours since the commit's own `ts`, mirroring
`commit-claims-open-milestone`'s own reasoning rather than
`dangling-issue-reference`'s flat score: a claim checked within a few
hours of the commit landing may simply be a race (the commit pushed
moments before the real merge lands) -- not yet a settled disagreement
between the permanent record and the tracker. The identical 24-hour bar
and 0.5/0.85 split every `*-claims-unmerged-pr` sibling already uses,
rather than a flat score or a new number.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.pr_claims import claimed_pr_numbers as _claimed_pr_numbers
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "commit_claims_unmerged_pr"
DEFAULT_COMMITS_FIXTURE = _FIXTURE_DIR / "commits.json"
DEFAULT_PULLS_FIXTURE = _FIXTURE_DIR / "pulls.json"

# A claim checked within this window of the commit's own ts may just be a
# race (the commit landing moments before the real merge lands) rather
# than a genuine, settled documentation error -- matches every other
# *-claims-unmerged-pr sibling's own 24h bar rather than inventing a new
# number.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _load_rows(path: Path) -> list[Any]:
    """Refuses a syntactically valid but non-list payload with a named
    error, the same guard every sibling detector's own `_load_rows` holds."""
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
class PullRequest:
    number: int
    title: str
    state: str
    merged: bool
    url: str


def load_commits(path: Path | None = None) -> list[Commit]:
    rows = _load_rows(path or DEFAULT_COMMITS_FIXTURE)
    return [
        Commit(
            sha=r["sha"], message=r["message"], url=r["url"],
            ts=_parse_ts(r["ts"]), author=r.get("author", "unknown"),
        )
        for r in rows
    ]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [
        PullRequest(
            number=r["number"], title=r["title"], state=r["state"],
            merged=r["merged"], url=r["url"],
        )
        for r in rows
    ]


def _find_pull(number: int, pulls: list[PullRequest]) -> PullRequest | None:
    for pull in pulls:
        if pull.number == number:
            return pull
    return None


def compute_gaps(
    commits: list[Commit], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed PR is excluded, named not hidden, the
    moment a commit makes no 'ships/includes/merges/via #N' claim at all,
    the moment it names no real pull request at all, or the PR it names is
    already merged -- everything left over (a permanent commit message the
    PR tracker itself contradicts) is surfaced, aged into a confidence
    score rank() can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for commit in sorted(commits, key=lambda c: c.sha):
        numbers = _claimed_pr_numbers(commit.message)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{commit.sha}",
                headline=f"Commit {commit.sha} names no ships/includes/merges/via PR claim",
                detail=(
                    f"'{commit.message}' ({commit.url}) carries no "
                    "'ships/includes/merges/via #N' claim phrase. No seam here."
                ),
                confidence=0.0,
                evidence=[commit.url],
            ))
            continue

        # dict.fromkeys dedupes, order-preserving: a commit message naming
        # the same PR twice must not produce two identical GapCandidates
        # that tie each other out of rank()'s SEPARATION_MARGIN, the same
        # guard every *-claims-unmerged-pr sibling already holds.
        for number in dict.fromkeys(numbers):
            pull = _find_pull(number, pulls)
            if pull is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-pr-not-found-{commit.sha}-{number}",
                    headline=f"Commit {commit.sha} claims PR #{number}, which doesn't exist",
                    detail=(
                        f"'{commit.message}' ({commit.url}) claims #{number} shipped, "
                        "but no such pull request exists. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[commit.url],
                ))
                continue

            if pull.merged:
                excluded.append(GapCandidate(
                    slug=f"claim-true-{commit.sha}-{number}",
                    headline=f"Commit {commit.sha}'s claim about #{number} holds",
                    detail=(
                        f"'{commit.message}' ({commit.url}) claims #{number} "
                        f"('{pull.title}') shipped; the pull request is merged. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[commit.url, pull.url],
                ))
                continue

            age_hours = (now - commit.ts).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"commit-claims-unmerged-pr-{commit.sha}-{number}",
                headline=f"Commit {commit.sha} claims #{number} shipped, but it's still unmerged",
                detail=(
                    f"'{commit.message}' ({commit.url}, {commit.ts.isoformat()}, "
                    f"{age_hours:.1f}h ago) claims #{number} ('{pull.title}') shipped; the "
                    f"pull request's real state is '{pull.state}' (merged={pull.merged}). "
                    "Nothing on GitHub's side ever compares a commit message's own prose to "
                    "the pull-request tracker."
                ),
                confidence=confidence,
                evidence=[commit.url, pull.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    commits_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListRepoCommits`/`ListPullRequests` read and these two loaders are
    swapped for real reads. The detection logic does not change when that
    happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    commits = load_commits(commits_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(commits, pulls, now=now)
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
