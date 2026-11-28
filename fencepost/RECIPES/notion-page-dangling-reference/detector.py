"""The hundred-fifteenth real seam recipe, and the eleventh leg of
the dangling-reference family. `RECIPES/dangling-issue-reference/` (task
368) watches this seam inside a commit message; `RECIPES/mention-
dangling-reference/` (task 388) watches it inside a mortal's X mention;
`RECIPES/release-note-dangling-reference/` (task 401) watches it inside a
release body; `RECIPES/issue-body-dangling-reference/` (task 504) watches
it inside an issue or pull request's own OPENING body; `RECIPES/milestone-
body-dangling-reference/` (task 522) watches it inside a milestone's own
description; `RECIPES/own-tweet-dangling-reference/` (task 527) watches it
inside the connected X account's own outbound tweets; `RECIPES/review-
comment-dangling-reference/` (task 534) watches it inside a pull request's
own inline, per-line REVIEW comments; `RECIPES/issue-comment-dangling-
reference/` watches it inside the ordinary issue/PR timeline conversation;
`RECIPES/linear-comment-dangling-reference/` (task 645) watches it inside
a comment left on Linear; `RECIPES/slack-message-dangling-reference/`
watches it inside a message posted to a Slack channel. None of the ten
ever read a page written in Notion.

This is the first recipe in the engine to read a Notion page at all, and
the first to ask the-hand's own gateway for a Notion READ scope --
`SCOPES.md` had only ever named Notion once before, for `CreatePage`, the
one authorized write `draftback.py` uses to render the ledger as an
unpublished page in the connected user's own workspace. `SearchPages` is
the read-side analog: Notion's own answer to `slack`'s
`SearchChannelMessages` and `linear`'s `SearchIssueComments`, both already
sitting on `consent.REQUIRED_SCOPES`.

Same inbound shape as its ten dangling-reference siblings: extract every
bare `#N` reference from a page's own text (title + body, concatenated
the same way a Slack message's or a Linear comment's single text field
already is) and check it against BOTH the live issue list and the live PR
list -- GitHub shares one number sequence between the two, so checking
only one would misfire on a perfectly good reference to a merged PR, the
exact crying-wolf failure Ogun's law calls fatal.

Reuses `seam_engine.references.referenced_numbers` verbatim -- the one
shared `#N`-extraction grammar all ten prior dangling-reference siblings
already import from the same place, so a future tightening of the
pattern lands in all eleven detectors at once or not at all, never a
twelfth independently retyped copy.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads three local fixture files (`pages.json`,
`issues.json`, `pulls.json`), shaped like what a real
`SearchPages`/`ListIssues`/`ListPullRequests` read would return.
`ListIssues` and `ListPullRequests` already sit on `SCOPES.md`'s cleared
oath table under the `github` row. `SearchPages` is new to the oath this
task (consent.py's `REQUIRED_SCOPES["notion"]`, SCOPES.md's table, and
point-fencepost.md's issue template all extended in this same commit, the
exact three-file discipline `recipes.validate_recipe`'s own error message
names) -- the-hand's live gateway exposes zero Notion-read tools today
(only the `CreatePage` write side has ever been confirmed live, per
SCOPES.md's addendum), the identical "registered on the Oath, not yet
wired into the gateway" shape `gmail`/`google_calendar`/`slack`/`linear`
already carry.

The seam: a bare `#N` reference inside a Notion page's own text (its
title or its body) names a GitHub issue or PR number. If no issue or PR
with that number exists in either tracker, whoever wrote the page has a
belief about the project that is already out of sync with GitHub's real
number space -- a typo, a reference to something deleted, or a number
meant for a different repo -- and nothing on either platform ever
compares the two. A page with no `#N` reference at all produces no
candidate whatsoever, not even an excluded one -- the identical "not an
invite at all" exclusion every dangling-reference sibling already makes
for a reference-free source. This never grades or blames whoever wrote
the page -- CONTRIBUTING.md's "No grading, ever" law, same as every
recipe in this engine: the headline names the gap between two records,
not a person's error.

Confidence is age-gated by the page's own `last_edited_at`, holding
`issue-comment-dangling-reference`'s, `linear-comment-dangling-
reference`'s, and `slack-message-dangling-reference`'s identical
0.85/0.55 edit-grace-window bar exactly (24 hours) -- not an
independently re-reasoned number just because the toolkit is new again.
A Notion page, like an ordinary GitHub issue comment, a Linear comment,
or a Slack message and unlike an immutable X mention, is a text surface
its author can still edit at any time, so a reference caught within the
grace window may simply not have been fixed yet, scoring the lower bar
(0.55) rather than the higher one (0.85) a stale, unedited reference
earns.
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
DEFAULT_PAGES_FIXTURE = _HERE.parents[1] / "fixtures" / "notion_page_dangling_reference" / "pages.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "notion_page_dangling_reference" / "issues.json"
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "notion_page_dangling_reference" / "pulls.json"

# A dangling reference on a Notion page touched less than this many hours
# ago is not yet scored as a confirmed gap -- it may simply not have been
# fixed yet. Same 24-hour shape as issue-comment-dangling-reference's,
# linear-comment-dangling-reference's, and slack-message-dangling-
# reference's own _EDIT_GRACE_WINDOW_HOURS, applied here for the identical
# reason: a Notion page is a text surface its author can still edit at
# any time.
_EDIT_GRACE_WINDOW_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _load_rows(path: Path) -> list[Any]:
    """Refuses a syntactically valid but non-list payload with a named
    error, the same guard every sibling detector's own `_load_rows` holds
    (task 358/359's fix, applied here from the start)."""
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(rows).__name__}")
    return rows


