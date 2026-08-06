"""Forty-seventh real seam recipe: a mortal's own X mention of the
connected account invokes a real GitHub closing keyword against an issue
("fixes #N" / "closes #N" / "resolves #N", both tenses), but the issue
never actually closed.

The mention-side leg the claims-unfixed-issue family had never grown.
`readme-claims-unfixed-issue`, `release-claims-unfixed-issue`,
`milestone-claims-unfixed-issue`, and `tweet-claims-unfixed-issue` already
cover every text surface the town itself controls -- its own README, its
own release notes, its own milestone descriptions, its own tweets -- but
all four only ever check a claim the town made ABOUT itself. This recipe
checks the identical closing-keyword grammar against the one inbound
surface none of those four ever read: a stranger's own mention of the
account, sourced from `GetMyMentions` rather than `GetUserTweets` -- the
same tweet-vs-mention split `mention-dangling-reference` (the eighteenth
real recipe) already opened against `own-tweet-dangling-reference` (the
forty-second), applied here to a claims-X seam instead of a dangling-
reference one.

Deliberately reuses `seam_engine.closing_keywords.CLOSING_KEYWORD_RE`
verbatim -- the same shared grammar `tweet-claims-unfixed-issue`,
`release-claims-unfixed-issue`, `commit-closes-keyword-issue-still-open`,
and `issue-closed-never-released` already import from there (task 394
centralized what had been three independently retyped copies) -- rather
than a fifth copy of the identical pattern drifting apart from the other
four. "closing #N" (present participle, Iron Rule #8's own prescribed safe
form) never matches either tense here either, same as everywhere else this
grammar is used.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`mentions.json`,
`issues.json`), shaped like what `GetMyMentions` and `ListIssues` would
actually return. Both scopes already sit on `SCOPES.md`'s cleared oath
table (`GetMyMentions` since founding, first used by mention-dangling-
reference; `ListIssues` used by nearly every recipe in this engine). No
new scope is asked for anywhere in this recipe.

The seam: a closing-keyword phrase inside a mortal's own mention names an
issue by number. If that issue does not exist at all, it is excluded here
-- that broken reference is `dangling-issue-reference`'s/`mention-
dangling-reference`'s own seam, not this one's. If it exists and is
closed, the claim was simply true -- excluded, named not hidden. If it
exists and is still open, a stranger's own permanent public claim about
the project, sitting on X, already disagrees with GitHub's own record --
and nothing on either platform ever compares the two.

Confidence is age-gated by the mention's own `created_at`, mirroring
`tweet-claims-unfixed-issue`'s identical reasoning -- not a discounted
copy of it. A claim checked within 24 hours of posting might still be a
race (the real fix landing moments after the mention went out) rather
than a settled overclaim. Unlike `mention-dangling-reference`'s own FLAT,
deliberately-lower-than-its-tweet-twin's score (which discounts a
mortal's own uncertain grasp of the repo's number space -- they may simply
be numbering a different tracker in their own head), the check this
recipe makes is objective: the claimed issue's own live `state` field,
verified against `ListIssues`, not the mortal's guess. A mortal cannot be
"wrong about the number space" and still land a real, existing issue
number attached to a real closing-keyword claim -- the uncertainty
`mention-dangling-reference` discounts for does not apply here, so this
recipe holds `tweet-claims-unfixed-issue`'s own 0.85/0.5 bar exactly, no
independently re-reasoned number.
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
DEFAULT_MENTIONS_FIXTURE = _HERE.parents[1] / "fixtures" / "mention_claims_unfixed_issue" / "mentions.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "mention_claims_unfixed_issue" / "issues.json"

# A claim checked within this window of the mention's own created_at may
# just be a race rather than a genuine, settled public overclaim -- the
# identical bar tweet-claims-unfixed-issue holds itself to.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Mention:
    id: str
    author: str
    text: str
    created_at: datetime
    url: str


@dataclass
class Issue:
    number: int
    title: str
    state: str
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_mentions(path: Path | None = None) -> list[Mention]:
    rows = _load_rows(path or DEFAULT_MENTIONS_FIXTURE)
    return [
        Mention(
            id=r["id"], author=r["author"], text=r["text"],
            created_at=_parse_ts(r["created_at"]), url=r["url"],
        )
        for r in rows
    ]


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [
        Issue(number=r["number"], title=r["title"], state=r["state"], url=r["url"])
        for r in rows
    ]


def _claimed_issue_numbers(text: str) -> list[int]:
    return [int(n) for n in CLOSING_KEYWORD_RE.findall(text)]


def _find_issue(number: int, issues: list[Issue]) -> Issue | None:
    for issue in issues:
        if issue.number == number:
            return issue
    return None


def compute_gaps(
    mentions: list[Mention], issues: list[Issue], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed issue is excluded, named not hidden, the
    moment it names no real issue at all, or the issue it names is already
    closed -- everything left over (a fix-claim the issue tracker itself
    contradicts) is surfaced, aged into a confidence score rank() can
    honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for mention in mentions:
        numbers = _claimed_issue_numbers(mention.text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{mention.id}",
                headline=f"@{mention.author}'s mention {mention.id} names no fixes/closes/resolves issue claim",
                detail=f"'{mention.text}' carries no closing-keyword reference. No seam here.",
                confidence=0.0,
                evidence=[mention.url],
            ))
            continue

        seen: set[int] = set()
        for number in numbers:
            if number in seen:
                continue
            seen.add(number)

            issue = _find_issue(number, issues)
            if issue is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-issue-not-found-{mention.id}-{number}",
                    headline=f"@{mention.author}'s mention {mention.id} claims fixing #{number}, which doesn't exist",
                    detail=f"'{mention.text}' claims #{number} fixed, but no such issue exists. No seam here (see dangling-issue-reference/mention-dangling-reference).",
                    confidence=0.0,
                    evidence=[mention.url],
                ))
                continue

            if issue.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{mention.id}-{number}",
                    headline=f"@{mention.author}'s mention {mention.id}'s claim about #{number} holds",
                    detail=f"'{mention.text}' claims #{number} fixed; issue #{number} ('{issue.title}') is closed. No seam here.",
                    confidence=0.0,
                    evidence=[mention.url, issue.url],
                ))
                continue

            age_hours = (now - mention.created_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"mention-claims-unfixed-issue-{mention.id}-{number}",
                headline=f"@{mention.author}'s mention {mention.id} claims #{number} fixed, but #{number} is still open",
                detail=(
                    f"'{mention.text}' (posted {mention.created_at.isoformat()}, "
                    f"{age_hours:.1f}h ago) claims #{number} ('{issue.title}') fixed; "
                    f"the issue's real state is '{issue.state}'."
                ),
                confidence=confidence,
                evidence=[mention.url, issue.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    mentions_path: Path | None = None,
    issues_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `GetMyMentions`/`ListIssues` read for a connected account and these two
    loaders are swapped for real calls. The detection logic does not
    change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    mentions = load_mentions(mentions_path)
    issues = load_issues(issues_path)
    surfaced, excluded = compute_gaps(mentions, issues, now=now)
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
