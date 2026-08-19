"""The eighty-fifth real seam recipe (ROADMAP.md #869): a pull request that
names itself blocked by another pull request, whose named blocker has
since resolved (merged or closed), while the blocked PR itself was never
revisited.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads one local fixture file
(`pulls.json`), shaped like what `ListPullRequests`/`GetPullRequest` would
return. Both scopes already sit on `SCOPES.md`'s cleared oath table under
the `github` row -- this recipe asks Arcade for nothing new.

The seam is the PR-side twin of `unblocked-issue-still-open` (task 593,
the sixty-first real recipe), the identical pairing shape
`duplicate-issue-still-open`/`duplicate-pr-still-open` (tasks 376/400) and
`milestone-closed-issue-still-open`/`milestone-closed-pr-still-open`
(tasks 379/380) already established for this engine: a mortal (or a god)
marks PR B "blocked by #A" (or "blocked on #A") in its own body, meaning
B's own work cannot start, or cannot finish, until A resolves. When A
merges or closes, B's own dependency clears -- but GitHub never revisits
B just because A resolved; nothing anywhere flags that a blocked PR's
blocker is now gone. B is left open, its own stated reason for waiting
already resolved, with nobody having come back to check.

Same claim distinction `unblocked-issue-still-open`'s own docstring
already drew, carried over unchanged for the PR side: a blocker marker
claims only a DEPENDENCY, never EQUIVALENCE. This recipe never claims B
should be closed (that would be `duplicate-pr-still-open`'s seam, wrongly
reused) -- it claims only that a fact B's own body asserts (I am blocked
by A) has quietly stopped being true, and nothing on either record shows
that anyone noticed. The no-grading law applies exactly as it does to
every sibling: the headline names the two PR numbers and the resolved
blocker's own timestamp, never a person, never a team, never a "should
have."

Confidence is age-gated on how long the blocker has been resolved while
the blocked PR still sits open -- see `recipe.json`'s `confidence_notes`
for the full reasoning behind reusing `unblocked-issue-still-open`'s and
`duplicate-pr-still-open`'s own 24-hour bar rather than inventing a new
number for a structurally similar self-declared-prose-marker family.

Imports `named_blocker_of` from `seam_engine.blocker_markers`
(ROADMAP.md #869) rather than defining a second hand-typed copy: this is
the SECOND recipe to read a "blocked by/on #N" marker, the exact
threshold `unblocked-issue-still-open/detector.py`'s own docstring named
as the moment the grammar should move out to a shared module, mirroring
`duplicate_markers.py`'s own two-user extraction for the "duplicate of
#N" family. `unblocked-issue-still-open/detector.py` was refactored in
the same commit to import the identical function rather than keep its own
copy, so `tools/duplicate_regex_check.py` never has cause to flag a
second hand-typed instance of an identical pattern.

A PR counts as "resolved" here whether it merged or was closed without
merging -- the identical `_RESOLVED_STATES` reasoning
`duplicate-pr-still-open/detector.py` already carries: either way,
whatever B was waiting on is done being tracked under that number, so a
blocked PR naming it is unblocked the same way in both cases.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.blocker_markers import named_blocker_of as _named_blocker_of
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "unblocked_pr_still_open" / "pulls.json"

# `_named_blocker_of` is bound above, not redefined here --
# `seam_engine.blocker_markers` (ROADMAP.md #869) is the one real law
# describing a "blocked by/on #N" marker now.
# `unblocked-issue-still-open/detector.py` imports the identical function
# too, as of the same commit.

# A blocker resolved under this age may not have been noticed yet by
# whoever is waiting on it -- not yet a gap. Matches
# `unblocked-issue-still-open`'s and `duplicate-pr-still-open`'s own 24h
# bar: an unambiguous, easily-verified resolution signal deserves the same
# short grace window on this seam as it does on its issue-side and
# duplicate-marker cousins.
_STALE_HOURS = 24.0

# A PR counts as "resolved" here whether it merged or was closed without
# merging -- either way, whatever it was blocking on is done being
# tracked under that number. Identical to `duplicate-pr-still-open`'s own
# `_RESOLVED_STATES`.
_RESOLVED_STATES = ("merged", "closed")


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    body: str
    closed_at: datetime | None
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [
        PullRequest(
            number=r["number"], title=r["title"], state=r["state"], body=r.get("body", ""),
            closed_at=_parse_ts(r["closed_at"]) if r.get("closed_at") else None,
            url=r["url"],
        )
        for r in rows
    ]


def _find_pull(number: int, pulls: list[PullRequest]) -> PullRequest | None:
    for pull in pulls:
        if pull.number == number:
            return pull
    return None


def compute_gaps(
    pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. Only PRs still in the `open` state are considered at
    all -- a PR that resolved itself has no gap left to surface, whatever
    its body once claimed about a blocker. An open PR is excluded, named
    not hidden, the moment it names no blocker marker, names a blocker
    this fixture doesn't carry at all, or names a blocker that is itself
    still open (no seam yet -- there is nothing this PR has missed). A
    blocker that reads resolved but carries no close timestamp is
    excluded as malformed, not folded into "still open" -- the two are
    different facts about the world. Everything left over -- an open PR
    whose named blocker already merged or closed, with a real timestamp
    -- is surfaced, aged into a confidence score `rank()` can honestly
    weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for pull in pulls:
        if pull.state != "open":
            continue

        number = _named_blocker_of(pull.body)
        if number is None:
            excluded.append(GapCandidate(
                slug=f"no-blocker-marker-{pull.number}",
                headline=f"PR #{pull.number} names no blocker marker",
                detail=f"'{pull.title}' is open with no 'blocked by #N' reference. No seam here.",
                confidence=0.0,
                evidence=[pull.url],
            ))
            continue

        blocker = _find_pull(number, pulls)
        if blocker is None:
            excluded.append(GapCandidate(
                slug=f"nonexistent-blocker-{pull.number}-{number}",
                headline=f"PR #{pull.number} names #{number} as its blocker, which does not exist in this repo",
                detail=(
                    f"'{pull.title}' names #{number} as its blocker, but no such pull request "
                    "exists. A broken link, not a broken promise."
                ),
                confidence=0.0,
                evidence=[pull.url],
            ))
            continue

        if blocker.state not in _RESOLVED_STATES:
            excluded.append(GapCandidate(
                slug=f"blocker-still-open-{pull.number}-{number}",
                headline=f"PR #{pull.number}'s named blocker #{number} is still open",
                detail=f"'{pull.title}' names #{number} as its blocker; that PR has not resolved yet. No seam here.",
                confidence=0.0,
                evidence=[pull.url, blocker.url],
            ))
            continue

        if blocker.closed_at is None:
            excluded.append(GapCandidate(
                slug=f"blocker-resolved-no-timestamp-{pull.number}-{number}",
                headline=f"PR #{pull.number}'s named blocker #{number} resolved with no timestamp",
                detail=(
                    f"'{pull.title}' names #{number} as its blocker; that PR reads resolved but "
                    "carries no close timestamp -- a malformed record, not an unresolved seam."
                ),
                confidence=0.0,
                evidence=[pull.url, blocker.url],
            ))
            continue

        age_hours = (now - blocker.closed_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"unblocked-pr-still-open-{pull.number}-{number}",
            headline=f"PR #{pull.number} names #{number} as its blocker, which already {blocker.state}",
            detail=(
                f"'{pull.title}' names #{number} ('{blocker.title}') as its blocker, "
                f"{blocker.state} {blocker.closed_at.isoformat()} ({age_hours:.1f}h ago). "
                f"The blocked PR still reads open."
            ),
            confidence=confidence,
            evidence=[pull.url, blocker.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListPullRequests` read and this one loader is swapped for a real
    read. The detection logic does not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(pulls, now=now)
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
