"""The eightieth real seam recipe: the repository's own one-line
description -- the text GitHub shows in search results, in a fork
listing, and above the fold on the repo's own homepage, before README.md
ever loads -- counts on an issue or pull request that isn't actually
there.

Nine recipes already watch this exact seam on nine other text surfaces --
`dangling-issue-reference` (commit messages, task 368),
`mention-dangling-reference` (X mentions, task 388),
`release-note-dangling-reference` (release notes, task 401),
`issue-body-dangling-reference` (issue/PR bodies, task 402),
`milestone-body-dangling-reference` (milestone descriptions, task 520),
`own-tweet-dangling-reference` (the town's own tweets, task 527),
`review-comment-dangling-reference` (inline review comments, task 534),
`issue-comment-dangling-reference` (timeline comments, task 581), and
`readme-dangling-reference` (README.md, task 665) -- but none of them ever
reads `GetRepository`'s own `description` field, even though that scope
has sat on `SCOPES.md`'s cleared oath table since the first day
(`example-release-vs-changelog` and `release-not-tweeted` both already
name it, but neither reads `description` -- both only ever look at the
repository's tags/releases). A maintainer types the one-line description
once, early, often to summarize "what shipped" or "see #N for the plan" --
and then almost never revisits it, unlike a README a stranger actually
opens and skims. It is exactly the kind of permanent, public, rarely-
reproofread surface `dangling-issue-reference`'s own docstring first named
this blind spot on, one level MORE forgotten than README itself.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads three local fixture files (`repository.json`,
`issues.json`, `pulls.json`), shaped like what a read-only `GetRepository`,
`ListIssues`, and `ListPullRequests` call would actually return. All three
scopes already sit on `SCOPES.md`'s cleared oath table under the `github`
row -- this recipe asks Arcade for nothing new.

The seam: `#N` inside the repository's own `description` field is checked
against BOTH the issue list and the PR list, the same "one shared number
sequence" discipline every sibling dangling-reference recipe already holds
itself to -- checking only one would misfire on a perfectly good reference
to a merged PR. A cross-repo `owner/repo#N` reference is never even
extracted as a candidate -- that names a different repo's own number space
on purpose. This recipe imports `seam_engine.references.referenced_numbers`
rather than writing a tenth copy of the same extraction regex -- the
identical "one law, not a tenth copy of it" discipline this engine has
already paid for on the same shared pattern nine times over.

Confidence is deliberately NOT age-gated, mirroring `readme-dangling-
reference`'s own flat 0.85 bar and its exact reasoning: a `GetRepository`
read returns the description CURRENT right now, not a change history, so
there is no per-claim "when was this written" timestamp to weigh a
staleness window against -- and no race to guard against either: the
description is read live, right now, so a reference it currently carries
and the issue/PR tracker's currently-known numbers are both true at the
same instant this scan runs. A repository carrying no description at all
(GitHub allows this; a null field is common on brand-new or minimal repos)
is excluded outright, named not hidden, not treated as a reference-free
false candidate.
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
_FIXTURE_DIR = _HERE.parents[1] / "fixtures" / "repo_description_dangling_reference"
DEFAULT_REPOSITORY_FIXTURE = _FIXTURE_DIR / "repository.json"
DEFAULT_ISSUES_FIXTURE = _FIXTURE_DIR / "issues.json"
DEFAULT_PULLS_FIXTURE = _FIXTURE_DIR / "pulls.json"

# Flat, not age-gated -- see module docstring for why this mirrors
# readme-dangling-reference's own bar exactly.
_DANGLING_CONFIDENCE = 0.85


def _load_rows(path: Path) -> list[Any]:
    """Refuses a syntactically valid but non-list payload with a named
    error, the same guard every sibling detector's own `_load_rows` holds."""
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


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


def load_description(path: Path | None = None) -> str | None:
    """Load the whole-file `{"full_name": ..., "description": ..., "url":
    ...}` shape a `GetRepository` call returns, refusing a syntactically
    valid but wrong-shaped payload with a named error -- same discipline
    `readme-dangling-reference`'s own `load_readme` already holds.
    `description` may be JSON `null` (a real, common GitHub value for a
    minimal repo) -- returned as `None`, not coerced into an empty string,
    so the caller can exclude it explicitly rather than silently treating
    it as reference-free."""
    p = path or DEFAULT_REPOSITORY_FIXTURE
    data = json.loads(p.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{p}: expected a JSON object, got {type(data).__name__}")
    if "description" not in data:
        raise ValueError(f"{p}: expected a 'description' field")
    description = data["description"]
    if description is not None and not isinstance(description, str):
        raise ValueError(f"{p}: expected 'description' to be a string or null")
    return description


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [Issue(number=r["number"], title=r["title"], state=r["state"], url=r["url"]) for r in rows]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [PullRequest(number=r["number"], title=r["title"], state=r["state"], url=r["url"]) for r in rows]


def compute_gaps(
    description: str | None, issues: list[Issue], pulls: list[PullRequest]
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A `None` description, or one with no
    `#N` reference at all, is never examined -- it claims nothing about a
    second record, so there is no seam to weigh, the identical "not an
    invite at all" exclusion every dangling-reference sibling already
    makes."""
    known_numbers = {i.number for i in issues} | {p.number for p in pulls}

    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    if description is None:
        excluded.append(GapCandidate(
            slug="no-description",
            headline="This repository carries no description",
            detail="GetRepository's own description field reads null. No seam here.",
            confidence=0.0,
            evidence=[],
        ))
        return surfaced, excluded

    # dict.fromkeys dedupes, order-preserving: the description naming the
    # same #N twice must not produce two identical GapCandidates that tie
    # each other out of rank()'s SEPARATION_MARGIN, the same fix task 442
    # made for release-note-dangling-reference's own extraction.
    for n in dict.fromkeys(_referenced_numbers(description)):
        if n in known_numbers:
            excluded.append(GapCandidate(
                slug=f"description-ref-matched-{n}",
                headline=f"The repo description's reference to #{n} matches a real issue or PR",
                detail=f"The repository description references #{n}; a real issue or "
                       f"pull request #{n} exists in this repo. No seam here.",
                confidence=0.0,
                evidence=[],
            ))
            continue

        surfaced.append(GapCandidate(
            slug=f"repo-description-dangling-reference-{n}",
            headline=f"The repo description references #{n}, but no issue or PR #{n} exists here",
            detail=f"The repository's own description references #{n}; ListIssues + "
                   f"ListPullRequests found no issue or pull request with that number "
                   f"in this repo. The description is the first thing a stranger sees "
                   f"in search results, above README, and nothing ever proofreads it "
                   f"again after it's written.",
            confidence=_DANGLING_CONFIDENCE,
            evidence=[],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    repository_path: Path | None = None,
    issues_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `GetRepository`/`ListIssues`/`ListPullRequests` read for a connected
    account and these three loaders are swapped for real reads. The
    detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    description = load_description(repository_path)
    issues = load_issues(issues_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(description, issues, pulls)
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
