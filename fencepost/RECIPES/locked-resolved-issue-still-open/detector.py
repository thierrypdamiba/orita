"""The sixty-fourth real seam recipe: an issue is locked as resolved, but
never actually closed.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads one local fixture file
(`issues.json`), shaped like what `ListIssues` would return -- GitHub's
real issue object already carries `locked` and `active_lock_reason`
alongside `state`. That scope already sits on SCOPES.md's cleared oath
table under the `github` row -- this recipe asks Arcade for nothing new.

The seam it watches sits on a field pair none of the sixty-three prior
recipes has ever read: `locked` and its own `active_lock_reason`. Locking
a GitHub conversation and closing the issue it belongs to are two
independent actions -- GitHub's own UI offers a single combined "Close as
resolved and lock" workflow that happens to fire both, but its API also
exposes each one on its own (`PUT .../lock` with `lock_reason: resolved`
touches nothing about `state`; a repository's own automation, a bot, or a
maintainer clicking only "Lock conversation" in the sidebar can set
`active_lock_reason: "resolved"` while the issue itself sits open the
whole time). When that happens, the record now carries its own
contradiction in plain sight: a maintainer's own explicit claim that the
matter is settled (`active_lock_reason == "resolved"`), sitting right next
to the one field that says otherwise (`state == "open"`). Nothing on
GitHub's side ever compares the two -- there is no auto-close wired to a
lock reason, the same "no forcing function, only a human notices" shape
`milestone-complete-still-open` and the `*-still-open` family already
established for other field pairs. Reading `ListIssues` once already
carries both halves of the promise; no second toolkit, no cross-account
join, is needed to see it -- it simply never gets compared to itself.

This is a genuinely different axis from every family this repo has
already saturated. It is not the claims-X grid (no claim phrase, no body
text parsed at all -- two structured fields compared against each other,
the same "structured field against structured fact" shape
`merged-pr-requested-reviewer-never-reviewed` established, but entirely
within one record instead of across two). It is not the dangling-
reference grid (no `#N` reference read anywhere). It is not a checklist
recipe (`issue-checklist-complete-still-open`, `pr-checklist-complete-
still-open` -- no task-list syntax parsed here). It shares only the
general *shape* of `commit-closes-keyword-issue-closed-not-planned` (task
594) -- a single record's own two fields disagreeing with each other,
read off one list, no second source needed -- but watches `locked`/
`active_lock_reason` against `state`, a pair that recipe never reads,
rather than `state_reason` against a commit's own closing-keyword claim.

The claim stays narrow on purpose, the same no-grading law every sibling
holds: this recipe never claims anyone forgot, dropped the ball, or did
anything wrong -- a maintainer may have locked the thread the moment they
posted the resolution, fully intending to close it next, and simply
navigated away; a bot might lock on a schedule independent of whoever
would eventually close it. It claims only the narrow, provable fact that
two fields on the same record disagree: GitHub's own lock reason says
"resolved," and GitHub's own state field says "open."

Only `active_lock_reason == "resolved"` is treated as a claim about the
issue's own resolution at all -- "off-topic," "spam," and "too heated" are
excluded outright, named not hidden, because none of them says anything
about whether the underlying issue is done; locking for those reasons
while the issue stays open is not a contradiction, it is simply what
locking for that reason means. A `locked` issue with no lock reason
recorded at all (`active_lock_reason` is `None`, a real, valid GitHub
state -- older locks and some direct API calls carry no reason) is
excluded too -- no explicit "resolved" claim was ever made for this
recipe to check against the issue's own state. An issue that is not
locked at all is excluded -- nothing to compare. A closed issue is
excluded -- whichever order locking and closing happened in, the two
fields already agree. A record with `locked == False` but a non-null
`active_lock_reason` is excluded as malformed, not guessed into either
bucket -- GitHub's own API never produces that combination for real.

There is no `locked_at` timestamp on a real GitHub issue object -- nothing
records the instant `active_lock_reason` was set. `updated_at` is the
closest real signal GitHub actually exposes (it moves whenever the issue's
own metadata changes, including a lock), so confidence is age-gated on how
long `updated_at` has sat still while the contradiction holds, mirroring
`milestone-complete-still-open`'s own identical reasoning for its own
missing `completed_at` field, and every `*-still-open` sibling's own
24-hour bar rather than inventing a new number.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "locked_resolved_issue_still_open" / "issues.json"

# The one lock reason that itself asserts the underlying issue is settled.
# "off-topic", "spam", and "too heated" say nothing about resolution, so
# they are never compared against `state` at all.
_RESOLVED_REASON = "resolved"

# An issue locked-as-resolved under this age may simply not have been
# closed yet by the same human who just locked it -- matches every other
# *-still-open sibling's own 24h bar.
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
class Issue:
    number: int
    title: str
    state: str
    locked: bool
    active_lock_reason: str | None
    updated_at: datetime
    url: str


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [
        Issue(
            number=r["number"],
            title=r["title"],
            state=r["state"],
            locked=bool(r.get("locked", False)),
            active_lock_reason=r.get("active_lock_reason"),
            updated_at=_parse_ts(r["updated_at"]),
            url=r["url"],
        )
        for r in rows
    ]


def compute_gaps(
    issues: list[Issue], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. Every issue is judged independently: not locked, locked
    for a non-resolution reason, locked with no reason at all, already
    closed, or malformed are all excluded named, not hidden; an open issue
    locked as resolved is surfaced, aged by how long `updated_at` has sat
    still."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for issue in sorted(issues, key=lambda i: i.number):
        if not issue.locked:
            if issue.active_lock_reason is not None:
                excluded.append(GapCandidate(
                    slug=f"malformed-lock-{issue.number}",
                    headline=f"Issue #{issue.number} carries a lock reason but reads unlocked",
                    detail=(
                        f"'{issue.title}' ({issue.url}) reads locked=False with "
                        f"active_lock_reason={issue.active_lock_reason!r} -- a combination GitHub's "
                        "own API never produces for real. A malformed record, not an unresolved seam."
                    ),
                    confidence=0.0,
                    evidence=[issue.url],
                ))
                continue
            excluded.append(GapCandidate(
                slug=f"not-locked-{issue.number}",
                headline=f"Issue #{issue.number} is not locked",
                detail=f"'{issue.title}' ({issue.url}) reads locked=False. Nothing to compare -- no seam here.",
                confidence=0.0,
                evidence=[issue.url],
            ))
            continue

        if issue.active_lock_reason is None:
            excluded.append(GapCandidate(
                slug=f"no-lock-reason-{issue.number}",
                headline=f"Issue #{issue.number} is locked with no reason recorded",
                detail=(
                    f"'{issue.title}' ({issue.url}) is locked but carries no active_lock_reason at "
                    "all -- a real, valid GitHub state (older locks and some direct API calls carry "
                    "no reason). No explicit resolution claim was ever made for this recipe to check "
                    "against the issue's own state."
                ),
                confidence=0.0,
                evidence=[issue.url],
            ))
            continue

        if issue.active_lock_reason != _RESOLVED_REASON:
            excluded.append(GapCandidate(
                slug=f"non-resolution-lock-reason-{issue.number}",
                headline=(
                    f"Issue #{issue.number} is locked for a reason other than resolution "
                    f"({issue.active_lock_reason!r})"
                ),
                detail=(
                    f"'{issue.title}' ({issue.url}) is locked with active_lock_reason="
                    f"{issue.active_lock_reason!r}, not {_RESOLVED_REASON!r} -- that reason makes no "
                    "claim about whether the underlying issue is done, so its open state is not a "
                    "contradiction."
                ),
                confidence=0.0,
                evidence=[issue.url],
            ))
            continue

        if issue.state != "open":
            excluded.append(GapCandidate(
                slug=f"already-closed-{issue.number}",
                headline=f"Issue #{issue.number} is locked as resolved and already closed",
                detail=(
                    f"'{issue.title}' ({issue.url}) reads state={issue.state!r} with "
                    "active_lock_reason='resolved'. Whichever order locking and closing happened in, "
                    "the two fields already agree -- no seam here."
                ),
                confidence=0.0,
                evidence=[issue.url],
            ))
            continue

        idle_hours = (now - issue.updated_at).total_seconds() / 3600.0
        confidence = 0.85 if idle_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"locked-resolved-issue-still-open-{issue.number}",
            headline=f"Issue #{issue.number} is locked as resolved, but still reads open",
            detail=(
                f"'{issue.title}' ({issue.url}) carries active_lock_reason='resolved' -- GitHub's own "
                f"record of a maintainer's claim the matter is settled -- but state={issue.state!r}. "
                f"Last touched {issue.updated_at.isoformat()} ({idle_hours:.1f}h ago). Locking a "
                "conversation and closing the issue it belongs to are two separate GitHub actions; "
                "nothing on GitHub's side ever compares them."
            ),
            confidence=confidence,
            evidence=[issue.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    issues_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every prior
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListIssues` read and this one loader is swapped for a real read. The
    detection logic does not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    issues = load_issues(issues_path)
    surfaced, excluded = compute_gaps(issues, now=now)
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
