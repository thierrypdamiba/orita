"""Hundred-twelfth real seam recipe: a pull request reached merged=true
while its own live GitHub review_decision still read CHANGES_REQUESTED --
a reviewer's objection that was never superseded by a later APPROVED
review, a dismissal, or a re-review before the merge button was pressed
anyway.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads one local fixture file
(`pull_requests.json`), shaped like what `ListPullRequests` (with each
PR's own live review decision) would actually return. The scope already
sits on `SCOPES.md`'s cleared oath table -- `../approved-pr-still-
unmerged/` already reads the identical `review_decision` field off the
identical `ListPullRequests` call. No new scope is asked for anywhere in
this recipe.

Distinct from the closest sibling, `../approved-pr-still-unmerged/`: that
recipe watches an APPROVED review that never got its own merge -- the
"granted but not taken" gap. This recipe watches the opposite silence: a
CHANGES_REQUESTED review that never got its own resolution, yet the PR
merged anyway. GitHub renders review_decision as a live aggregate of every
review currently in force, already accounting for a dismissal or a
superseding later review, so a merged PR whose review_decision still
reads CHANGES_REQUESTED at scan time means, on the record GitHub itself
keeps, nobody ever walked the objection back -- the merge and the
open objection sit in the same repository, at the same instant, with
nothing in the UI or the API that ever cross-checks one against the
other.

review_decision is read as GitHub's own live aggregate, not re-derived
from an individual review list -- the same trust `approved-pr-still-
unmerged` already places in the identical field. A branch-protection
override by a repository admin is a real, legitimate path to this exact
state (merge over a required review, on purpose) that this recipe cannot
distinguish from a plain oversight; the confidence is capped to reflect
that one irreducible blind spot rather than reading as an accusation --
see `recipe.json`'s `confidence_notes` for the full reasoning.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_PULL_REQUESTS_FIXTURE = (
    _HERE.parents[1] / "fixtures" / "merged_pr_changes_requested_not_addressed" / "pull_requests.json"
)

# Flat, not aged: unlike a still-open PR (whose gap can only get more
# settled the longer it waits, the shape `approved-pr-still-unmerged`'s
# own 24h staleness bar exists for), a merge is a single, already-complete
# event -- there is no "how long has this sat" to weigh, the objection was
# either resolved on the record before that one instant or it was not.
_CONFIDENCE = 0.8


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    merged: bool
    review_decision: str | None
    merged_at: datetime | None
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_pull_requests(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULL_REQUESTS_FIXTURE)
    return [
        PullRequest(
            number=r["number"], title=r["title"], state=r["state"],
            merged=r.get("merged", False), review_decision=r.get("review_decision"),
            merged_at=_parse_ts(r["merged_at"]) if r.get("merged_at") else None,
            url=r["url"],
        )
        for r in rows
    ]


def compute_gaps(pull_requests: list[PullRequest]) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. A pull request that never merged is excluded outright:
    whatever its review_decision says, there is no merge to have gone
    ahead of it. A merged pull request whose review_decision is not
    CHANGES_REQUESTED kept no unresolved objection open at merge time --
    excluded too, nothing was missed. Everything left over -- merged with
    review_decision still CHANGES_REQUESTED -- is the gap this recipe
    exists to name."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for pr in pull_requests:
        if not pr.merged:
            excluded.append(GapCandidate(
                slug=f"merged-pr-changes-requested-not-merged-{pr.number}",
                headline=f"PR #{pr.number} never merged",
                detail=f"'{pr.title}' (#{pr.number}) is {pr.state}, merged={pr.merged}. No seam here.",
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        if pr.review_decision != "CHANGES_REQUESTED":
            excluded.append(GapCandidate(
                slug=f"merged-pr-changes-requested-no-objection-{pr.number}",
                headline=f"PR #{pr.number} merged with no open CHANGES_REQUESTED review",
                detail=(
                    f"'{pr.title}' (#{pr.number}) merged with review_decision="
                    f"{pr.review_decision!r}. No unresolved objection, nothing missed."
                ),
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        merged_at = pr.merged_at.isoformat() if pr.merged_at else "an unknown time"
        surfaced.append(GapCandidate(
            slug=f"merged-pr-changes-requested-not-addressed-{pr.number}",
            headline=f"PR #{pr.number} merged while its most recent review still reads CHANGES_REQUESTED",
            detail=(
                f"'{pr.title}' (#{pr.number}) merged at {merged_at}; review_decision was "
                "still CHANGES_REQUESTED at that instant, and nothing on the record shows "
                "the objection was ever resolved."
            ),
            confidence=_CONFIDENCE,
            evidence=[pr.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    pull_requests_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListPullRequests` read (with each PR's own review decision) and this
    one loader is swapped for a real read. The detection logic does not
    change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    pull_requests = load_pull_requests(pull_requests_path)
    surfaced, excluded = compute_gaps(pull_requests)
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
