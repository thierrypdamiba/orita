"""Fifth real seam recipe: a contributor thanked in a tweet from the
connected X account, never credited in the repo's own README.

STRATEGY.md's own Growth notes name two worked-example seams in the same
sentence: "a release shipped but never tweeted" (built as
`RECIPES/release-not-tweeted/`, task 110) and "a contributor thanked on X
but missing from the README." Only the first half was ever actually built.
This recipe closes the second half, and is the second CROSS-TOOLKIT recipe
(X + GitHub) after `release-not-tweeted`.

Read-only in spirit, MOCK ONLY in practice, same as every recipe before
this one: this module only ever reads two local fixture files (`tweets.json`,
`readme.json`), shaped like what `GetUserTweets` and a read-only
`GetFileContents` call on this repo's own README would actually return.
`GetUserTweets` already sits on SCOPES.md's cleared X row;
`GetFileContents` is new but clears the same oath everything else does
(starts with `Get`, no forbidden word inside it) -- it reads a repo file,
nothing more.

Not every tweet naming a contributor is a "thanks" -- an ordinary
`@mention` with no thanks-shaped language is not a candidate at all, the
same "no fuzzy matching to misfire on" discipline `release-not-tweeted`
already holds for its exact-tag match. `_THANKS_RE` requires "thanks" or
"thank you" followed (loosely) by an `@handle` in the same tweet before that
handle is even considered.

Confidence is age-gated, mirroring `release-not-tweeted`'s own reasoning,
but with a genuinely different number: `_CREDIT_WINDOW_HOURS = 72.0`, not
24. Crediting a README is a slower, more deliberate edit than posting an
announcement tweet -- a real maintainer cadence difference, not a
copy-pasted constant with the label changed.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate
from seam_engine.thanks import THANKS_RE

_HERE = Path(__file__).resolve().parent
DEFAULT_TWEETS_FIXTURE = _HERE.parents[1] / "fixtures" / "contributor_thanked_not_credited" / "tweets.json"
DEFAULT_README_FIXTURE = _HERE.parents[1] / "fixtures" / "contributor_thanked_not_credited" / "readme.json"

# A handle thanked but not yet credited within this window is not yet a
# gap -- a human maintainer may simply not have gotten to the README edit.
# Longer than release-not-tweeted's 24h: crediting a doc lags an
# announcement tweet more than announcing a release lags shipping it.
_CREDIT_WINDOW_HOURS = 72.0

# Requires "thank(s)" or "thank you", loosely followed by an @handle, in the
# same tweet -- a bare @mention with no thanks-shaped language never
# matches, so it never becomes a candidate at all. Shared with
# `readme-credited-not-thanked/detector.py`'s own inverse check via
# `seam_engine.thanks` (task 396) -- see that module for why the two used
# to carry independent, textually-identical copies.
_THANKS_RE = THANKS_RE


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Tweet:
    id: str
    text: str
    created_at: datetime
    url: str


def _load_rows(path: Path) -> list[Any]:
    rows = json.loads(path.read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


def load_tweets(path: Path | None = None) -> list[Tweet]:
    rows = _load_rows(path or DEFAULT_TWEETS_FIXTURE)
    return [
        Tweet(id=r["id"], text=r["text"], created_at=_parse_ts(r["created_at"]), url=r["url"])
        for r in rows
    ]


def load_readme(path: Path | None = None) -> str:
    """Load the whole-file `{"path": ..., "content": ...}` shape a
    `GetFileContents` call returns, refusing a syntactically valid but
    wrong-shaped payload with a named error -- same discipline as every
    other loader in this engine (task 355's `_load_sealed_arg` and its
    seam_engine siblings), applied to a single-object load instead of a
    list one."""
    p = path or DEFAULT_README_FIXTURE
    data = json.loads(p.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{p}: expected a JSON object, got {type(data).__name__}")
    content = data.get("content")
    if not isinstance(content, str):
        raise ValueError(f"{p}: expected a string 'content' field")
    return content


def _thanked_handle(text: str) -> str | None:
    match = _THANKS_RE.search(text)
    return match.group(1) if match else None


def _is_credited(handle: str, readme_content: str) -> bool:
    # A handle can itself contain hyphens ("mortal-fixer"), so a bare `\b`
    # after it is not enough -- `\b` sits between a word char and a hyphen
    # too, which would let "mortal" falsely match inside "@mortal-fixer".
    # The negative lookahead requires the match not be immediately followed
    # by another word char OR hyphen, so only the whole handle matches.
    pattern = re.compile(r"@" + re.escape(handle) + r"(?![\w-])", re.IGNORECASE)
    return bool(pattern.search(readme_content))


def compute_gaps(
    tweets: list[Tweet], readme_content: str, *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every recipe before this
    one. A tweet with no thanks-shaped mention never becomes a candidate at
    all (not even in `excluded` -- there is nothing to name; mirrors
    `dangling-issue-reference`'s "no reference, no candidate" rule, not
    `merged-pr-issue-still-open`'s "name every non-match too" rule, because
    here the non-match is the tweet's own shape, not a comparison that was
    actually attempted). A thanked handle already in the README is named in
    `excluded`, not hidden."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for tweet in tweets:
        handle = _thanked_handle(tweet.text)
        if handle is None:
            continue

        if _is_credited(handle, readme_content):
            excluded.append(GapCandidate(
                slug=f"contributor-credited-{handle}",
                headline=f"@{handle} is already credited",
                detail=f"{tweet.url} thanks @{handle}; the README already names them. No seam here.",
                confidence=0.0,
                evidence=[tweet.url],
            ))
            continue

        age_hours = (now - tweet.created_at).total_seconds() / 3600.0
        confidence = 0.85 if age_hours >= _CREDIT_WINDOW_HOURS else 0.5
        surfaced.append(GapCandidate(
            slug=f"contributor-thanked-not-credited-{handle}",
            headline=f"@{handle} was thanked on X, not yet in the README credits",
            detail=(
                f"{tweet.url} thanked @{handle} {age_hours:.1f}h ago "
                f"({tweet.created_at.isoformat()}); no README entry names them yet."
            ),
            confidence=confidence,
            evidence=[tweet.url],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    tweets_path: Path | None = None,
    readme_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every recipe before
    this one -- `source: "fixture"` is the honest WIP marker until the Hand's
    gateway carries a live `GetFileContents` read and these two loaders are
    swapped for real calls. The detection logic does not change when it
    does."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    tweets = load_tweets(tweets_path)
    readme_content = load_readme(readme_path)
    surfaced, excluded = compute_gaps(tweets, readme_content, now=now)
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
