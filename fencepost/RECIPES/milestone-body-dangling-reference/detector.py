"""The forty-first real seam recipe, and the fifth and final leg of the
dangling-reference family: a milestone's own description counts on a
`#N` that isn't actually there.

`RECIPES/dangling-issue-reference/` (task 368) watches this exact seam
inside a commit message; `RECIPES/mention-dangling-reference/` (task 388)
watches it inside a mortal's X mention; `RECIPES/release-note-dangling-
reference/` (task 401) watches it inside a release body;
`RECIPES/issue-body-dangling-reference/` (task 504, formerly self-
described as "the fourth and final leg") watches it inside an issue or
pull request's own body. None of the four ever read the one other place
GitHub itself invites exactly this same mistake: a milestone's own
`description` field. Real milestone objects returned by `ListMilestones`
carry a `description` string exactly like an issue or PR body, and
mortals and gods alike routinely write "tracks #501, #502" or "blocked on
#N until that lands" directly into it -- GitHub renders every `#N` there
as a clickable link with zero validation that it resolves to anything,
the identical blind spot every sibling in this family already proved, one
text surface further.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads three local fixture files (`milestones.json`,
`issues.json`, `pulls.json`), shaped like what `ListMilestones`,
`ListIssues`, and `ListPullRequests` would actually return. All three
scopes already sit on `SCOPES.md`'s cleared oath table -- this recipe
asks Arcade for nothing new.

The seam: `#N` inside a milestone's own description is checked against
BOTH the issue list and the PR list, the same "one shared number
sequence" discipline `dangling-issue-reference` and `issue-body-dangling-
reference` already established -- checking only one would misfire on a
perfectly good reference to a merged PR sitting inside a milestone's own
notes. A cross-repo `owner/repo#N` reference is never even extracted as a
candidate -- that names a different repo's own number space on purpose.
This recipe imports `seam_engine.references.referenced_numbers` rather
than writing a fifth copy of the same extraction regex -- the identical
"one law, not a fifth copy of it" discipline this whole family already
pays for.

Confidence mirrors `issue-body-dangling-reference` exactly, for the same
reason: a milestone's `description`, like an issue or PR body, is a text
surface its author can edit at any time -- unlike a permanent commit,
someone else's tweet, or a published release note, there is a real
"may simply not have caught up yet" grace period that means something
here. A dangling reference inside a description touched less than 24h ago
scores 0.55 (still might get fixed any minute); one that has sat,
uncorrected, for at least 24h since the milestone's own `updated_at`
scores 0.85 (nobody is coming back to fix it). A milestone with no
description at all (`null` or empty) is excluded outright -- there is no
claim to have broken.
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
DEFAULT_MILESTONES_FIXTURE = _HERE.parents[1] / "fixtures" / "milestone_body_dangling_reference" / "milestones.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "milestone_body_dangling_reference" / "issues.json"
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "milestone_body_dangling_reference" / "pulls.json"

# A dangling reference in a description touched less than this many hours
# ago is not yet scored as a confirmed gap -- it may simply not have been
# fixed yet. Same 24-hour shape as issue-body-dangling-reference's own
# _EDIT_GRACE_WINDOW_HOURS, applied here for the identical reason: a
# milestone's description is a text surface its author can still edit at
# any time.
_EDIT_GRACE_WINDOW_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _load_rows(path: Path) -> list[Any]:
    """Refuses a syntactically valid but non-list payload with a named
    error, the same guard every sibling detector's own `_load_rows` holds
    (task 358/359's fix, applied here from the start)."""
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


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
    url: str


@dataclass
class PullRequest:
    number: int
    url: str


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
    return [Issue(number=r["number"], url=r["url"]) for r in rows]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [PullRequest(number=r["number"], url=r["url"]) for r in rows]


def _confidence_for(updated_at: datetime, *, now: datetime) -> float:
    age_hours = (now - updated_at).total_seconds() / 3600.0
    return 0.85 if age_hours >= _EDIT_GRACE_WINDOW_HOURS else 0.55


def compute_gaps(
    milestones: list[Milestone], issues: list[Issue], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A milestone with no description at all
    is never examined -- it claims nothing about a second record, so
    there is no seam to weigh, the identical "not an invite at all"
    exclusion `dangling-issue-reference.compute_gaps` already makes for a
    reference-free commit."""
    known_numbers = {i.number for i in issues} | {p.number for p in pulls}

    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for m in sorted(milestones, key=lambda m: m.number):
        if not m.description:
            continue

        # dict.fromkeys dedupes, order-preserving: a description naming
        # the same #N twice must not produce two identical GapCandidates
        # that tie each other out of rank()'s SEPARATION_MARGIN (task 442).
        for n in dict.fromkeys(_referenced_numbers(m.description)):
            if n in known_numbers:
                excluded.append(GapCandidate(
                    slug=f"milestone-body-ref-matched-{m.number}-{n}",
                    headline=f"Milestone #{m.number}'s reference to #{n} matches a real issue or PR",
                    detail=f"'{m.description}' ({m.url}) references #{n}; a real issue or pull "
                           f"request #{n} exists in this repo. No seam here.",
                    confidence=0.0,
                    evidence=[m.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"milestone-body-dangling-reference-{m.number}-{n}",
                headline=f"Milestone #{m.number} references #{n}, but no issue or PR #{n} exists here",
                detail=f"'{m.description}' ({m.url}) references #{n}; ListMilestones + ListIssues "
                       f"+ ListPullRequests found no issue or pull request with that number in this "
                       f"repo. Likely a typo, a reference to something deleted, or a number meant "
                       f"for a different repo, sitting in a description anyone can still edit but "
                       f"nobody has.",
                confidence=_confidence_for(m.updated_at, now=now),
                evidence=[m.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    milestones_path: Path | None = None,
    issues_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest
    WIP marker this recipe carries until the Hand's gateway carries a
    live `ListMilestones`/`ListIssues`/`ListPullRequests` read for a
    connected account and these three loaders are swapped for real reads.
    The detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    milestones = load_milestones(milestones_path)
    issues = load_issues(issues_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(milestones, issues, pulls, now=now)
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
