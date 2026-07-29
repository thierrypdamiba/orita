"""The eighteenth real seam recipe: a mortal's own X mention of the
connected account counts on an issue or pull request that isn't actually
there.

Every cross-toolkit recipe shipped so far (`release-not-tweeted`,
`contributor-thanked-not-credited`, `readme-credited-not-thanked`) reads
OUTBOUND signal from the town's own X account -- its tweets. `GetMyMentions`
reads the opposite direction: INBOUND mentions FROM mortals, a scope that
has sat cleared on `SCOPES.md`'s oath table since founding (`X | GetUserTweets,
GetMyMentions, WhoAmI`) without a single recipe ever using it. This one does.

The seam this recipe watches is the same shape `dangling-issue-reference`
(RECIPES/dangling-issue-reference/) already proved for commit messages --
GitHub's own `#N` shorthand rendered as a clickable link with no check that
it resolves to anything -- but sourced from a different, riskier place: a
stranger's own prose about the town, sitting on a platform GitHub does not
control at all. A mortal who mentions the account about "#99" believing it
is a real, live issue, when no issue or pull request #99 exists in this
repo, is a genuine cross-account confusion: their own belief, formed on X,
is already out of sync with GitHub's real number space, and nothing on
either platform alone would ever surface that -- reading only mentions
never shows the tracker is empty at that number; reading only the tracker
never shows anyone believed otherwise.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads three local fixture files (`mentions.json`,
`issues.json`, `pulls.json`), shaped like what `GetMyMentions`, `ListIssues`,
and `ListPullRequests` would actually return. All three scopes already sit
on SCOPES.md's cleared oath table -- this recipe asks Arcade for nothing
new.

The extraction regex and the cross-repo `owner/repo#N` exclusion are the
same law `dangling-issue-reference/detector.py` already proved for commit
messages -- what counts as a same-repo `#N` reference. This module shipped
(task 388) with that law RETYPED a second time as its own local `_REF_RE`,
under a docstring claim of "not a second copy of it drifting apart" that
the code did not actually honor: two textually-identical, independently
defined regexes are not one law. Task 389 fixed that for real: both this
module and `dangling-issue-reference/detector.py` now import
`referenced_numbers` from `seam_engine.references`, the one place the
grammar lives, so a future tightening of the pattern lands in both
detectors at once or not at all. GitHub shares one number sequence between
issues and pull requests, so a reference is checked against BOTH lists,
exactly as the commit-sourced twin does -- checking only one would
misfire on a perfectly good reference to a merged PR, the exact
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
DEFAULT_MENTIONS_FIXTURE = _HERE.parents[1] / "fixtures" / "mention_dangling_reference" / "mentions.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "mention_dangling_reference" / "issues.json"
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "mention_dangling_reference" / "pulls.json"

# `_referenced_numbers` is bound above, not redefined here -- task 389 made
# this docstring's own "reused verbatim... not a second copy of it
# drifting apart" claim true. It was false the hour this recipe shipped
# (task 388): the code below retyped `_REF_RE` a second time with no
# import connecting it to `dangling-issue-reference/detector.py`'s
# original. Both recipes now import the identical function from
# `seam_engine.references`, the one real place this grammar lives.

# Flat, not age-gated -- the same reasoning `dangling-issue-reference`
# already gives for its own flat score: a miss against BOTH the live issue
# list and the live PR list is a real, structural signal with no keyword
# fuzziness to misfire on, and a mention (unlike a PR body or a release
# that can still catch up later) never gets a second edit pass either.
#
# Deliberately LOWER than that twin's 0.8, though, not a copy-pasted
# number: a commit message is authored by a god following this town's own
# repo-scoped `#N` convention on purpose. An X mention is unstructured
# prose from a stranger, who may simply be numbering a wholly different
# tracker in their own head -- a habit this recipe has no way to see,
# unlike the explicit `owner/repo#N` shorthand a cross-repo commit
# reference is expected to use and this recipe already excludes on sight.
# 0.75 still clears CONFIDENCE_BAR (0.70) with room to spare, but honestly
# short of the same certainty a same-author, same-repo commit reference
# earns.
_DANGLING_CONFIDENCE = 0.75


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _load_rows(path: Path) -> list[Any]:
    """Load a whole-file JSON list, refusing a syntactically valid but
    non-list payload with a named error instead of letting it reach a `for`
    loop unmarked. Mirrors `dangling-issue-reference/detector.py`'s own
    `_load_rows` exactly -- the identical bug class, task 358/359's own
    fix, applied here from the start rather than found later."""
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


@dataclass
class Mention:
    id: str
    author: str
    text: str
    url: str
    ts: datetime


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


def load_mentions(path: Path | None = None) -> list[Mention]:
    rows = _load_rows(path or DEFAULT_MENTIONS_FIXTURE)
    return [
        Mention(id=r["id"], author=r["author"], text=r["text"], url=r["url"], ts=_parse_ts(r["created_at"]))
        for r in rows
    ]


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [Issue(number=r["number"], title=r["title"], state=r["state"], url=r["url"]) for r in rows]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [PullRequest(number=r["number"], title=r["title"], state=r["state"], url=r["url"]) for r in rows]


def compute_gaps(
    mentions: list[Mention], issues: list[Issue], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other detector in
    this engine. A mention with no `#N` reference at all is not examined --
    it never claims anything about a second record, so there is no seam to
    weigh, the same "not an invite at all" exclusion `dangling-issue-reference
    .compute_gaps` already makes for a commit with no reference. `now` is
    accepted, unused, for interface parity with every sibling recipe's
    `compute_gaps(..., *, now=...)` shape."""
    del now  # unused today; kept for interface parity, see docstring

    known_numbers = {i.number for i in issues} | {p.number for p in pulls}

    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for m in mentions:
        for n in _referenced_numbers(m.text):
            if n in known_numbers:
                excluded.append(GapCandidate(
                    slug=f"mention-ref-matched-{m.id}-{n}",
                    headline=f"@{m.author}'s mention referencing #{n} matches a real issue or PR",
                    detail=f"'{m.text}' ({m.url}) references #{n}; a real issue or pull "
                           f"request #{n} exists in this repo. No seam here.",
                    confidence=0.0,
                    evidence=[m.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"mention-dangling-reference-{m.id}-{n}",
                headline=f"@{m.author} mentions #{n}, but no issue or PR #{n} exists here",
                detail=f"'{m.text}' ({m.url}) references #{n}; ListIssues + "
                       f"ListPullRequests found no issue or pull request with that number "
                       f"in this repo. A mortal's own belief about the project, sitting on "
                       f"X, is already out of sync with GitHub's real number space -- a "
                       f"typo, a reference to something deleted, or a number meant for a "
                       f"different repo.",
                confidence=_DANGLING_CONFIDENCE,
                evidence=[m.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    mentions_path: Path | None = None,
    issues_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `GetMyMentions`/`ListIssues`/`ListPullRequests` read for a connected
    account and these three loaders are swapped for real reads. The
    detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    mentions = load_mentions(mentions_path)
    issues = load_issues(issues_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(mentions, issues, pulls, now=now)
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
