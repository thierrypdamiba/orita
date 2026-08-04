"""The forty-fifth real seam recipe: a milestone's own description names a
real GitHub closing keyword against an issue ("fixes #N" / "closes #N" /
"resolves #N", both tenses), but the named issue is still open.

The issue leg of the claims-X family, applied to the one text surface it
had never reached. README, a release body, and a tweet each already
carry all three claims-X legs -- unfixed-issue (`readme-claims-unfixed-
issue`, `release-claims-unfixed-issue`, `tweet-claims-unfixed-issue`),
unmerged-pr, and open-milestone -- but a milestone's own `description`
field, already read for DANGLING references by `milestone-body-dangling-
reference` (task 504/511), had never been checked for this different,
sibling shape: not "does #N exist at all" but "this text claims #N is
FIXED, and it is not." `milestone-closed-issue-still-open` and
`milestone-closed-pr-still-open` check a genuinely different mechanism --
the milestone's own `state` FLAG against its issue membership -- never a
keyword phrase sitting inside its free-text description.

Deliberately reuses `seam_engine.closing_keywords.CLOSING_KEYWORD_RE`
verbatim -- the same shared grammar `commit-closes-keyword-issue-still-
open`, `issue-closed-never-released`, `release-claims-unfixed-issue`, and
`readme-claims-unfixed-issue` already import from there -- rather than a
sixth independently-retyped copy of the identical pattern.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`milestones.json`,
`issues.json`), shaped like what `ListMilestones` and `ListIssues` would
actually return. Both scopes already sit on `SCOPES.md`'s cleared oath
table -- this recipe asks Arcade for nothing new.

The seam: a closing-keyword phrase inside a milestone's own description
names an issue by number. If that issue does not exist at all, it is
excluded here -- a broken reference is `milestone-body-dangling-
reference`'s own seam, not this one's. If it exists and is closed, the
claim was simply true -- excluded, named not hidden. If it exists and is
still open, the milestone's own free-text description disagrees with the
issue tracker's real state: that is the gap.

Confidence is age-gated off the milestone's own `updated_at`, mirroring
`milestone-body-dangling-reference`'s own reasoning rather than
`readme-claims-unfixed-issue`'s flat 0.85: a `GetFileContents` read of
README returns CURRENT text with no per-line edit timestamp to weigh, but
a milestone object carries a real `updated_at` -- and, like an issue or PR
body, its description is a text surface its author can still edit at any
time. A claim first written moments ago may simply not have caught up
with reality yet; the same 24-hour grace window every sibling editable-
text recipe in this engine already uses. A milestone with no description
at all is excluded outright -- there is no claim to have broken.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "milestone_claims_unfixed_issue"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"
DEFAULT_ISSUES_FIXTURE = _FIXTURE_DIR / "issues.json"

# A dangling claim inside a description touched less than this many hours
# ago is not yet scored as a confirmed gap -- it may simply not have been
# fixed yet. Same 24-hour shape as milestone-body-dangling-reference's own
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
class Issue:
    number: int
    title: str
    state: str
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


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [
        Issue(number=r["number"], title=r["title"], state=r["state"], url=r["url"])
        for r in rows
    ]


def _claimed_issue_numbers(description: str) -> list[int]:
    return [int(n) for n in CLOSING_KEYWORD_RE.findall(description)]


def _find_issue(number: int, issues: list[Issue]) -> Issue | None:
    for issue in issues:
        if issue.number == number:
            return issue
    return None


def _confidence_for(updated_at: datetime, *, now: datetime) -> float:
    age_hours = (now - updated_at).total_seconds() / 3600.0
    return 0.85 if age_hours >= _EDIT_GRACE_WINDOW_HOURS else 0.55


def compute_gaps(
    milestones: list[Milestone], issues: list[Issue], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A milestone with no description at all
    is never examined -- it claims nothing about a second record, so
    there is no seam to weigh, the identical "not an invite at all"
    exclusion `milestone-body-dangling-reference.compute_gaps` already
    makes for a description-free milestone."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for m in sorted(milestones, key=lambda m: m.number):
        if not m.description:
            continue

        numbers = _claimed_issue_numbers(m.description)
        if not numbers:
            continue

        # dict.fromkeys dedupes, order-preserving: a description naming
        # the same #N twice must not produce two identical GapCandidates
        # that tie each other out of rank()'s SEPARATION_MARGIN (task 442).
        for n in dict.fromkeys(numbers):
            issue = _find_issue(n, issues)
            if issue is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-issue-not-found-milestone-{m.number}-{n}",
                    headline=f"Milestone #{m.number} claims fixing #{n}, which doesn't exist",
                    detail=f"'{m.description}' ({m.url}) claims #{n} fixed, but no such issue "
                           f"exists in this repo. No seam here (see milestone-body-dangling-"
                           f"reference).",
                    confidence=0.0,
                    evidence=[m.url],
                ))
                continue

            if issue.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-milestone-{m.number}-{n}",
                    headline=f"Milestone #{m.number}'s claim about #{n} holds",
                    detail=f"'{m.description}' ({m.url}) claims #{n} ('{issue.title}') fixed; "
                           f"the issue is closed. No seam here.",
                    confidence=0.0,
                    evidence=[m.url, issue.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"milestone-claims-unfixed-issue-{m.number}-{n}",
                headline=f"Milestone #{m.number} claims #{n} fixed, but #{n} is still open",
                detail=(
                    f"Milestone #{m.number}'s description ('{m.description}', {m.url}) claims "
                    f"#{n} ('{issue.title}') fixed; the issue's real state is '{issue.state}'."
                ),
                confidence=_confidence_for(m.updated_at, now=now),
                evidence=[m.url, issue.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    milestones_path: Path | None = None,
    issues_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest
    WIP marker this recipe carries until the Hand's gateway carries a
    live `ListMilestones`/`ListIssues` read for a connected account and
    these two loaders are swapped for real reads. The detection logic
    does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    milestones = load_milestones(milestones_path)
    issues = load_issues(issues_path)
    surfaced, excluded = compute_gaps(milestones, issues, now=now)
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
