"""The ninety-second real seam recipe: an issue or pull request's own
OPENING BODY names a real "milestone #N" claim phrase, but the named
milestone is not actually closed.

The one surface the claims-open-milestone family had never grown a leg
for. `readme-claims-open-milestone`, `release-claims-open-milestone`,
`tweet-claims-open-milestone`, `mention-claims-open-milestone`,
`milestone-claims-open-milestone`, `review-comment-claims-open-milestone`,
`slack-message-claims-open-milestone`, and `linear-comment-claims-open-
milestone` all already check the identical claim grammar against eight
other text surfaces -- but none of them ever reads an issue or pull
request's own OPENING BODY, the exact surface `issue-body-dangling-
reference` (the twenty-fourth real recipe) already proved was the single
most common place a stray `#N` gets typed in this town's own history, for
the dangling-reference leg of this family only. That recipe never checked
the milestone-claim leg against the same surface; `issue-comment-claims-
open-milestone` (the fifty-ninth) checks an issue/PR's ordinary TIMELINE
COMMENTS, a related but genuinely distinct GitHub-native surface (a
comment on the thread, not the issue/PR's own description) -- so an
issue or PR body naming "milestone #N shipped" has never been checked
against the milestone tracker's real state anywhere in this engine until
now.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`issues.json`,
`pulls.json`, the identical shape `issue-body-dangling-reference` already
established for this exact surface) plus `milestones.json`, shaped like
what `ListIssues`, `ListPullRequests`, and `ListMilestones` would actually
return. All three scopes already sit on `SCOPES.md`'s cleared oath table
-- this recipe asks Arcade for nothing new, and unlike `issue-comment-
claims-open-milestone`'s own honest WIP marker (no live "list issue/PR
comments" tool exists on the-hand gateway today), `ListIssues` and
`ListPullRequests` are both real, live, read-only tools on the-hand
gateway already -- this recipe carries `"source": "fixture"` only because
CONTRIBUTING.md's MOCK ONLY law holds for every recipe on the day it
merges, not because the underlying scope itself is unavailable.

Deliberately reuses `seam_engine.milestone_claims.claimed_milestone_numbers`
verbatim -- the same shared grammar every other `*-claims-open-milestone`
sibling already imports from there -- rather than a ninth independently
retyped copy of the identical pattern. Also reuses the exact `Issue`/
`PullRequest` dataclass shape and `load_issues`/`load_pulls` loaders
`issue-body-dangling-reference` already established for this surface,
rather than a second, independently drifting copy of the same two
loaders.

The seam: a "milestone #N" claim phrase inside an issue or PR's own
opening body names a milestone by number -- "this also ships milestone
#6201 while we're in here", "closes out milestone #6203 too". If that
milestone does not exist at all, it is excluded here, named not hidden
-- that broken reference is `issue-body-dangling-reference`'s own seam,
not this one's (that recipe already watches bare `#N` references against
the issue/PR number space specifically; a `milestone #N` claim phrase
names a different number space entirely, so the two never collide on the
same candidate). If it exists and is closed, the claim was simply true --
excluded, named not hidden. A body with no "milestone #N" claim phrase at
all is never examined -- it claims nothing about a second record, so
there is no seam to weigh, the identical exclusion `issue-comment-claims-
open-milestone.compute_gaps` already makes for a claim-free comment,
applied here to a claim-free body.

Confidence is age-gated off the record's own `updated_at`, mirroring
`issue-body-dangling-reference`'s and `issue-comment-claims-open-
milestone`'s identical reasoning rather than `readme-claims-open-
milestone`'s flat 0.85: an issue or PR body, like a timeline comment or a
milestone description, is a text surface its own author can still edit at
any time, so a fresh claim earns the same 24-hour grace window every
sibling editable-text recipe in this engine already uses before being
scored as a confirmed gap.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "issue_body_claims_open_milestone"
DEFAULT_ISSUES_FIXTURE = _FIXTURE_DIR / "issues.json"
DEFAULT_PULLS_FIXTURE = _FIXTURE_DIR / "pulls.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# A dangling claim inside a body touched less than this many hours ago is
# not yet scored as a confirmed gap -- it may simply not have been fixed
# yet. Same 24-hour shape issue-body-dangling-reference's and
# issue-comment-claims-open-milestone's own age-gates already use.
_EDIT_GRACE_WINDOW_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _load_rows(path: Path) -> list[Any]:
    """Refuses a syntactically valid but non-list payload with a named
    error, the same guard every sibling detector's own `_load_rows`
    holds."""
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


@dataclass
class Issue:
    number: int
    title: str
    state: str
    body: str
    updated_at: datetime
    url: str


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    body: str
    updated_at: datetime
    url: str


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    url: str


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [
        Issue(
            number=r["number"], title=r["title"], state=r["state"], body=r.get("body") or "",
            updated_at=_parse_ts(r["updated_at"]), url=r["url"],
        )
        for r in rows
    ]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [
        PullRequest(
            number=r["number"], title=r["title"], state=r["state"], body=r.get("body") or "",
            updated_at=_parse_ts(r["updated_at"]), url=r["url"],
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


def _confidence_for(updated_at: datetime, *, now: datetime) -> float:
    age_hours = (now - updated_at).total_seconds() / 3600.0
    return 0.85 if age_hours >= _EDIT_GRACE_WINDOW_HOURS else 0.55


def compute_gaps(
    issues: list[Issue], pulls: list[PullRequest], milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A body with no "milestone #N" claim
    phrase at all is never examined -- it claims nothing about a second
    record, so there is no seam to weigh. Both issues and pull requests
    are scanned as sources (either can claim a milestone shipped in its
    own opening body)."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    _SOURCE_LABEL = {"issue": "Issue", "pr": "PR"}

    def _scan(source_kind: str, number: int, body: str, updated_at: datetime, url: str) -> None:
        label = _SOURCE_LABEL[source_kind]
        if not body:
            return

        numbers = _claimed_milestone_numbers(body)
        if not numbers:
            return

        # dict.fromkeys dedupes, order-preserving: a body naming the same
        # "milestone #N" twice must not produce two identical
        # GapCandidates that tie each other out of rank()'s
        # SEPARATION_MARGIN (task 442's fix, applied here from the start).
        for n in dict.fromkeys(numbers):
            milestone = _find_milestone(n, milestones)
            if milestone is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-not-found-{source_kind}-{number}-{n}",
                    headline=f"{label} #{number} claims milestone #{n}, which doesn't exist",
                    detail=f"'{body}' ({url}) claims milestone #{n} shipped, but no such "
                           f"milestone exists in this repo. No seam here (a broken reference "
                           f"is issue-body-dangling-reference's own seam).",
                    confidence=0.0,
                    evidence=[url],
                ))
                continue

            if milestone.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{source_kind}-{number}-{n}",
                    headline=f"{label} #{number}'s claim about milestone #{n} holds",
                    detail=f"'{body}' ({url}) claims milestone #{n} ('{milestone.title}') "
                           f"shipped; the milestone is closed. No seam here.",
                    confidence=0.0,
                    evidence=[url, milestone.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"issue-body-claims-open-milestone-{source_kind}-{number}-{n}",
                headline=f"{label} #{number} claims milestone #{n} shipped, but it's still open",
                detail=(
                    f"{label} #{number}'s own body ('{body}', {url}) claims milestone #{n} "
                    f"('{milestone.title}') shipped; its real state is '{milestone.state}'. "
                    f"Milestones carry no auto-close trigger of their own regardless -- this "
                    f"claim was never going to resolve itself."
                ),
                confidence=_confidence_for(updated_at, now=now),
                evidence=[url, milestone.url],
            ))

    for issue in issues:
        _scan("issue", issue.number, issue.body, issue.updated_at, issue.url)
    for pull in pulls:
        _scan("pr", pull.number, pull.body, pull.updated_at, pull.url)

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    issues_path: Path | None = None,
    pulls_path: Path | None = None,
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest
    MOCK ONLY marker CONTRIBUTING.md requires of every recipe on the day
    it merges, not a claim the underlying scopes are unavailable
    (`ListIssues`/`ListPullRequests`/`ListMilestones` are all live,
    cleared tools already)."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    issues = load_issues(issues_path)
    pulls = load_pulls(pulls_path)
    milestones = load_milestones(milestones_path)
    surfaced, excluded = compute_gaps(issues, pulls, milestones, now=now)
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
