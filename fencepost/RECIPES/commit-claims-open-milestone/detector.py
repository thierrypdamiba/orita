"""The sixty-sixth real seam recipe: a commit's own message claims a
milestone shipped ("milestone #N"), but the named milestone is not
actually closed.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads two local fixture files
(`commits.json`, `milestones.json`), shaped like what `ListRepoCommits`
and `ListMilestones` would actually return. Both scopes already sit on
SCOPES.md's cleared oath table under the `github` row -- this recipe asks
Arcade for nothing new.

The seam it watches sits on a scope PAIR none of the sixty-five prior
recipes has ever combined: `ListRepoCommits` and `ListMilestones` in the
same detector, reading `seam_engine.milestone_claims.claimed_milestone_numbers`
-- the shared "milestone #N" claim grammar ten prior recipes already
import (`milestone-closed-never-released`, `release-claims-open-milestone`,
`milestone-closed-not-tweeted`, `tweet-claims-open-milestone`,
`mention-claims-open-milestone`, `readme-claims-open-milestone`,
`review-comment-claims-open-milestone`, `issue-comment-claims-open-milestone`,
plus `milestone-claims-open-milestone` and `milestone-claims-unfixed-issue`
for the sibling grammars) -- against a text surface none of them has ever
read: a commit message. `dangling-issue-reference` (the fourth real
recipe) already proved a commit message is a real, permanent claim-bearing
surface, but it only ever checks a bare `#N` against the issue/PR number
space, never a `milestone #N` phrase against the milestone tracker. The
three `commit-closes-keyword-*` recipes also already read commit messages,
but only for GitHub's own real closing-keyword grammar
(close/closes/closed/fix/fixes/fixed/resolve/resolves/resolved), which
targets issues and pull requests -- GitHub gives a milestone no
auto-close-style keyword of its own at all (the same fact
`milestone_claims.py`'s own module docstring already states, and the
reason the "milestone #N" grammar had to be invented in the first place,
rather than overloading the issue-side closing-keyword one). Structurally,
none of those three recipes could ever see this seam: their own detection
logic never looks past a match on the closing-keyword regex, which a
"milestone #N" phrase never satisfies. A maintainer writing a commit
message like "Ships milestone #47, closing out the whole batch" or
"Completes milestone #12" makes exactly the same kind of permanent,
public, unedited claim `release-claims-open-milestone` and
`tweet-claims-open-milestone` already watch on their own surfaces --
GitHub renders `#47` inside a commit message as a clickable link the
identical way regardless of whether it resolves to an issue, a PR, or (as
here) is meant to name a milestone, and nothing on GitHub's side ever
opens the milestone tracker to check a commit message's own prose against
it.

This is a genuinely different axis from every family this repo has
already saturated. It is not the claims-X grid crossed against the seven
external text surfaces this repo's own `*-claims-open-milestone` family
already covers exhaustively (issue-comment, mention, milestone, readme,
release, review-comment, tweet) -- a commit message is an eighth surface
none of those seven recipes reads, and this recipe never touches any of
their seven fixtures. It is not the dangling-reference grid (nine legs,
all asking whether a referenced `#N` target *exists* in the issue/PR
number space) -- this recipe never looks up a bare `#N` at all, and never
reads `ListIssues` or `ListPullRequests`; a claimed milestone that does
not exist is excluded here, named not hidden, as belonging to a future
milestone-side dangling-reference recipe's own seam, the same boundary
`release-claims-open-milestone` already draws for itself. It is not the
`commit-closes-keyword-*` family (three recipes, all reading commit
messages, all requiring the real GitHub closing-keyword grammar against
an issue or PR number) -- this recipe requires the structurally different
"milestone #N" phrase and reads `ListMilestones`, a scope none of those
three ever declares. It shares only the general *shape* of
`release-claims-open-milestone` (task 385) -- a single, permanent record's
own claim about a milestone, checked against the milestone tracker's real
state -- but reads a commit message instead of a release body, the one
"claims a milestone" surface this repo had never actually reached despite
already reading commit messages for two OTHER grammars.

The claim stays narrow on purpose, the same no-grading law every sibling
holds: this recipe never claims the author did anything wrong, or that
the milestone will never close. A commit message naming a milestone the
moment before that milestone's own last issue gets closed out is
completely ordinary -- the two events can land minutes apart in either
order, and there is no forcing function on GitHub's side that would ever
make them agree with each other automatically. The gap only exists once
the claim has sat unresolved for a while with nothing in the record
itself explaining why.

Only a real "milestone #N" claim phrase is treated as a claim about the
milestone tracker at all -- a commit message that merely mentions a bare
`#N` in passing ("see #47 for context", "related to #12") makes no
milestone-shipped promise, and is excluded, not guessed into either
bucket; that bare-`#N` shape is `dangling-issue-reference`'s own seam
(over issues/PRs), not this one's. A claimed milestone number that names
no real milestone at all is excluded too, named not hidden -- a broken
reference belongs to a future milestone-side dangling-reference recipe,
not this one. A claimed milestone that IS closed is excluded -- the claim
was simply true, no seam here. Everything left over -- a commit message
claiming a milestone shipped while the milestone tracker itself still
reads open -- is surfaced, aged into a confidence score `rank()` can
honestly weigh.

A commit message is permanent the instant it is pushed, the same
"immutable ground truth" property `dangling-issue-reference`'s own
confidence reasoning already leans on -- there is no editing a commit
message after the fact the way a release body, a tweet, or a comment can
still be revised. But mirroring `release-claims-open-milestone`'s and
`tweet-claims-open-milestone`'s own reasoning rather than
`dangling-issue-reference`'s flat score: a claim checked within a few
hours of the commit landing may simply be a race (the commit pushed
moments before the milestone is actually closed out, a maintainer
squashing several PRs and closing the milestone in the same sitting) --
not yet a settled disagreement between the permanent record and the
tracker. Confidence is therefore age-gated on hours since the commit's
own `ts`, the identical 24-hour bar and 0.5/0.85 split every sibling in
this family already uses, rather than a flat score or a new number.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.milestone_claims import claimed_milestone_numbers as _claimed_milestone_numbers
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "commit_claims_open_milestone"
DEFAULT_COMMITS_FIXTURE = _FIXTURE_DIR / "commits.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# A claim checked within this window of the commit's own ts may just be a
# race (the commit landing moments before the milestone is actually closed
# out) rather than a genuine, settled documentation error -- matches every
# other *-claims-open-milestone sibling's own 24h bar rather than inventing
# a new number.
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
class Milestone:
    number: int
    title: str
    state: str
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


def load_milestones(path: Path | None = None) -> list[Milestone]:
    rows = _load_rows(path or DEFAULT_MILESTONES_FIXTURE)
    return [
        Milestone(number=r["number"], title=r["title"], state=r["state"], url=r["url"])
        for r in rows
    ]


def _find_milestone(number: int, milestones: list[Milestone]) -> Milestone | None:
    for milestone in milestones:
        if milestone.number == number:
            return milestone
    return None


def compute_gaps(
    commits: list[Commit], milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed milestone is excluded, named not hidden,
    the moment a commit makes no 'milestone #N' claim at all, the moment it
    names no real milestone at all, or the milestone it names is already
    closed -- everything left over (a permanent commit message the
    milestone tracker itself contradicts) is surfaced, aged into a
    confidence score rank() can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for commit in sorted(commits, key=lambda c: c.sha):
        numbers = _claimed_milestone_numbers(commit.message)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{commit.sha}",
                headline=f"Commit {commit.sha} names no milestone claim",
                detail=(
                    f"'{commit.message}' ({commit.url}) carries no 'milestone #N' claim "
                    "phrase. No seam here."
                ),
                confidence=0.0,
                evidence=[commit.url],
            ))
            continue

        # dict.fromkeys dedupes, order-preserving: a commit message naming
        # the same milestone twice must not produce two identical
        # GapCandidates that tie each other out of rank()'s
        # SEPARATION_MARGIN, the same guard release-claims-open-milestone
        # already holds.
        for number in dict.fromkeys(numbers):
            milestone = _find_milestone(number, milestones)
            if milestone is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-not-found-{commit.sha}-{number}",
                    headline=f"Commit {commit.sha} claims milestone #{number}, which doesn't exist",
                    detail=(
                        f"'{commit.message}' ({commit.url}) claims milestone #{number} "
                        "shipped, but no such milestone exists. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[commit.url],
                ))
                continue

            if milestone.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{commit.sha}-{number}",
                    headline=f"Commit {commit.sha}'s claim about milestone #{number} holds",
                    detail=(
                        f"'{commit.message}' ({commit.url}) claims milestone #{number} "
                        f"('{milestone.title}') shipped; the milestone is closed. No seam here."
                    ),
                    confidence=0.0,
                    evidence=[commit.url, milestone.url],
                ))
                continue

            age_hours = (now - commit.ts).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"commit-claims-open-milestone-{commit.sha}-{number}",
                headline=f"Commit {commit.sha} claims milestone #{number} shipped, but it's still open",
                detail=(
                    f"'{commit.message}' ({commit.url}, {commit.ts.isoformat()}, "
                    f"{age_hours:.1f}h ago) claims milestone #{number} ('{milestone.title}') "
                    f"shipped; the milestone's real state is '{milestone.state}'. Nothing on "
                    "GitHub's side ever compares a commit message's own prose to the milestone "
                    "tracker."
                ),
                confidence=confidence,
                evidence=[commit.url, milestone.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    commits_path: Path | None = None,
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListRepoCommits`/`ListMilestones` read and these two loaders are
    swapped for real reads. The detection logic does not change when that
    happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    commits = load_commits(commits_path)
    milestones = load_milestones(milestones_path)
    surfaced, excluded = compute_gaps(commits, milestones, now=now)
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
