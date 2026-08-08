"""The sixty-fifth real seam recipe: a pull request's own body already
promises to close an issue, while the pull request itself is still marked
a draft.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads one local fixture file
(`pull_requests.json`), shaped like what `ListPullRequests` would return --
GitHub's real pull-request object already carries both `draft` and `body`
alongside `state`. That scope already sits on SCOPES.md's cleared oath
table under the `github` row -- this recipe asks Arcade for nothing new.

The seam it watches sits on a field none of the sixty-four prior recipes
has ever read: `draft`, a real, structured boolean GitHub's own Pull
Request API returns -- the author's own explicit flag that the work is
not ready to be reviewed or merged yet. Nine recipes already parse a PR or
commit's own prose for a closing keyword ("closes/fixes/resolves #N"),
reusing `seam_engine.closing_keywords.CLOSING_KEYWORD_RE` (the shared,
single source for that grammar) -- but every one of them either reads a
commit message (`commit-closes-keyword-issue-still-open`,
`commit-closes-keyword-pr-still-open`,
`commit-closes-keyword-issue-closed-not-planned`) or requires the PR to
have already merged (`merged-pr-issue-still-open`,
`merged-pr-pr-still-open`) before it looks at the body at all. None of
them ever reads a PR's own body while the PR is still open and unmerged,
and none of them has ever read `draft`. When a PR's own body already
writes "closes #N" while its own `draft` field still reads `true`, the
record carries a real tension in plain sight: the author's own prose
claims a specific, named outcome is coming, while the author's own
structured flag says the work behind that outcome is not ready for anyone
to act on yet. GitHub renders the "will close #N" note on the issue's own
sidebar the identical way whether the linked PR is a draft or not -- a
maintainer skimming the issue sees "a PR will close this" with no
indication the PR is still explicitly marked not-ready. Nothing on
GitHub's side ever compares `draft` to the PR's own body text; the two
fields simply sit next to each other, unreconciled, for as long as the
draft sits open.

This is a genuinely different axis from every family this repo has
already saturated. It is not the claims-X grid (seven external text
surfaces -- readme, release, milestone, tweet, mention, issue comment,
review comment -- crossed with three claim phrases, 21/21 closed): a PR's
own body is not one of those seven surfaces, and this recipe never
crosses the toolkit boundary into X at all. It is not the dangling-
reference grid (nine legs, all asking whether a referenced `#N` target
*exists*): this recipe never looks up the named issue at all, real or
not -- whether #N exists, and whether it is open or closed, is a fact
about a SECOND record this recipe deliberately never reads, the same
"holding only what one call already returns" discipline
`locked-resolved-issue-still-open` established for its own `locked`/
`active_lock_reason` pair. It is not `merged-pr-issue-still-open`'s seam
(that recipe requires `state == "merged"` before it ever reads a body,
and watches whether the referenced issue caught up -- a claim about a
SECOND record); this recipe requires `draft == true` and never advances
past `state != "open"`, so the same PR can never appear in both recipes'
surfaced output. It is not `commit-closes-keyword-issue-still-open`'s
seam either (that reads a commit message, immutable the instant it is
pushed); a PR's own body is mutable right up until the PR closes, so this
recipe's own claim is only ever about the body's LATEST read, not a
permanent record the way a commit message is. It shares only the general
*shape* of `locked-resolved-issue-still-open` and
`commit-closes-keyword-issue-closed-not-planned` -- a single record's own
fields disagreeing with each other, read off one list, no second source
needed -- but watches `draft` against the record's own body text, a pair
neither of those recipes, nor any other, has ever paired.

The claim stays narrow on purpose, the same no-grading law every sibling
holds: this recipe never claims the author did anything wrong, or that
the promise is false. A brand-new draft PR carrying "closes #N" in its
own opening scaffolding is completely ordinary -- plenty of contributors
open a draft with the intended closing keyword already written, exactly
so reviewers can see the target up front while the work is still in
progress. That is not a seam; it is simply what "draft" is for. The gap
only exists once the same tension has sat unresolved for a while with
nothing in the record itself explaining why -- the same "under a day,
maybe nobody's looked yet; a day and more, worth a human's attention"
reasoning the entire `*-still-open` family already leans on, applied here
to a PR that has not been touched, not an issue.

Only a body that GitHub's own closing-keyword grammar actually matches is
treated as a claim at all -- a body that merely mentions the issue number
in passing ("related to #N", "see #N for context") makes no closing
promise, and is excluded, not guessed into either bucket. A `draft` PR
with no body at all (`body` is `None`, a real, valid GitHub state for a
PR opened with an empty description) is excluded the same way, no claim
having been made to check against anything. A PR that is not a draft at
all is excluded outright -- nothing about `draft` to compare against its
own body. A draft PR whose own closing keyword sits on a PR that has
since closed WITHOUT merging is excluded -- the PR itself is dead; its
one-time claim is moot, not a live gap sitting in front of anyone. A
`draft == true` PR whose own `state` reads `"merged"` is excluded as
malformed, not guessed into the surfaced set: GitHub's own API refuses to
merge a pull request while it is still marked draft (the author must
explicitly mark it "ready for review" first, which flips `draft` to
`false` in the same action) -- that combination never occurs for real.

There is no `marked_draft_at` timestamp on a real GitHub pull-request
object -- nothing records the instant `draft` was last set. `updated_at`
is the closest real signal GitHub actually exposes (it moves whenever the
PR's own metadata changes), so confidence is age-gated on how long
`updated_at` has sat still while the tension holds, mirroring
`locked-resolved-issue-still-open`'s own identical reasoning for its
missing `locked_at`, and every `*-still-open` sibling's own 24-hour bar
rather than inventing a new number.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.closing_keywords import closing_keyword_numbers
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_PULL_REQUESTS_FIXTURE = (
    _HERE.parents[1] / "fixtures" / "draft_pr_closes_keyword_issue" / "pull_requests.json"
)

# A draft PR that only just started claiming a closing keyword under this
# age may simply not have been touched again yet -- matches every other
# *-still-open sibling's own 24h bar rather than inventing a new number.
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
    draft: bool
    body: str | None
    updated_at: datetime
    url: str


def load_pull_requests(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULL_REQUESTS_FIXTURE)
    return [
        PullRequest(
            number=r["number"],
            title=r["title"],
            state=r["state"],
            draft=bool(r.get("draft", False)),
            body=r.get("body"),
            updated_at=_parse_ts(r["updated_at"]),
            url=r["url"],
        )
        for r in rows
    ]


def compute_gaps(
    pull_requests: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every prior recipe's
    `compute_gaps`. Every pull request is judged independently: not a
    draft, no closing keyword in its own body, already closed without
    merging, or the malformed draft-and-merged combination are all
    excluded named, not hidden; an open draft PR whose own body already
    claims a closing keyword is surfaced, aged by how long `updated_at`
    has sat still."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for pr in sorted(pull_requests, key=lambda p: p.number):
        if not pr.draft:
            excluded.append(GapCandidate(
                slug=f"not-draft-{pr.number}",
                headline=f"PR #{pr.number} is not a draft",
                detail=(
                    f"'{pr.title}' ({pr.url}) reads draft=False. Nothing to compare against its "
                    "own body -- no seam here."
                ),
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        closing_nums = closing_keyword_numbers(pr.body or "")
        if not closing_nums:
            excluded.append(GapCandidate(
                slug=f"no-closing-keyword-{pr.number}",
                headline=f"Draft PR #{pr.number}'s own body makes no closing-keyword claim",
                detail=(
                    f"'{pr.title}' ({pr.url}) is a draft, but its own body carries no real GitHub "
                    "closing keyword (a bare issue mention like 'related to #N' does not count) -- "
                    "no claim was ever made for this recipe to check against `draft`."
                ),
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        if pr.state == "merged":
            excluded.append(GapCandidate(
                slug=f"malformed-merged-draft-{pr.number}",
                headline=f"PR #{pr.number} reads draft=True and state=merged",
                detail=(
                    f"'{pr.title}' ({pr.url}) reads draft=True with state='merged' -- a combination "
                    "GitHub's own API never produces for real (merging requires marking a draft "
                    "'ready for review' first, which flips draft to False in the same action). A "
                    "malformed record, not an unresolved seam."
                ),
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        if pr.state != "open":
            excluded.append(GapCandidate(
                slug=f"already-closed-{pr.number}",
                headline=f"Draft PR #{pr.number} closed without merging",
                detail=(
                    f"'{pr.title}' ({pr.url}) reads state={pr.state!r} with a closing-keyword claim "
                    "still in its own draft body -- but the PR itself is dead. Its one-time claim is "
                    "moot, not a live gap sitting in front of anyone."
                ),
                confidence=0.0,
                evidence=[pr.url],
            ))
            continue

        idle_hours = (now - pr.updated_at).total_seconds() / 3600.0
        confidence = 0.85 if idle_hours >= _STALE_HOURS else 0.5
        nums = ", ".join(f"#{n}" for n in closing_nums)
        surfaced.append(GapCandidate(
            slug=f"draft-pr-closes-keyword-issue-{pr.number}",
            headline=f"Draft PR #{pr.number}'s own body claims a closing keyword, but it isn't ready",
            detail=(
                f"'{pr.title}' ({pr.url}) still reads draft=True while its own body already promises "
                f"to close {nums} -- GitHub's own author-set flag says the work isn't ready, sitting "
                f"next to the same author's own prose claim that it will resolve something specific. "
                f"Last touched {pr.updated_at.isoformat()} ({idle_hours:.1f}h ago). Nothing on "
                "GitHub's side ever compares `draft` to the PR's own body."
            ),
            confidence=confidence,
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
    `ListPullRequests` read and this one loader is swapped for a real
    read. The detection logic does not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    pull_requests = load_pull_requests(pull_requests_path)
    surfaced, excluded = compute_gaps(pull_requests, now=now)
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
