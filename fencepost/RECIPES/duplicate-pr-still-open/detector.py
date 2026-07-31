"""Twenty-second real seam recipe: a pull request that names itself a
duplicate of another PR whose original has since closed or merged, while
the duplicate itself was never closed alongside it.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before this
one: this module only ever reads one local fixture file (`pulls.json`),
shaped like what `ListPullRequests`/`GetPullRequest` would return. Both
scopes already sit on SCOPES.md's cleared oath table under the `github`
row -- this recipe asks Arcade for nothing new.

The seam is the PR-side twin of `duplicate-issue-still-open` (the seventh
real recipe): a mortal (or a god) marks PR B "duplicate of #A" in its body,
meaning B's own fix arrives however A gets resolved. When A merges or
closes, B's own promise is done too -- but GitHub never closes B
automatically just because its body mentions A (that auto-close wiring only
exists for a PR naming a closing keyword against an ISSUE, which is exactly
`merged-pr-issue-still-open`'s seam, not this one's). B is left open,
orphaned, referencing a seam that already resolved without it. Neither A
alone nor B alone shows this -- only holding both at once does.

The duplicate-marker extraction (`named_duplicate_of`) lives in
`seam_engine.duplicate_markers` (task 400), not here -- this module imports
it rather than defining its own copy, the same law
`duplicate-issue-still-open/detector.py` now imports too, so
`tools/duplicate_regex_check.py` (task 397) never has cause to flag a
sixth hand-typed instance of an identical pattern.

Confidence is age-gated on how long the original PR has been resolved while
the duplicate still sits open -- see `recipe.json`'s `confidence_notes` for
the full reasoning.

This module's exclusion branch used to fold "the named original does not
exist at all" and "the named original exists but has not resolved yet" into
one `original is None or original.state not in _RESOLVED_STATES` check, one
shared slug (`original-still-open-...`), and one detail line that flatly
claimed "that PR has not resolved yet" even when no such PR was ever found
-- the same conflation `duplicate-issue-still-open/detector.py` carried on
its issue-original pair. Split here too, mirroring that fix:
`nonexistent-original-...` for a duplicate marker naming a number this
fixture doesn't carry at all, `original-still-open-...` reserved for a real
original that just hasn't merged or closed yet.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.duplicate_markers import named_duplicate_of as _named_duplicate_of
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "duplicate_pr_still_open" / "pulls.json"

# `_named_duplicate_of` is bound above, not redefined here --
# `seam_engine.duplicate_markers` (task 400) is the one real law describing
# a "duplicate of #N" marker now. `duplicate-issue-still-open/detector.py`
# imports the identical function rather than each recipe hand-typing its
# own copy of the same regex.

# A PR resolved under this age may not have been noticed yet by whoever
# filed the duplicate -- not yet a gap. Matches `duplicate-issue-still-
# open`'s own 24h bar: an unambiguous, easily-verified resolution signal
# (merged or closed) deserves the same short grace window on the PR side
# of the seam as it does on the issue side.
_STALE_HOURS = 24.0

# A PR counts as "resolved" here whether it merged or was closed without
# merging -- either way, whatever it promised to fix is done being tracked
# under that number, so a duplicate naming it is orphaned the same way in
# both cases.
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
    all -- a PR that resolved itself (whether via the duplicate marking or
    any other route) has no gap left to surface, the ordinary,
    unremarkable case. An open PR is excluded, named not hidden, the moment
    it names no duplicate marker, names an original this fixture doesn't
    carry at all, or names an original that is itself still open (no seam
    yet -- there is nothing for this PR to have missed). Everything left
    over -- an open PR whose named original already merged or closed -- is
    surfaced, aged into a confidence score `rank()` can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for pull in pulls:
        if pull.state != "open":
            continue

        number = _named_duplicate_of(pull.body)
        if number is None:
            excluded.append(GapCandidate(
                slug=f"no-duplicate-marker-{pull.number}",
                headline=f"PR #{pull.number} names no duplicate marker",
                detail=f"'{pull.title}' is open with no 'duplicate of #N' reference. No seam here.",
                confidence=0.0,
                evidence=[pull.url],
            ))
            continue

        original = _find_pull(number, pulls)
        if original is None:
            excluded.append(GapCandidate(
                slug=f"nonexistent-original-{pull.number}-{number}",
                headline=f"PR #{pull.number} names #{number}, which does not exist in this repo",
                detail=(
                    f"'{pull.title}' names #{number} as its original, but no such pull request "
                    "exists. A broken link, not a broken promise."
                ),
                confidence=0.0,
                evidence=[pull.url],
            ))
            continue

        if original.state not in _RESOLVED_STATES or original.closed_at is None:
            excluded.append(GapCandidate(
                slug=f"original-still-open-{pull.number}-{number}",
                headline=f"PR #{pull.number}'s named original #{number} is still open",
                detail=f"'{pull.title}' names #{number} as its original; that PR has not resolved yet. No seam here.",
                confidence=0.0,
                evidence=[pull.url, original.url],
            ))
            continue

        age_hours = (now - original.closed_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"duplicate-pr-still-open-{pull.number}-{number}",
            headline=f"PR #{pull.number} names #{number} as its original, which already {original.state}",
            detail=(
                f"'{pull.title}' names #{number} ('{original.title}') as its original, "
                f"{original.state} {original.closed_at.isoformat()} ({age_hours:.1f}h ago). "
                f"The duplicate still reads open."
            ),
            confidence=confidence,
            evidence=[pull.url, original.url],
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
    `ListPullRequests` read and this one loader is swapped for a real read.
    The detection logic does not change when that happens."""
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
