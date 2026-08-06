"""The fiftieth real seam recipe: a milestone's own description names a
real ships/includes/merges/via #N PR-claim phrase, but the named PR never
actually merged.

The milestone-side leg the claims-unmerged-pr family had never grown.
`readme-claims-unmerged-pr`, `release-claims-unmerged-pr`,
`tweet-claims-unmerged-pr`, and `mention-claims-unmerged-pr` already cover
every surface -- the town's own README, its own release notes, its own
tweets, and a stranger's own X mention -- but none of them ever reads a
milestone's own `description` field. `milestone-claims-unfixed-issue`
(task 535, the forty-fifth real recipe) closed the identical gap for the
sibling claims-unfixed-issue family -- a milestone's description already
gets checked for a closing-keyword issue claim -- but the PR-claim grammar
("ships/includes/merges/via #N") was never checked against that same
free-text field, even though `milestone-body-dangling-reference` (task
504/511) already reads it for a completely different question (does #N
exist at all).

Deliberately reuses `seam_engine.pr_claims.claimed_pr_numbers` verbatim --
the same shared "ships/includes/merges/via #N" grammar
`release-claims-unmerged-pr`, `merged-pr-never-released`,
`tweet-claims-unmerged-pr`, and `mention-claims-unmerged-pr` already
import from there -- rather than a fifth independently-retyped copy of
the identical pattern.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`milestones.json`,
`pulls.json`), shaped like what `ListMilestones` and `ListPullRequests`
would actually return. Both scopes already sit on `SCOPES.md`'s cleared
oath table -- this recipe asks Arcade for nothing new.

The seam: a ships/includes/merges/via `#N` claim phrase inside a
milestone's own description names a PR by number. If that PR does not
exist at all, it is excluded here -- a broken reference is
`milestone-body-dangling-reference`'s own seam, not this one's. If it
exists and is merged, the claim was simply true -- excluded, named not
hidden. If it exists and is NOT merged (still open, or closed without
merging), the milestone's own free-text description disagrees with the PR
tracker's real state: that is the gap.

Confidence is age-gated off the milestone's own `updated_at`, holding
`milestone-claims-unfixed-issue`'s own 0.55/0.85 24-hour bar exactly, not
a discounted copy of it -- the identical reasoning applies unchanged: a
milestone description is a text surface its author can still edit at any
time, so a fresh claim earns the same grace window before being scored as
a confirmed gap. A milestone with no description at all is excluded
outright -- there is no claim to have broken.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "milestone_claims_unmerged_pr"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"
DEFAULT_PULLS_FIXTURE = _FIXTURE_DIR / "pulls.json"

# A dangling claim inside a description touched less than this many hours
# ago is not yet scored as a confirmed gap -- it may simply not have
# merged yet. Same 24-hour shape as milestone-claims-unfixed-issue's own
# _EDIT_GRACE_WINDOW_HOURS, applied here for the identical reason: a
# milestone's description is a text surface its author can still edit at
# any time.
_EDIT_GRACE_WINDOW_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    description: str
    updated_at: datetime
    url: str


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    merged: bool
    url: str


def _load_rows(path: Path) -> list[Any]:
    """Refuses a syntactically valid but non-list payload with a named
    error, the same guard every sibling detector's own `_load_rows` holds
    (task 358/359's fix, applied here from the start)."""
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_milestones(path: Path | None = None) -> list[Milestone]:
    rows = _load_rows(path or DEFAULT_MILESTONES_FIXTURE)
    return [
        Milestone(
            number=r["number"], title=r["title"], state=r["state"],
            description=r.get("description") or "",
            updated_at=_parse_ts(r["updated_at"]), url=r["url"],
        )
        for r in rows
    ]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [
        PullRequest(number=r["number"], title=r["title"], state=r["state"], merged=r["merged"], url=r["url"])
        for r in rows
    ]


def _find_pull(number: int, pulls: list[PullRequest]) -> PullRequest | None:
    for pr in pulls:
        if pr.number == number:
            return pr
    return None


def _confidence_for(updated_at: datetime, *, now: datetime) -> float:
    age_hours = (now - updated_at).total_seconds() / 3600.0
    return 0.85 if age_hours >= _EDIT_GRACE_WINDOW_HOURS else 0.55


def compute_gaps(
    milestones: list[Milestone], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A milestone with no description at all
    is never examined -- it claims nothing about a second record, so
    there is no seam to weigh, the identical "not an invite at all"
    exclusion `milestone-claims-unfixed-issue.compute_gaps` already makes
    for a description-free milestone."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for m in sorted(milestones, key=lambda m: m.number):
        if not m.description:
            continue

        numbers = _claimed_pr_numbers(m.description)
        if not numbers:
            continue

        # dict.fromkeys dedupes, order-preserving: a description naming
        # the same #N twice via two different claim verbs must not
        # produce two identical GapCandidates that tie each other out of
        # rank()'s SEPARATION_MARGIN (task 442).
        for n in dict.fromkeys(numbers):
            pr = _find_pull(n, pulls)
            if pr is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-pr-not-found-milestone-{m.number}-{n}",
                    headline=f"Milestone #{m.number} claims #{n} shipped, which doesn't exist",
                    detail=f"'{m.description}' ({m.url}) claims #{n} shipped, but no such PR "
                           f"exists in this repo. No seam here (see milestone-body-dangling-"
                           f"reference).",
                    confidence=0.0,
                    evidence=[m.url],
                ))
                continue

            if pr.merged:
                excluded.append(GapCandidate(
                    slug=f"claim-true-milestone-{m.number}-{n}",
                    headline=f"Milestone #{m.number}'s claim about #{n} holds",
                    detail=f"'{m.description}' ({m.url}) claims #{n} ('{pr.title}') shipped; "
                           f"the PR is merged. No seam here.",
                    confidence=0.0,
                    evidence=[m.url, pr.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"milestone-claims-unmerged-pr-{m.number}-{n}",
                headline=f"Milestone #{m.number} claims #{n} shipped, but #{n} never merged",
                detail=(
                    f"Milestone #{m.number}'s description ('{m.description}', {m.url}) claims "
                    f"#{n} ('{pr.title}') shipped; the PR's real state is '{pr.state}', "
                    f"merged={pr.merged}."
                ),
                confidence=_confidence_for(m.updated_at, now=now),
                evidence=[m.url, pr.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    milestones_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest
    WIP marker this recipe carries until the Hand's gateway carries a
    live `ListMilestones`/`ListPullRequests` read for a connected account
    and these two loaders are swapped for real reads. The detection logic
    does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    milestones = load_milestones(milestones_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(milestones, pulls, now=now)
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
