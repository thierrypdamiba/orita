"""Twenty-eighth real seam recipe: a tweet from the connected X account
invokes a real GitHub closing keyword against an issue ("fixes #N" /
"closes #N" / "resolves #N", both tenses), but the issue never actually
closed.

The tweet-side twin of `release-claims-unfixed-issue` (task 382), which
watches the identical single-record-makes-a-permanent-false-claim shape
but inside a release's own body. This recipe watches the same shape
against the OTHER place the town makes a public, unedited "fixed it"
claim -- a tweet, mirroring `tweet-claims-unmerged-pr` (task 450, the
tweet-side twin of `release-claims-unmerged-pr`) one leg over: that recipe
covers the PR-claim half of the release-vs-tweet split this family
already has for PRs; this recipe closes the matching issue-claim half.

Deliberately reuses `seam_engine.closing_keywords.CLOSING_KEYWORD_RE`
verbatim -- the same shared grammar `release-claims-unfixed-issue`,
`commit-closes-keyword-issue-still-open`, and `issue-closed-never-
released` already import from there (task 394 centralized what had been
three independently retyped copies) -- rather than a fourth copy of the
identical pattern drifting apart from the other three. "closing #N"
(present participle, Iron Rule #8's own prescribed safe form) never
matches either tense here either, same as everywhere else this grammar is
used.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`tweets.json`,
`issues.json`), shaped like what `GetUserTweets` and `ListIssues` would
actually return. Both scopes already sit on `SCOPES.md`'s cleared oath
table -- this recipe asks Arcade for nothing new.

The seam: a closing-keyword phrase inside a tweet's own text names an
issue by number. If that issue does not exist at all, it is excluded here
-- that broken reference is `dangling-issue-reference`'s/`mention-
dangling-reference`'s own seam. If it exists and is closed, the claim was
simply true -- excluded, named not hidden. If it exists and is still
open, the tweet's own permanent public record disagrees with reality:
that is the gap.

Confidence is age-gated by the tweet's own `created_at`, mirroring
`release-claims-unfixed-issue`'s and `tweet-claims-unmerged-pr`'s
identical reasoning: a claim checked within a few hours of posting might
still be a race (tweet posted moments before the real fix lands) rather
than a settled overclaim.
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
DEFAULT_TWEETS_FIXTURE = _HERE.parents[1] / "fixtures" / "tweet_claims_unfixed_issue" / "tweets.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "tweet_claims_unfixed_issue" / "issues.json"

# A claim checked within this window of the tweet's own created_at may just
# be a race rather than a genuine, settled public overclaim.
_STALE_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Tweet:
    id: str
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


def load_tweets(path: Path | None = None) -> list[Tweet]:
    rows = _load_rows(path or DEFAULT_TWEETS_FIXTURE)
    return [
        Tweet(id=r["id"], text=r["text"], created_at=_parse_ts(r["created_at"]), url=r["url"])
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
    tweets: list[Tweet], issues: list[Issue], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed issue is excluded, named not hidden, the
    moment it names no real issue at all, or the issue it names is already
    closed -- everything left over (a fix-claim the issue tracker itself
    contradicts) is surfaced, aged into a confidence score rank() can
    honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for tweet in tweets:
        numbers = _claimed_issue_numbers(tweet.text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{tweet.id}",
                headline=f"Tweet {tweet.id} names no fixes/closes/resolves issue claim",
                detail=f"'{tweet.text}' carries no closing-keyword reference. No seam here.",
                confidence=0.0,
                evidence=[tweet.url],
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
                    slug=f"claimed-issue-not-found-{tweet.id}-{number}",
                    headline=f"Tweet {tweet.id} claims fixing #{number}, which doesn't exist",
                    detail=f"'{tweet.text}' claims #{number} fixed, but no such issue exists. No seam here (see dangling-issue-reference).",
                    confidence=0.0,
                    evidence=[tweet.url],
                ))
                continue

            if issue.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{tweet.id}-{number}",
                    headline=f"Tweet {tweet.id}'s claim about #{number} holds",
                    detail=f"'{tweet.text}' claims #{number} fixed; issue #{number} ('{issue.title}') is closed. No seam here.",
                    confidence=0.0,
                    evidence=[tweet.url, issue.url],
                ))
                continue

            age_hours = (now - tweet.created_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"tweet-claims-unfixed-issue-{tweet.id}-{number}",
                headline=f"Tweet {tweet.id} claims #{number} fixed, but #{number} is still open",
                detail=(
                    f"'{tweet.text}' (posted {tweet.created_at.isoformat()}, "
                    f"{age_hours:.1f}h ago) claims #{number} ('{issue.title}') fixed; "
                    f"the issue's real state is '{issue.state}'."
                ),
                confidence=confidence,
                evidence=[tweet.url, issue.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    tweets_path: Path | None = None,
    issues_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    tweet read and these loaders are swapped for real calls. The detection
    logic does not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    tweets = load_tweets(tweets_path)
    issues = load_issues(issues_path)
    surfaced, excluded = compute_gaps(tweets, issues, now=now)
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
