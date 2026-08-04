"""The forty-second real seam recipe (ROADMAP.md #527): the connected X
account's OWN tweet counts on an issue or pull request that isn't actually
there.

Every leg of the dangling-reference family shipped so far reads a text
surface and checks its `#N` references against the live issue/PR number
space: `dangling-issue-reference` (commit messages), `mention-dangling-
reference` (a MORTAL's own mention of the account), `issue-body-dangling-
reference` (issue/PR bodies), `milestone-body-dangling-reference`
(milestone descriptions), and `release-note-dangling-reference` (release
notes). Five legs, five surfaces -- and not one of them ever reads the
account's OWN outbound tweets, the one surface every cross-toolkit recipe
in this engine (`release-not-tweeted`, `star-milestone-not-announced`,
`tweet-claims-open-milestone` and its two siblings) already treats as a
first-class read. `mention-dangling-reference`'s own docstring drew the
INBOUND/OUTBOUND line explicitly -- "every cross-toolkit recipe shipped so
far reads OUTBOUND signal... this one reads the opposite direction,
INBOUND" -- and then nothing ever came back to close the outbound side of
this specific seam. `tweet-claims-*` already checks whether an outbound
tweet's STATE CLAIM ("shipped", "fixed") matches reality; this recipe asks
a narrower, more mechanical question those three never do: does the bare
`#N` the tweet points at even exist at all?

The seam: GitHub renders `#N` as a clickable link with no check that it
resolves to anything, in any piece of text that carries it -- the same
mechanical fact `dangling-issue-reference` proved for a commit message.
A tweet is the one place this town's own words go out with NO second
edit pass and NO reviewer (a commit gets none either, but a commit is
read only by the town and future contributors; a tweet is public,
permanent, and the town's own front door to a stranger). A typo'd number,
a reference to an issue that was later deleted, or digits meant for a
different repo, sitting live on the account's own timeline pointing at
nothing, is a genuine cross-account confusion: reading only the tweet
never shows the tracker is empty at that number; reading only the
tracker never shows the town's own account already claimed otherwise.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads three local fixture files (`tweets.json`,
`issues.json`, `pulls.json`), shaped like what `GetUserTweets`/`ListIssues`/
`ListPullRequests` would actually return. All three scopes already sit on
`SCOPES.md`'s cleared oath table (`GetUserTweets` since founding,
`ListIssues`/`ListPullRequests` since `dangling-issue-reference`) -- this
recipe asks Arcade for nothing new.

The extraction grammar is not retyped a third time: this module imports
`referenced_numbers` from `seam_engine.references`, the one shared place
that regex lives (task 389's own fix for the second copy drifting apart),
exactly the reuse its own docstring invites for "a third recipe that ever
needs the same #N extraction." GitHub shares one number sequence between
issues and pull requests, so a reference is checked against BOTH lists,
the same law every sibling in this family already holds -- checking only
one would misfire on a perfectly good reference to a merged PR, the exact
crying-wolf failure Ogun's law calls fatal.
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
DEFAULT_TWEETS_FIXTURE = _HERE.parents[1] / "fixtures" / "own_tweet_dangling_reference" / "tweets.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "own_tweet_dangling_reference" / "issues.json"
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "own_tweet_dangling_reference" / "pulls.json"

# Flat 0.8 -- the same score `dangling-issue-reference` gives its own
# commit-sourced twin, deliberately HIGHER than `mention-dangling-
# reference`'s 0.75: a tweet from the connected account, like a commit, is
# authored by the town itself on purpose, following this town's own
# repo-scoped #N convention -- not a stranger's own possibly-different
# numbering scheme in their head. See recipe.json's confidence_notes for
# the full reasoning.
_DANGLING_CONFIDENCE = 0.8


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _load_rows(path: Path) -> list[Any]:
    """Load a whole-file JSON list, refusing a syntactically valid but
    non-list payload with a named error instead of letting it reach a `for`
    loop unmarked. Mirrors every sibling detector's own `_load_rows`."""
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


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


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    url: str


def load_tweets(path: Path | None = None) -> list[Tweet]:
    rows = _load_rows(path or DEFAULT_TWEETS_FIXTURE)
    return [
        Tweet(id=r["id"], text=r["text"], created_at=_parse_ts(r["created_at"]), url=r["url"])
        for r in rows
    ]


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [Issue(number=r["number"], title=r["title"], state=r["state"], url=r["url"]) for r in rows]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [PullRequest(number=r["number"], title=r["title"], state=r["state"], url=r["url"]) for r in rows]


def compute_gaps(
    tweets: list[Tweet], issues: list[Issue], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other detector in
    this engine. A tweet with no `#N` reference at all is not examined --
    it never claims anything about a second record, so there is no seam to
    weigh, the same "not an invite at all" exclusion every sibling in this
    family already makes. `now` is accepted, unused, for interface parity
    with every sibling recipe's `compute_gaps(..., *, now=...)` shape."""
    del now  # unused today; kept for interface parity, see docstring

    known_numbers = {i.number for i in issues} | {p.number for p in pulls}

    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for t in tweets:
        # dict.fromkeys dedupes, order-preserving: a tweet naming the same
        # #N twice must not produce two identical GapCandidates that tie
        # each other out of rank()'s SEPARATION_MARGIN (the same task 442
        # bug mention-dangling-reference already guards against).
        for n in dict.fromkeys(_referenced_numbers(t.text)):
            if n in known_numbers:
                excluded.append(GapCandidate(
                    slug=f"own-tweet-ref-matched-{t.id}-{n}",
                    headline=f"Our own tweet referencing #{n} matches a real issue or PR",
                    detail=f"'{t.text}' ({t.url}) references #{n}; a real issue or pull "
                           f"request #{n} exists in this repo. No seam here.",
                    confidence=0.0,
                    evidence=[t.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"own-tweet-dangling-reference-{t.id}-{n}",
                headline=f"Our own tweet references #{n}, but no issue or PR #{n} exists",
                detail=f"'{t.text}' ({t.url}) references #{n}; ListIssues + "
                       f"ListPullRequests found no issue or pull request with that number "
                       f"in this repo. The town's own public claim, sitting on X forever, "
                       f"is already out of sync with GitHub's real number space -- a typo, "
                       f"a reference to something deleted, or a number meant for a "
                       f"different repo, and nobody proofread it before it went out.",
                confidence=_DANGLING_CONFIDENCE,
                evidence=[t.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    tweets_path: Path | None = None,
    issues_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `GetUserTweets`/`ListIssues`/`ListPullRequests` read for the connected
    account and these three loaders are swapped for real reads. The
    detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    tweets = load_tweets(tweets_path)
    issues = load_issues(issues_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(tweets, issues, pulls, now=now)
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
