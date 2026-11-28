"""The hundred-sixteenth real seam recipe, and the first Notion leg of the
claims-unfixed-issue family. `RECIPES/release-claims-unfixed-issue/`
(task 382) watches a release body's own closing-keyword claim against the
issue tracker's real state; `RECIPES/tweet-claims-unfixed-issue/`
(ROADMAP.md #451, the twenty-eighth real recipe) watches the identical
shape one platform over, against a tweet from the connected X account.
Neither has ever read a page written in Notion. `RECIPES/notion-page-
dangling-reference/` (ROADMAP.md #2729, the hundred-fifteenth real
recipe) opened Notion as a read source for the DANGLING-REFERENCE family
only; no claims-* family has ever had a Notion leg before this one.

Same inbound shape as its claims-unfixed-issue siblings: extract every
closing-keyword claim (`fixes #N` / `closes #N` / `resolves #N`, both
tenses) from a Notion page's own text (title + body, concatenated the
same way notion-page-dangling-reference already does), and check the
named issue's real state. If the issue does not exist at all, that is
notion-page-dangling-reference's own seam, not this one's -- excluded
here, named not hidden. If it exists and is closed, the page's claim was
simply true -- excluded, named not hidden. If it exists and is still
open, the page's own durable written record disagrees with reality: that
is the gap.

Reuses `seam_engine.closing_keywords.CLOSING_KEYWORD_RE` verbatim -- the
same shared grammar `release-claims-unfixed-issue`, `tweet-claims-
unfixed-issue`, `commit-closes-keyword-issue-still-open`, and `issue-
closed-never-released` already import from there, rather than a fifth
independently retyped copy of the identical pattern drifting apart from
the other four.

Asks the oath for no new scope: `SearchPages` and `ListIssues` both
already sit cleared on `SCOPES.md`'s table, added for `SearchPages` by
`notion-page-dangling-reference` in the prior task. This recipe is
fixture-only, MOCK ONLY, same WIP shape every other non-GitHub/X toolkit
in this engine already carries: the-hand's live gateway exposes zero
Notion-read tools today.

Confidence is age-gated by the page's own `last_edited_at`, holding
`notion-page-dangling-reference`'s and `issue-comment-claims-unfixed-
issue`'s identical 0.85/0.55 edit-grace-window bar (24 hours) -- a Notion
page, like an ordinary GitHub issue comment, is a text surface its
author can still edit at any time, so a claim caught within the grace
window may simply not have been fixed yet, scoring the lower bar (0.55)
rather than the higher one (0.85) a stale, unedited claim earns. (Two of
this family's existing siblings, `linear-comment-claims-unfixed-issue`
and `slack-message-claims-unfixed-issue`, use a 0.5 lower bar instead for
their own equally-editable surfaces -- a pre-existing inconsistency with
their own dangling-reference twins' 0.55, left alone here: that drift
belongs to those two recipes to resolve, not a reason to pick a third
number for this one.)

This never grades or blames whoever wrote the page -- CONTRIBUTING.md's
"No grading, ever" law, same as every recipe in this engine: the
headline names the gap between a written claim and the tracker's real
state, not a person's error.
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
DEFAULT_PAGES_FIXTURE = _HERE.parents[1] / "fixtures" / "notion_page_claims_unfixed_issue" / "pages.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "notion_page_claims_unfixed_issue" / "issues.json"

# A claim checked within this window of the page's own last_edited_at may
# simply not have been fixed yet, not a settled overclaim -- holds
# notion-page-dangling-reference's own _EDIT_GRACE_WINDOW_HOURS exactly.
_EDIT_GRACE_WINDOW_HOURS = 24.0


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _load_rows(path: Path) -> list[Any]:
    """Refuses a syntactically valid but non-list payload with a named
    error, the same guard every sibling detector's own `_load_rows`
    holds."""
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
    title: str
    state: str
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


def _confidence_for(last_edited_at: datetime, *, now: datetime) -> float:
    age_hours = (now - last_edited_at).total_seconds() / 3600.0
    return 0.85 if age_hours >= _EDIT_GRACE_WINDOW_HOURS else 0.55


def compute_gaps(
    pages: list[NotionPage], issues: list[Issue], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every sibling
    detector's own `compute_gaps`. A page naming no closing-keyword claim
    at all is excluded, named not hidden, the moment it has none; a
    claimed issue is excluded, named not hidden, the moment it names no
    real issue at all, or the issue it names is already closed --
    everything left over (a fix-claim the issue tracker itself
    contradicts) is surfaced, aged into a confidence score `rank()` can
    honestly weigh."""
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for page in pages:
        numbers = _claimed_issue_numbers(page.text)
        if not numbers:
            excluded.append(GapCandidate(
                slug=f"no-claim-phrase-{page.id}",
                headline=f"Notion page {page.id} names no fixes/closes/resolves issue claim",
                detail=f"'{page.title}' ({page.url}) carries no closing-keyword reference. No seam here.",
                confidence=0.0,
                evidence=[page.url],
            ))
            continue

        # dict.fromkeys dedupes, order-preserving -- same precedent every
        # claims-unfixed-issue sibling already holds for a page naming the
        # same #N twice.
        for number in dict.fromkeys(numbers):
            issue = _find_issue(number, issues)
            if issue is None:
                excluded.append(GapCandidate(
                    slug=f"claimed-issue-not-found-{page.id}-{number}",
                    headline=f"Notion page {page.id} claims fixing #{number}, which doesn't exist",
                    detail=f"'{page.title}' ({page.url}) claims #{number} fixed, but no such issue "
                           f"exists. No seam here (see notion-page-dangling-reference).",
                    confidence=0.0,
                    evidence=[page.url],
                ))
                continue

            if issue.state == "closed":
                excluded.append(GapCandidate(
                    slug=f"claim-true-{page.id}-{number}",
                    headline=f"Notion page {page.id}'s claim about #{number} holds",
                    detail=f"'{page.title}' ({page.url}) claims #{number} fixed; issue #{number} "
                           f"('{issue.title}') is closed. No seam here.",
                    confidence=0.0,
                    evidence=[page.url, issue.url],
                ))
                continue

            confidence = _confidence_for(page.last_edited_at, now=now)
            age_hours = (now - page.last_edited_at).total_seconds() / 3600.0
            surfaced.append(GapCandidate(
                slug=f"notion-page-claims-unfixed-issue-{page.id}-{number}",
                headline=f"Notion page {page.id} claims #{number} fixed, but #{number} is still open",
                detail=(
                    f"'{page.title}' ({page.url}, last edited {page.last_edited_at.isoformat()}, "
                    f"{age_hours:.1f}h ago) claims #{number} ('{issue.title}') fixed; "
                    f"the issue's real state is '{issue.state}'."
                ),
                confidence=confidence,
                evidence=[page.url, issue.url],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    pages_path: Path | None = None,
    issues_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every other
    recipe's own `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `SearchPages`/`ListIssues` read for a connected Notion workspace and
    these two loaders are swapped for real calls. The detection logic does
    not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    pages = load_pages(pages_path)
    issues = load_issues(issues_path)
    surfaced, excluded = compute_gaps(pages, issues, now=now)
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
