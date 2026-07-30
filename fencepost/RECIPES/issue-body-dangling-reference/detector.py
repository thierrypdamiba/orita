"""The twenty-fourth real seam recipe: an issue or pull request's own body
counts on a `#N` that isn't actually there.

`RECIPES/dangling-issue-reference/` (task 368) watches this exact seam
inside a commit message; `RECIPES/mention-dangling-reference/` (task 388)
watches it inside a mortal's X mention; `RECIPES/release-note-dangling-
reference/` (task 401) watches it inside a release body. None of the three
ever checked the single most common place a stray `#N` actually gets typed
in this town's own history: an issue or pull request's own description.
Every mortal and every god routinely writes "related to #N" / "see #N for
context" / "same root cause as #N" directly into an issue or PR body, and
GitHub renders that `#N` as a clickable link with no check it resolves to
anything at all -- the identical blind spot every sibling in this family
already proved, on the one text surface none of them had looked at yet.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`issues.json`,
`pulls.json`), shaped like what `ListIssues` and `ListPullRequests` would
actually return -- each row carrying its own `body` and `updated_at`, the
two fields this recipe actually needs (no other recipe's fixture for
these two scopes needed `body` before now). Both scopes already sit on
`SCOPES.md`'s cleared oath table -- this recipe asks Arcade for nothing
new.

The seam: `#N` inside an issue OR a pull request's own body is checked
against BOTH the issue list and the PR list, the same "one shared number
sequence" discipline `dangling-issue-reference` already established --
checking only one would misfire on a perfectly good reference to a merged
PR from inside an issue, or to a closed issue from inside a PR. A
cross-repo `owner/repo#N` reference is never even extracted as a
candidate -- that names a different repo's own number space on purpose.
This recipe imports `seam_engine.references.referenced_numbers` rather
than writing a fourth copy of the same extraction regex -- the identical
"one law, not a fourth copy of it" discipline tasks 389/390/393/394/396/400
already paid for on five other shared patterns in this engine.

Confidence is the one place this recipe reasons differently than its three
siblings, deliberately, not by oversight: `dangling-issue-reference`,
`mention-dangling-reference`, and `release-note-dangling-reference` each
carry a FLAT score, because a commit message, someone else's tweet, and a
published release note are all permanent the instant they exist -- there
is no "give it a chance to get fixed" grace period that means anything for
any of them. An issue or PR body is the one text surface in this family
that is NOT like that: GitHub lets the author edit it at any time, and a
typo'd `#N` gets corrected in the ordinary course of triage constantly.
So this recipe age-gates off the record's own `updated_at`, the same
`_ANNOUNCE_WINDOW_HOURS`-shaped 24-hour grace period `issue-closed-not-
tweeted`/`milestone-closed-not-tweeted`/`merged-pr-not-tweeted` already use
for an analogous "may simply not have caught up yet" reason: a dangling
reference sitting in a body that was touched less than 24h ago scores 0.55
(still might get fixed any minute); one that has sat, uncorrected, for at
least 24h since the record's own last update scores 0.85 (nobody is coming
back to fix it).
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
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "issue_body_dangling_reference" / "issues.json"
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "issue_body_dangling_reference" / "pulls.json"

# A dangling reference in a body touched less than this many hours ago is
# not yet scored as a confirmed gap -- it may simply not have been fixed
# yet. Same 24-hour shape as every "may not have caught up yet" grace
# window elsewhere in this engine (issue-closed-not-tweeted and its
# siblings), applied here for an analogous but distinct reason: unlike
# those recipes' "hasn't tweeted yet," this one's reason is "hasn't been
# edited to fix the typo yet" -- both are the same shape of "give it a
# beat before calling it a real gap."
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


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [
        Issue(
            number=r["number"], title=r["title"], state=r["state"], body=r["body"],
            updated_at=_parse_ts(r["updated_at"]), url=r["url"],
        )
        for r in rows
    ]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [
        PullRequest(
            number=r["number"], title=r["title"], state=r["state"], body=r["body"],
            updated_at=_parse_ts(r["updated_at"]), url=r["url"],
        )
        for r in rows
    ]


def _confidence_for(updated_at: datetime, *, now: datetime) -> float:
    age_hours = (now - updated_at).total_seconds() / 3600.0
    return 0.85 if age_hours >= _EDIT_GRACE_WINDOW_HOURS else 0.55


def compute_gaps(
    issues: list[Issue], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A record with no `#N` reference at all
    is never examined -- it claims nothing about a second record, so there
    is no seam to weigh, the identical "not an invite at all" exclusion
    `dangling-issue-reference.compute_gaps` already makes for a
    reference-free commit. Both issues and pull requests are scanned as
    sources (either can carry a dangling reference in its own body), and
    both lists are checked as the target number space (a reference from
    either source can validly resolve against either list)."""
    known_numbers = {i.number for i in issues} | {p.number for p in pulls}

    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    _SOURCE_LABEL = {"issue": "Issue", "pr": "PR"}

    def _scan(source_kind: str, number: int, body: str, updated_at: datetime, url: str) -> None:
        label = _SOURCE_LABEL[source_kind]
        for n in _referenced_numbers(body):
            if n in known_numbers:
                excluded.append(GapCandidate(
                    slug=f"issue-body-ref-matched-{source_kind}-{number}-{n}",
                    headline=f"{label} #{number}'s reference to #{n} matches a real issue or PR",
                    detail=f"'{body}' ({url}) references #{n}; a real issue or pull request "
                           f"#{n} exists in this repo. No seam here.",
                    confidence=0.0,
                    evidence=[url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"issue-body-dangling-reference-{source_kind}-{number}-{n}",
                headline=f"{label} #{number} references #{n}, but no issue or PR #{n} exists here",
                detail=f"'{body}' ({url}) references #{n}; ListIssues + ListPullRequests found "
                       f"no issue or pull request with that number in this repo. Likely a typo, "
                       f"a reference to something deleted, or a number meant for a different "
                       f"repo, sitting in a body anyone can still edit but nobody has.",
                confidence=_confidence_for(updated_at, now=now),
                evidence=[url],
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
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListIssues`/`ListPullRequests` read for a connected account and these
    two loaders are swapped for real reads. The detection logic does not
    change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    issues = load_issues(issues_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(issues, pulls, now=now)
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
