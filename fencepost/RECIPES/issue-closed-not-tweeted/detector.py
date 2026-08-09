"""The twenty-first real seam recipe: a GitHub issue closes -- a bug fixed,
a feature delivered -- but no tweet from the connected X account ever names
its number.

The issue-side twin of `release-not-tweeted` (task 110),
`milestone-closed-not-tweeted` (task 390), and `merged-pr-not-tweeted`
(task 398) -- the last leg of the same "shipped work never announced"
family, completing it across all three GitHub artifact types that can close
without ever being wrapped in a release or a milestone. An issue closing is
its own real, user-facing event -- a bug fixed, a feature delivered -- with
no second GitHub record it has to acquire before it becomes announceable,
the identical shape `merged-pr-not-tweeted`'s own docstring already made
for a merged PR.

GitHub+X, the same cross-toolkit shape `release-not-tweeted` established
first. Both scopes already sit on `SCOPES.md`'s cleared oath table under
their own toolkit rows (`ListIssues`, `GetUserTweets`) -- no new scope
wiring anywhere in this recipe, matching the last several recipes' own
"reuse, don't widen" discipline.

Matching is by exact issue-number substring (`#<N>`), not title-keyword
overlap, mirroring `merged-pr-not-tweeted`'s own "exact tag, not fuzzy
matching" doctrine, itself mirroring `release-not-tweeted`'s: an issue's
number either appears in a tweet's text, on its own, digit-bounded, or it
does not. The same collision class `release-not-tweeted` fixed once
already (a short tag matching inside a longer one) exists here in numeral
form -- `#12` must not be considered a mention of issue #12 just because
"123" is a substring of a tweet naming the unrelated, longer "#123" -- so
the match is digit-boundary-guarded on both sides, not bare substring
containment.

An issue that is still open is not in scope at all -- there is nothing
shipped yet to announce, the same exclusion `issue-closed-never-released`
already draws at its own front door.

Confidence is age-gated, matching every sibling in this family exactly (no
reason to weigh an issue differently than a release, a milestone, or a PR
-- the same 24-hour "may simply not have tweeted yet" grace window
applies): a close with no matching tweet within `_ANNOUNCE_WINDOW_HOURS`
is not yet a gap; past the window with still no match, it is.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "issue_closed_not_tweeted" / "issues.json"
DEFAULT_TWEETS_FIXTURE = _HERE.parents[1] / "fixtures" / "issue_closed_not_tweeted" / "tweets.json"

# A close announced within this window of closing is not yet a gap --
# auto-post lag or a human simply hasn't tweeted yet. Matches every sibling
# in this family (release-not-tweeted, milestone-closed-not-tweeted,
# merged-pr-not-tweeted) exactly.
_ANNOUNCE_WINDOW_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class ClosedIssue:
    number: int
    title: str
    state: str
    closed_at: datetime | None
    url: str


@dataclass
class Tweet:
    id: str
    text: str
    created_at: datetime
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_closed_issues(path: Path | None = None) -> list[ClosedIssue]:
    """Only rows whose `state` reads `closed` (with a real `closed_at`)
    become candidates at all -- an open issue has nothing shipped yet to
    announce, the same front-door exclusion every closed-issue recipe
    before this one draws."""
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [
        ClosedIssue(
            number=r["number"], title=r["title"], state=r["state"],
            closed_at=_parse_ts(r["closed_at"]) if r.get("closed_at") else None,
            url=r["url"],
        )
        for r in rows
        if r.get("state") == "closed" and r.get("closed_at")
    ]


def load_tweets(path: Path | None = None) -> list[Tweet]:
    rows = _load_rows(path or DEFAULT_TWEETS_FIXTURE)
    return [
        Tweet(id=r["id"], text=r["text"], created_at=_parse_ts(r["created_at"]), url=r["url"])
        for r in rows
    ]


def _find_announcing_tweet(number: int, tweets: list[Tweet]) -> Tweet | None:
    # Digit-boundary match on both sides -- "#12" must not be considered
    # mentioned by a tweet naming the unrelated, longer "#123", the same
    # short-inside-long collision release-not-tweeted's own tag matcher (and
    # merged-pr-not-tweeted's own numeral-form copy) already guards against.
    pattern = re.compile(r"(?<!\d)#" + re.escape(str(number)) + r"(?!\d)")
    for tweet in tweets:
        if pattern.search(tweet.text):
            return tweet
    return None


def compute_gaps(
    issues: list[ClosedIssue], tweets: list[Tweet], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape every recipe before this
    one returns. A closed issue is excluded, named not hidden, the moment a
    tweet's text names its number; everything left over (never mentioned)
    is surfaced, aged into a confidence score `rank()` can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for issue in issues:
        tweet = _find_announcing_tweet(issue.number, tweets)
        if tweet is not None:
            excluded.append(GapCandidate(
                slug=f"issue-tweeted-{issue.number}",
                headline=f"#{issue.number} was tweeted",
                detail=f"'{issue.title}' (#{issue.number}) is named in {tweet.url}. No seam here.",
                confidence=0.0,
                evidence=[issue.url, tweet.url],
            ))
            continue

        if issue.closed_at is None:
            raise ValueError(
                f"compute_gaps(): issue #{issue.number} reached the surfaced-gap "
                "branch with no closed_at -- load_closed_issues() should have "
                "filtered it out before this call; ruff S101 (task 622)."
            )
        age_hours = (now - issue.closed_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _ANNOUNCE_WINDOW_HOURS else 0.55
        surfaced.append(GapCandidate(
            slug=f"issue-closed-not-tweeted-{issue.number}",
            headline=f"#{issue.number} closed, never tweeted",
            detail=(
                f"'{issue.title}' (#{issue.number}) closed {issue.closed_at.isoformat()} "
                f"({age_hours:.1f}h ago); no tweet from the connected account names it."
            ),
            confidence=confidence,
            evidence=[issue.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    issues_path: Path | None = None,
    tweets_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every recipe before
    this one -- `source: "fixture"` is the honest WIP marker this recipe
    carries until the Hand's gateway carries a live issue-list scope wired
    into the real daily run and these two loaders are swapped for real
    reads. The detection logic does not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    issues = load_closed_issues(issues_path)
    tweets = load_tweets(tweets_path)
    surfaced, excluded = compute_gaps(issues, tweets, now=now)
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
