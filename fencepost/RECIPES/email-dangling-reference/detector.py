"""The ninety-eighth real seam recipe, and the eleventh leg of the
dangling-reference family. `RECIPES/dangling-issue-reference/` (task 368)
watches this seam inside a commit message; `RECIPES/mention-dangling-
reference/` (task 388) watches it inside a mortal's X mention;
`RECIPES/release-note-dangling-reference/` (task 401) watches it inside a
release body; `RECIPES/issue-body-dangling-reference/` (task 504) watches
it inside an issue or pull request's own OPENING body; `RECIPES/milestone-
body-dangling-reference/` (task 522) watches it inside a milestone's own
description; `RECIPES/own-tweet-dangling-reference/` (task 527) watches it
inside the connected X account's own outbound tweets; `RECIPES/review-
comment-dangling-reference/` (task 534) watches it inside a pull request's
own inline, per-line REVIEW comments; `RECIPES/issue-comment-dangling-
reference/` watches it inside the ordinary issue/PR timeline conversation;
`RECIPES/linear-comment-dangling-reference/` (task 645) watches it inside a
comment left on Linear; `RECIPES/slack-message-dangling-reference/` (task
1153, by count) watches it inside a message posted to a Slack channel.
None of the ten ever read an inbound email.

`RECIPES/email-claims-unfixed-issue/detector.py`'s own docstring (the
ninety-third real recipe) named this seam and deliberately left it open:
"If that issue does not exist at all, it is excluded here -- that broken
reference belongs to a future email-side dangling-reference recipe, not
this one." This is that recipe. Same inbound surface (an email landing in
a connected inbox, read via `ListEmails`), a different claim shape:
`email-claims-unfixed-issue` only ever looks at real GitHub closing-keyword
phrases (`fixes`/`closes`/`resolves #N`) and only against the issue
tracker; this recipe looks at EVERY bare `#N` reference regardless of the
word in front of it ("any movement on #N", "saw #N land in the changelog")
and checks it against BOTH the issue list and the PR list -- GitHub shares
one number sequence between the two, the same "checking only one misfires
on a perfectly good reference to a merged PR" discipline every
dangling-reference sibling already holds itself to.

Reuses `seam_engine.references.referenced_numbers` verbatim -- the one
shared `#N`-extraction grammar `dangling-issue-reference` and its nine
prior dangling-reference siblings already import from the same place, so
a future tightening of the pattern (the cross-repo `owner/repo#N`
exclusion, in particular) lands in all eleven detectors at once or not at
all, never a twelfth independently retyped copy.

Read-only, MOCK ONLY, same as every recipe under CONTRIBUTING.md's law:
this module only ever reads three local fixture files (`emails.json`,
`issues.json`, `pulls.json`), shaped like what a real
`ListEmails`/`ListIssues`/`ListPullRequests` read would return. `ListIssues`
and `ListPullRequests` already sit on `SCOPES.md`'s cleared oath table
under the `github` row. `ListEmails` is the same scope
`email-claims-unfixed-issue` already asks for -- it clears
`seam_engine.recipes.validate_recipe`'s oath the same way every scope in
this engine does. See `SCOPES.md`'s own WIP note for this toolkit: the-hand
gateway's connected Google account carries `gmail.readonly` among its
granted OAuth scopes, but exposes zero Gmail-capable tools anywhere in its
live MCP toolset today -- the identical "connected upstream, not wired
into the gateway" shape `SCOPES.md`'s Slack/Linear WIP notes each carry
for their own toolkit.

The seam: a bare `#N` reference inside an inbound email's own body names a
GitHub issue or PR number. If no issue or PR with that number exists at
all in either tracker, whoever sent the email has a belief about the
project that is already out of sync with GitHub's real number space -- a
typo, a reference to something deleted, or a number meant for a different
repo -- and nothing on either platform ever compares the two. An email
with no `#N` reference at all produces no candidate whatsoever, not even
an excluded one -- the identical "not an invite at all" exclusion every
dangling-reference sibling already makes for a reference-free source. This
never grades or blames whoever sent the email -- CONTRIBUTING.md's "No
grading, ever" law, same as every recipe in this engine: the headline
names the gap between two records, not a person's error.

Confidence is FLAT, not age-gated -- the same reasoning `mention-dangling-
reference` already gives for its own flat score, and unlike `slack-message-
dangling-reference`/`linear-comment-dangling-reference`'s age-gated
0.85/0.55: an email, like an X mention and unlike a Slack message or a
Linear comment, is not a text surface its sender can revise after the fact
once it has landed in a connected inbox -- there is no second edit pass to
wait out. Held at 0.75, `mention-dangling-reference`'s own exact number,
not an independently re-reasoned one: an inbound email is unstructured
prose from a correspondent who may simply be numbering a wholly different
tracker in their own head, the identical reasoning `mention-dangling-
reference`'s docstring already gives for scoring below `dangling-issue-
reference`'s self-authored 0.8 -- a stranger's own belief, not the town's
own repo-scoped convention.
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
DEFAULT_EMAILS_FIXTURE = _HERE.parents[1] / "fixtures" / "email_dangling_reference" / "emails.json"
DEFAULT_ISSUES_FIXTURE = _HERE.parents[1] / "fixtures" / "email_dangling_reference" / "issues.json"
DEFAULT_PULLS_FIXTURE = _HERE.parents[1] / "fixtures" / "email_dangling_reference" / "pulls.json"

# Flat 0.75 -- mention-dangling-reference's own exact score, not a
# copy-pasted guess: an inbound email, like an X mention and unlike a
# Slack message or a Linear comment, is unstructured prose from a
# correspondent who may simply be numbering a different tracker in their
# own head, and is not a text surface its sender gets a second edit pass
# on once it has landed. See this module's own docstring for the full
# reasoning.
_DANGLING_CONFIDENCE = 0.75


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
class Email:
    id: str
    sender: str
    subject: str
    body: str
    received_at: datetime


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


def load_emails(path: Path | None = None) -> list[Email]:
    rows = _load_rows(path or DEFAULT_EMAILS_FIXTURE)
    return [
        Email(
            id=r["id"], sender=r["sender"], subject=r["subject"], body=r["body"],
            received_at=_parse_ts(r["received_at"]),
        )
        for r in rows
    ]


def load_issues(path: Path | None = None) -> list[Issue]:
    rows = _load_rows(path or DEFAULT_ISSUES_FIXTURE)
    return [Issue(number=r["number"], title=r["title"], state=r["state"], url=r["url"]) for r in rows]


def load_pulls(path: Path | None = None) -> list[PullRequest]:
    rows = _load_rows(path or DEFAULT_PULLS_FIXTURE)
    return [PullRequest(number=r["number"], title=r["title"], state=r["state"], url=r["url"]) for r in rows]


def compute_gaps(
    emails: list[Email], issues: list[Issue], pulls: list[PullRequest], *, now: datetime
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced, excluded) -- same shape as every other detector in
    this engine. An email with no `#N` reference at all is not examined --
    it never claims anything about a second record, so there is no seam to
    weigh, the same "not an invite at all" exclusion `mention-dangling-
    reference.compute_gaps` already makes for a reference-free mention.
    `now` is accepted, unused, for interface parity with every sibling
    recipe's `compute_gaps(..., *, now=...)` shape -- this recipe is flat,
    not age-gated, same as its `mention-dangling-reference` twin."""
    del now  # unused today; kept for interface parity, see docstring

    known_numbers = {i.number for i in issues} | {p.number for p in pulls}

    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for e in emails:
        # dict.fromkeys dedupes, order-preserving: an email naming the
        # same #N twice must not produce two identical GapCandidates that
        # tie each other out of rank()'s SEPARATION_MARGIN (task 442's
        # precedent, held by every sibling in this family).
        for n in dict.fromkeys(_referenced_numbers(e.body)):
            if n in known_numbers:
                excluded.append(GapCandidate(
                    slug=f"email-ref-matched-{e.id}-{n}",
                    headline=f"{e.sender}'s email referencing #{n} matches a real issue or PR",
                    detail=f"'{e.body}' ({e.id}, from {e.sender}) references #{n}; a real "
                           f"issue or pull request #{n} exists in this repo. No seam here.",
                    confidence=0.0,
                    evidence=[e.id],
                ))
                continue

            surfaced.append(GapCandidate(
                slug=f"email-dangling-reference-{e.id}-{n}",
                headline=f"{e.sender}'s email references #{n}, but no issue or PR #{n} exists here",
                detail=f"'{e.body}' ({e.id}, from {e.sender}) references #{n}; ListIssues + "
                       f"ListPullRequests found no issue or pull request with that number "
                       f"in this repo. A correspondent's own belief about the project, "
                       f"sitting in an inbox, is already out of sync with GitHub's real "
                       f"number space -- a typo, a reference to something deleted, or a "
                       f"number meant for a different repo.",
                confidence=_DANGLING_CONFIDENCE,
                evidence=[e.id],
            ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_recipe_scan(
    emails_path: Path | None = None,
    issues_path: Path | None = None,
    pulls_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The manifest's `entrypoint`. Same output shape as every sibling
    recipe's `run_recipe_scan` -- `source: "fixture"` is the honest WIP
    marker this recipe carries until the Hand's gateway carries a live
    `ListEmails`/`ListIssues`/`ListPullRequests` read for a connected
    Gmail account and these three loaders are swapped for real calls. The
    detection logic does not change one line when that happens."""
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    emails = load_emails(emails_path)
    issues = load_issues(issues_path)
    pulls = load_pulls(pulls_path)
    surfaced, excluded = compute_gaps(emails, issues, pulls, now=now)
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
