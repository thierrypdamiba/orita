"""The forty-ninth real seam recipe: a mortal's own X mention of the
connected account claims a pull request shipped ("ships/includes/merges/via
#N"), but the named PR never actually merged.

The mention-side leg the claims-unmerged-pr family had never grown.
`readme-claims-unmerged-pr`, `release-claims-unmerged-pr`, and
`tweet-claims-unmerged-pr` already cover every text surface the town
itself controls -- its own README, its own release notes, its own tweets
-- but all three only ever check a "shipped it" claim the town made ABOUT
itself. This recipe checks the identical PR-claim grammar against the one
inbound surface none of those three ever read: a stranger's own mention of
the account, sourced from `GetMyMentions` rather than `GetUserTweets` --
the same tweet-vs-mention split `mention-claims-unfixed-issue` (the
forty-seventh real recipe) opened against `tweet-claims-unfixed-issue` for
the sibling claims-unfixed-issue family, and `mention-claims-open-milestone`
(the forty-eighth) opened against `tweet-claims-open-milestone` for the
claims-open-milestone family -- applied here to the third and last
claims-X family, claims-unmerged-pr.

Deliberately reuses `seam_engine.pr_claims.claimed_pr_numbers` verbatim --
the same shared "ships/includes/merges/via #N" grammar
`release-claims-unmerged-pr`, `merged-pr-never-released`, and
`tweet-claims-unmerged-pr` already import from there -- rather than a
fourth copy of the identical pattern drifting apart from the rest.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads two local fixture files (`mentions.json`,
`pulls.json`), shaped like what `GetMyMentions` and `ListPullRequests`
would actually return. Both scopes already sit on `SCOPES.md`'s cleared
oath table (`GetMyMentions` since founding, first used by
`mention-dangling-reference`; `ListPullRequests` used by every recipe that
reads the PR tracker already in this engine). No new scope is asked for
anywhere in this recipe.

The seam: a claim phrase ("ships #N" / "includes #N" / "merges #N" /
"via #N", case-insensitive) inside a mortal's own mention names a PR by
number. If that PR does not exist at all, it is excluded here -- that
broken reference is `dangling-issue-reference`'s/`mention-dangling-
reference`'s own seam, not this one's. If it exists and is merged, the
claim was simply true -- excluded, named not hidden. If it exists and is
NOT merged (still open, or closed without merging), a stranger's own
permanent public claim about the project, sitting on X, already disagrees
with GitHub's own record -- and nothing on either platform ever compares
the two.

Confidence is age-gated by the mention's own `created_at`, mirroring
`tweet-claims-unmerged-pr`'s identical reasoning -- not a discounted copy
of it. A claim checked within 24 hours of posting might still be a race
(the real merge landing moments after the mention went out) rather than a
settled overclaim. Like `mention-claims-unfixed-issue`'s and
`mention-claims-open-milestone`'s own reasoning (and unlike
`mention-dangling-reference`'s deliberately lower, flat score), the check
this recipe makes is objective: the claimed PR's own live `state`/`merged`
fields, verified against `ListPullRequests`, not the mortal's guess at the
repo's number space. A mortal cannot be "wrong about the number space" and
still land a real, existing PR number attached to a real claim phrase -- so
this recipe holds `tweet-claims-unmerged-pr`'s own 0.85/0.5 bar exactly, no
independently re-reasoned number.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.pr_claims import claimed_pr_numbers as _claimed_pr_numbers
from seam_engine.scan import GapCandidate

_HERE = Path(__file__).resolve().parent
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "mention_claims_unmerged_pr"
DEFAULT_MENTIONS_FIXTURE = _FIXTURE_DIR / "mentions.json"
DEFAULT_PULLS_FIXTURE = _FIXTURE_DIR / "pulls.json"

# A claim checked within this window of the mention's own created_at may
# just be a race rather than a genuine, settled public overclaim -- the
# identical bar tweet-claims-unmerged-pr holds itself to.
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
class PullRequest:
    number: int
    title: str
    state: str
    merged: bool
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


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [
        PullRequest(number=r["number"], title=r["title"], state=r["state"], merged=r["merged"], url=r["url"])
        for r in rows
    ]


def _find_pull(number: int, pulls: list[PullRequest]) -> PullRequest | None:
    for pr in pulls:
        if pr.number == number:
            return pr
    return None


def compute_gaps(
    mentions: list[Mention], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other recipe's
    own `compute_gaps`. A claimed PR is excluded, named not hidden, the
    moment it names no real PR at all, or the PR it names is actually
    merged -- everything left over (a shipped-it claim the PR tracker
    itself contradicts) is surfaced, aged into a confidence score rank()
    can honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for mention in mentions:
        numbers = _claimed_pr_numbers(mention.text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{mention.id}",
                headline=f"@{mention.author}'s mention {mention.id} names no ships/includes/merges/via PR claim",
                detail=f"'{mention.text}' carries no claim-phrase reference. No seam here.",
                confidence=0.0,
                evidence=[mention.url],
            ))
            continue

        seen: set[int] = set()
        for number in numbers:
            if number in seen:
                continue
            seen.add(number)

            pr = _find_pull(number, pulls)
            if pr is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-pr-not-found-{mention.id}-{number}",
                    headline=f"@{mention.author}'s mention {mention.id} claims #{number}, which doesn't exist",
                    detail=f"'{mention.text}' claims #{number} shipped, but no such PR exists. No seam here (see dangling-issue-reference).",
                    confidence=0.0,
                    evidence=[mention.url],
                ))
                continue

            if pr.merged:
                excluded.append(GapCandidate(
                    slug=f"claim-true-{mention.id}-{number}",
                    headline=f"@{mention.author}'s mention {mention.id}'s claim about #{number} holds",
                    detail=f"'{mention.text}' claims #{number} shipped; PR #{number} ('{pr.title}') is merged. No seam here.",
                    confidence=0.0,
                    evidence=[mention.url, pr.url],
                ))
                continue

            age_hours = (now - mention.created_at).total_seconds() / 3600.0
            confidence = 0.85 if age_hours >= _STALE_HOURS else 0.5
            surfaced.append(GapCandidate(
                slug=f"mention-claims-unmerged-pr-{mention.id}-{number}",
                headline=f"@{mention.author}'s mention {mention.id} claims #{number} shipped, but #{number} never merged",
                detail=(
                    f"'{mention.text}' (posted {mention.created_at.isoformat()}, "
                    f"{age_hours:.1f}h ago) claims #{number} ('{pr.title}') shipped; "
                    f"the PR's real state is '{pr.state}', merged={pr.merged}."
                ),
                confidence=confidence,
                evidence=[mention.url, pr.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    mentions_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `GetMyMentions`/`ListPullRequests` read for a connected account and
    these two loaders are swapped for real calls. The detection logic does
    not change when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    mentions = load_mentions(mentions_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(mentions, pulls, now=now)
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