@dataclass
class NotionPage:
    id: str
    title: str
    author: str
    text: str
    last_edited_at: datetime
    url: str


@dataclass
class Issue:
    number: int
    url: str


@dataclass
class PullRequest:
    number: int
    url: str


def load_pages(path: Path | None = None) -> list[NotionPage]:
    rows = _load_rows(path or DEFAULT_PAGES_FIXTURE)
    return [
        NotionPage(
            id=r["id"], title=r["title"], author=r["author"],
            text=r["text"], last_edited_at=_parse_ts(r["last_edited_at"]), url=r["url"],
        )
        for r in rows
    ]


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [Issue(number=r["number"], url=r["url"]) for r in rows]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [PullRequest(number=r["number"], url=r["url"]) for r in rows]


def _confidence_for(last_edited_at: datetime, *, now: datetime) -> float:
    age_hours = (now - last_edited_at).total_seconds() / 3600.0
    return 0.85 if age_hours >= _EDIT_GRACE_WINDOW_HOURS else 0.55


def compute_gaps(
    pages: list[NotionPage], issues: list[Issue], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A page with no `#N` reference at all is
    never examined -- it claims nothing about a second record, so there
    is no seam to weigh, the identical "not an invite at all" exclusion
    `slack-message-dangling-reference.compute_gaps` already makes for a
    reference-free message."""
    known_numbers = {i.number for i in issues} | {p.number for p in pulls}

    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for page in pages:
        # dict.fromkeys dedupes, order-preserving: a page naming the same
        # #N twice must not produce two identical GapCandidates that tie
        # each other out of rank()'s SEPARATION_MARGIN (task 442's
        # precedent, held by every sibling in this family).
        for n in dict.fromkeys(_referenced_numbers(page.text)):
            if n in known_numbers:
                excluded.append(GapCandidate(
                    slug=f"notion-page-ref-matched-{page.id}-{n}",
                    headline=f"Notion page {page.id}'s reference to #{n} matches a real issue or PR",
                    detail=f"'{page.title}' ({page.url}) references #{n}; a real issue or "
                           f"pull request #{n} exists in this repo. No seam here.",
                    confidence=0.0,
                    evidence=[page.url],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"notion-page-dangling-reference-{page.id}-{n}",
                headline=f"Notion page '{page.title}' references #{n}, but no issue or PR #{n} exists here",
                detail=f"'{page.title}' ({page.url}) references #{n}; ListIssues + "
                       f"ListPullRequests found no issue or pull request with that number "
                       f"in this repo. Whoever wrote this page has a belief about the "
                       f"project that is already out of sync with GitHub's real number "
                       f"space -- a typo, a reference to something deleted, or a number "
                       f"meant for a different repo.",
                confidence=_confidence_for(page.last_edited_at, now=now),
                evidence=[page.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    pages_path: Path | None = None,
    issues_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `SearchPages`/`ListIssues`/`ListPullRequests` read for a connected
    Notion workspace and these three loaders are swapped for real calls.
    The detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    pages = load_pages(pages_path)
    issues = load_issues(issues_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(pages, issues, pulls, now=now)
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
