"""The ninety-first real seam recipe (ROADMAP.md #876): a pull request is
locked as resolved, but never actually closed or merged.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads one local fixture file
(`pulls.json`), shaped like what `ListPullRequests`/`GetPullRequest` would
return -- GitHub's real PR object already carries `locked` and
`active_lock_reason` alongside `state`, the identical fields its own issue
object carries, because a pull request IS an issue under GitHub's own REST
numbering and locking machinery (`GetPullRequest`'s own JSON is issues-
shaped for exactly this reason). Both scopes already sit on `SCOPES.md`'s
cleared oath table under the `github` row -- this recipe asks Arcade for
nothing new.

This is the PR-side twin of `locked-resolved-issue-still-open` (task 596,
the sixty-fourth real recipe): the identical field pair, `locked` and its
own `active_lock_reason`, checked against `state`, this time on a pull
request's own record instead of an issue's. `locked-resolved-issue-still-
open`'s own docstring was built for issues only -- it never named or
excluded the PR side, and nothing about GitHub's Lock API
(`PUT .../lock` with `lock_reason: resolved`) is issue-specific: it works
identically on a PR's own conversation, because a PR's conversation
thread and an issue's conversation thread are the same underlying GitHub
object as far as locking is concerned. Locking a PR's conversation and
actually merging or closing the PR it belongs to are two independent
actions -- a maintainer, or a bot, can set a PR's `active_lock_reason` to
`"resolved"` while the PR itself sits open the whole time, exactly the
same way `locked-resolved-issue-still-open` already established for
issues. Nothing on GitHub's side ever compares the two -- there is no
auto-close, no auto-merge, wired to a lock reason, the same "no forcing
function, only a human notices" shape the `*-still-open` family already
established for other field pairs, this time reached through the
identical `locked`/`active_lock_reason` pair rather than a new one.
Reading `ListPullRequests`/`GetPullRequest` once already carries both
halves of the promise; no second toolkit, no cross-account join, is
needed to see it -- it simply never gets compared to itself.

This is not `unblocked-pr-still-open`'s seam (a PR's own body naming a
"blocked by #N" marker that has since resolved) -- no prose marker is
parsed here at all, the identical distinction `locked-resolved-issue-
still-open`'s own docstring already drew against the claims-X and
dangling-reference grids. It shares only the general *shape* of
`commit-closes-keyword-issue-closed-not-planned` -- a single record's own
two fields disagreeing with each other, read off one list, no second
source needed -- but watches `locked`/`active_lock_reason` against
`state`, the exact pair `locked-resolved-issue-still-open` already reads,
carried onto the PR object it also happens to sit on.

The claim stays narrow on purpose, the same no-grading law every sibling
holds: this recipe never claims anyone forgot, dropped the ball, or did
anything wrong -- a maintainer may have locked the PR's thread the moment
they posted the resolution, fully intending to merge or close it next,
and simply navigated away; a bot might lock on a schedule independent of
whoever would eventually merge or close it. It claims only the narrow,
provable fact that two fields on the same record disagree: GitHub's own
lock reason says "resolved," and GitHub's own state field says "open."

Only `active_lock_reason == "resolved"` is treated as a claim about the
PR's own resolution at all -- "off-topic," "spam," and "too heated" are
excluded outright, named not hidden, because none of them says anything
about whether the underlying PR is done; locking for those reasons while
the PR stays open is not a contradiction, it is simply what locking for
that reason means. A `locked` PR with no lock reason recorded at all
(`active_lock_reason` is `None`, a real, valid GitHub state -- older
locks and some direct API calls carry no reason) is excluded too -- no
explicit "resolved" claim was ever made for this recipe to check against
the PR's own state. A PR that is not locked at all is excluded --
nothing to compare. A PR that already reads anything other than `"open"`
is excluded -- unlike an issue, a real GitHub pull request's own `state`
field is not two-valued: `unblocked-pr-still-open` and `duplicate-pr-
still-open` (the current PR-fixture convention this recipe follows, per
both of their own `_RESOLVED_STATES = ("merged", "closed")` checks) both
already treat a PR's `state` as reading `"merged"` for a merged PR and
`"closed"` for one closed without merging, two distinct terminal values
rather than a single `"closed"` plus a separate boolean. Whichever of the
two a PR has already reached, and whichever order locking and reaching it
happened in, the two fields already agree -- no seam here. A record with
`locked == False` but a non-null `active_lock_reason` is excluded too, as
malformed, not guessed into either bucket -- GitHub's own API never
produces that combination for real, the identical guard `locked-resolved-
issue-still-open`'s own detector already holds.

There is no `locked_at` timestamp on a real GitHub pull request object
either -- nothing records the instant `active_lock_reason` was set.
`updated_at` is the closest real signal GitHub actually exposes (it moves
whenever the PR's own metadata changes, including a lock), so confidence
is age-gated on how long `updated_at` has sat still while the
contradiction holds, mirroring `locked-resolved-issue-still-open`'s own
identical reasoning for its own missing `locked_at`, and every
`*-still-open` sibling's own 24-hour bar rather than inventing a new
number.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "locked_resolved_pr_still_open" / "pulls.json"

# The one lock reason that itself asserts the underlying PR is settled.
# "off-topic", "spam", and "too heated" say nothing about resolution, so
# they are never compared against `state` at all. Identical to
# `locked-resolved-issue-still-open`'s own `_RESOLVED_REASON`.
_RESOLVED_REASON = "resolved"

# A PR locked-as-resolved under this age may simply not have been merged
# or closed yet by the same human who just locked it -- matches every
# other *-still-open sibling's own 24h bar.
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
class PullRequest:
    number: int
    title: str
    state: str
    locked: bool
    active_lock_reason: str | None
    updated_at: datetime
    url: str


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [
        PullRequest(
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
    pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. Every PR is judged independently: not locked, locked
    for a non-resolution reason, locked with no reason at all, already
    merged or closed, or malformed are all excluded named, not hidden; an
    open PR locked as resolved is surfaced, aged by how long `updated_at`
    has sat still."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for pull in sorted(pulls, key=lambda p: p.number):
        if not pull.locked:
            if pull.active_lock_reason is not None:
                excluded.append(GapCandidate(
                    slug=f"malformed-lock-{pull.number}",
                    headline=f"PR #{pull.number} carries a lock reason but reads unlocked",
                    detail=(
                        f"'{pull.title}' ({pull.url}) reads locked=False with "
                        f"active_lock_reason={pull.active_lock_reason!r} -- a combination GitHub's "
                        "own API never produces for real. A malformed record, not an unresolved seam."
                    ),
                    confidence=0.0,
                    evidence=[pull.url],
                ))
                continue
            excluded.append(GapCandidate(
                slug=f"not-locked-{pull.number}",
                headline=f"PR #{pull.number} is not locked",
                detail=f"'{pull.title}' ({pull.url}) reads locked=False. Nothing to compare -- no seam here.",
                confidence=0.0,
                evidence=[pull.url],
            ))
            continue

        if pull.active_lock_reason is None:
            excluded.append(GapCandidate(
                slug=f"no-lock-reason-{pull.number}",
                headline=f"PR #{pull.number} is locked with no reason recorded",
                detail=(
                    f"'{pull.title}' ({pull.url}) is locked but carries no active_lock_reason at "
                    "all -- a real, valid GitHub state (older locks and some direct API calls carry "
                    "no reason). No explicit resolution claim was ever made for this recipe to check "
                    "against the PR's own state."
                ),
                confidence=0.0,
                evidence=[pull.url],
            ))
            continue

        if pull.active_lock_reason != _RESOLVED_REASON:
            excluded.append(GapCandidate(
                slug=f"non-resolution-lock-reason-{pull.number}",
                headline=(
                    f"PR #{pull.number} is locked for a reason other than resolution "
                    f"({pull.active_lock_reason!r})"
                ),
                detail=(
                    f"'{pull.title}' ({pull.url}) is locked with active_lock_reason="
                    f"{pull.active_lock_reason!r}, not {_RESOLVED_REASON!r} -- that reason makes no "
                    "claim about whether the underlying PR is done, so its open state is not a "
                    "contradiction."
                ),
                confidence=0.0,
                evidence=[pull.url],
            ))
            continue

        if pull.state != "open":
            excluded.append(GapCandidate(
                slug=f"already-resolved-{pull.number}",
                headline=f"PR #{pull.number} is locked as resolved and already {pull.state}",
                detail=(
                    f"'{pull.title}' ({pull.url}) reads state={pull.state!r} with "
                    "active_lock_reason='resolved'. Whichever route it reached (merged, or closed "
                    "without merging) and whichever order locking and that happened in, the two "
                    "fields already agree -- no seam here."
                ),
                confidence=0.0,
                evidence=[pull.url],
            ))
            continue

        idle_hours = (now - pull.updated_at).total_seconds() / 3600.0
        confidence = 0.85 if idle_hours >= _STALE_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"locked-resolved-pr-still-open-{pull.number}",
            headline=f"PR #{pull.number} is locked as resolved, but still reads open",
            detail=(
                f"'{pull.title}' ({pull.url}) carries active_lock_reason='resolved' -- GitHub's own "
                f"record of a maintainer's claim the matter is settled -- but state={pull.state!r}. "
                f"Last touched {pull.updated_at.isoformat()} ({idle_hours:.1f}h ago). Locking a "
                "PR's conversation and merging or closing the PR itself are two separate GitHub "
                "actions; nothing on GitHub's side ever compares them."
            ),
            confidence=confidence,
            evidence=[pull.url],
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
    `ListPullRequests`/`GetPullRequest` read and this one loader is
    swapped for a real read. The detection logic does not change when
    that happens."""
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
