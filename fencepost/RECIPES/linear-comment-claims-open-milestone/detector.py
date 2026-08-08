"""The seventieth real seam recipe: a Linear issue comment claims a
milestone shipped ("milestone #N"), but the named milestone is not
actually closed.

The Linear source's second `claims-X` leg, alongside `linear-comment-
claims-unfixed-issue` (task 600, the sixty-eighth real recipe). That
recipe proved the first Linear-side claim leg -- an issue comment's
closing-keyword claim against the issue tracker's own state -- and left
the milestone-claim leg open. `slack-message-claims-open-milestone` (task
601, the sixty-ninth) already proved the identical milestone-claim shape
for the Slack channel-message surface `slack-message-claims-unfixed-
issue` opened; this recipe is that same check applied to the Linear
issue-comment surface `linear-comment-claims-unfixed-issue` opened, not a
new pattern independently invented for the occasion. A third leg,
`linear-comment-claims-unmerged-pr`, remains open for a future hour --
this recipe closes one cell of that grid, not all three.

With this recipe shipped, the claims-X grid (ten sources -- mention,
tweet, issue-comment, review-comment, milestone, readme, release, commit,
slack-message, linear-comment -- times three targets -- open-milestone,
unfixed-issue, unmerged-pr -- twenty-four filled and structurally-
unfillable cells at task 599, thirty cells total once slack/linear joined
as sources) has exactly two genuinely open cells left:
`slack-message-claims-unmerged-pr` and `linear-comment-claims-unmerged-
pr`. `commit-claims-unfixed-issue` and `commit-claims-unmerged-pr` remain
the two structurally-unfillable cells task 599's own history already
named -- `commit-closes-keyword-issue-still-open` and `commit-closes-
keyword-pr-still-open` already cover that identical semantic space under
a different recipe name, so filling those two cells a second time under
the `claims-X` name would be the same fact asserted twice, not a new one.

Reuses `seam_engine.milestone_claims.claimed_milestone_numbers` verbatim
-- the same shared "milestone #N" grammar `milestone-closed-never-
released`, `release-claims-open-milestone`, `milestone-closed-not-
tweeted`, `mention-claims-open-milestone`, `milestone-claims-open-
milestone`, `commit-claims-open-milestone`, `review-comment-claims-open-
milestone`, `issue-comment-claims-open-milestone`, `readme-claims-open-
milestone`, `tweet-claims-open-milestone`, and `slack-message-
claims-open-milestone` already import from there (task 389 centralized
what had been independently retyped copies) -- rather than a twelfth copy
of the identical pattern drifting apart from the rest.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`comments.json`,
`milestones.json`), shaped like what a real `SearchIssueComments`/
`ListMilestones` read would return. `ListMilestones` is already cleared
on `SCOPES.md`'s oath table under the `github` row, used by every
milestone-claim recipe already in this engine. `SearchIssueComments` is
the same scope `linear-comment-claims-unfixed-issue` (task 600) already
cleared through `seam_engine.recipes.validate_recipe`'s oath (it matches
the allowed `Search*` prefix and contains none of the forbidden write
words); this recipe asks for nothing new, and `linear+github` is not a
new toolkit pair either -- `linear-comment-claims-unfixed-issue` already
proposed it. See `SCOPES.md`'s own WIP note for the `linear` toolkit: the-
hand gateway holds a real, live, upstream `arcade-linear` connection
today, but exposes zero Linear-capable tools on the live gateway -- the
identical "connected upstream, not wired into the gateway" shape
`SCOPES.md`'s Gmail/Calendar and Slack WIP notes already document for two
other toolkits.

The seam: a `milestone #N` claim phrase inside a Linear issue comment
names a milestone by number. If that milestone does not exist at all, it
is excluded here -- that broken reference belongs to a future Linear-side
dangling-reference recipe, not this one. If it exists and is closed, the
claim was simply true -- excluded, named not hidden. If it exists and is
still open, a comment already sitting on a Linear issue disagrees with
GitHub's own record, and nothing on either platform ever compares the
two. This never grades or blames whoever left the comment --
CONTRIBUTING.md's "No grading, ever" law, same as every recipe in this
engine: the headline names the gap between two records, not a person's
error.

Confidence is age-gated by the comment's own `created_at`, holding
`slack-message-claims-open-milestone`'s own 0.85/0.5 bar exactly -- a
comment posted on a Linear issue is exactly as durable and readable-later
as a Slack channel message, a tweet, or a mention once posted, "posted
once and stands", not an editable review comment (`review-comment-
claims-open-milestone`'s own 0.55/0.85 bar does not apply here, and this
recipe deliberately does not re-derive it). A claim checked within 24
hours of posting might still be a race (the milestone actually closing
out moments after the comment went out) rather than a settled overclaim.
The check itself is objective: the claimed milestone's own live `state`
field, verified against `ListMilestones`, not a guess about which
tracker the commenter meant -- the same reasoning `slack-message-claims-
open-milestone`'s own docstring already gives for holding `mention-
claims-open-milestone`'s/`tweet-claims-open-milestone`'s bar exactly, no
independently re-reasoned number.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "linear_comment_claims_open_milestone"
DEFAULT_COMMENTS_FIXTURE = _FIXTURE_DIR / "comments.json"
DEFAULT_MILESTONES_FIXTURE = _FIXTURE_DIR / "milestones.json"

# A claim checked within this window of the comment's own created_at may
# just be a race rather than a genuine, settled public overclaim -- the
# identical bar slack-message-claims-open-milestone/linear-comment-
# claims-unfixed-issue hold themselves to.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Comment:
    id: str
    issue_identifier: str
    author: str
    text: str
    created_at: datetime
    url: str


@dataclass
class Milestone:
    number: int
    title: str
    state: str
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_comments(path: Path | None = None) -> list[Comment]:
    rows = _load_rows(path or DEFAULT_COMMENTS_FIXTURE)
    return [
        Comment(
            id=r["id"], issue_identifier=r["issue_identifier"], author=r["author"],
            text=r["text"], created_at=_parse_ts(r["ts"]), url=r["url"],
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


def compute_gaps(
    comments: list[Comment], milestones: list[Milestone], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed milestone is excluded, named not hidden,
    the moment it names no real milestone at all, or the milestone it
    names is already closed -- everything left over (a shipped-it claim
    the milestone tracker itself contradicts) is surfaced, aged into a
    confidence score rank() can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for comment in comments:
        numbers = _claimed_milestone_numbers(comment.text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{comment.id}",
                headline=f"{comment.issue_identifier}'s comment {comment.id} names no milestone claim",
                detail=f"'{comment.text}' carries no 'milestone #N' claim phrase. No seam here.",
                confidence=0.0,
                evidence=[comment.url],
            ))
            continue

        seen: set[int] = set()
        for number in numbers:
            if number in seen:
                continue
            seen.add(number)

            milestone = _find_milestone(number, milestones)
            if milestone is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-milestone-not-found-{comment.id}-{number}",
                    headline=f"{comment.issue_identifier}'s comment {comment.id} claims milestone #{number}, which doesn't exist",
                    detail=f"'{comment.text}' claims milestone #{number} shipped, but no such milestone exists. No seam here.",
                    confidence=0.0,
                    evidence=[comment.url],
                ))
                continue

            if milestone.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{comment.id}-{number}",
                    headline=f"{comment.issue_identifier}'s comment {comment.id}'s claim about milestone #{number} holds",
                    detail=f"'{comment.text}' claims milestone #{number} ('{milestone.title}') shipped; the milestone is closed. No seam here.",
                    confidence=0.0,
                    evidence=[comment.url, milestone.url],
                ))
                continue

            age_hours = (now - comment.created_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"linear-comment-claims-open-milestone-{comment.id}-{number}",
                headline=f"{comment.issue_identifier}'s comment {comment.id} claims milestone #{number} shipped, but it's still open",
                detail=(
                    f"'{comment.text}' (posted {comment.created_at.isoformat()} on "
                    f"{comment.issue_identifier}, {age_hours:.1f}h ago) claims milestone #{number} "
                    f"('{milestone.title}') shipped; the milestone's real state is "
                    f"'{milestone.state}'."
                ),
                confidence=confidence,
                evidence=[comment.url, milestone.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    comments_path: Path | None = None,
    milestones_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the-hand's gateway carries a live
    `SearchIssueComments`/`ListMilestones` read for a connected Linear
    workspace and these two loaders are swapped for real calls. The
    detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    comments = load_comments(comments_path)
    milestones = load_milestones(milestones_path)
    surfaced, excluded = compute_gaps(comments, milestones, now=now)
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
