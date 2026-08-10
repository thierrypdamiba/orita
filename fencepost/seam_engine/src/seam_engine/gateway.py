"""The Arcade gateway contract Fencepost is built on — read only, on iron.

This module is not decoration. It is the single source of truth for the
exact capabilities string a forker pastes into Arcade when they build their
own gateway (CONNECT.md and docs/fencepost/connect.html both quote
``READ_ONLY_CAPABILITIES`` verbatim — tested, not just claimed, by
tests/test_connect_doctrine.py). If this string ever drifts toward asking
for a write, ``is_read_only_capabilities`` catches it before a human does.

Per fencepost/SCOPES.md: Fencepost holds only Get/List/Read/Search/Count/
WhoAmI. A gateway capabilities description is a *request* Arcade's tool
matcher reads to select tools — so the request itself must never use a verb
that could steer the matcher toward a write-capable tool.

Task 152: this string is also a *floor*, not just a ceiling. A forker who
pastes it verbatim into Arcade's Gateway Assistant provisions a gateway
that must be able to satisfy every scope ``consent.REQUIRED_SCOPES`` will
later demand a scope-confirm name verbatim, or their own onboarding consent
gate (``consent.enforce_consent_gate``) can never pass. Before task 152 the
string named only 4 of the 8 GitHub tool concepts and 2 of the 3 X tool
concepts ``REQUIRED_SCOPES`` requires — a real forker following CONNECT.md
exactly could have provisioned a gateway missing repository metadata,
repository activity, stargazer-count, and identity tools.
``required_scopes_covered_by_capabilities`` makes that relationship
checkable instead of two constants that happened to agree.

Task 372: that checker had its own silent gap. ``GetFileContents`` (added
to ``consent.REQUIRED_SCOPES["github"]`` by task 371 for the fifth recipe)
had no entry in ``_SCOPE_KEYWORDS`` and no wording anywhere in
``READ_ONLY_CAPABILITIES`` — yet ``required_scopes_covered_by_capabilities()``
still returned ``{}`` (fully covered) because a missing keyword defaulted to
an empty string, and an empty string is a substring of everything. Fixed
both halves together: the string now names "individual file contents", and
a ``REQUIRED_SCOPES`` tool with no keyword entry at all is now always
reported as a gap rather than silently passing.
"""
from __future__ import annotations

import re

from seam_engine.consent import REQUIRED_SCOPES

# The exact string to paste into Arcade's Gateway Assistant, or into the
# "Description" field on https://api.arcade.dev/dashboard/mcp-gateways, when
# building your own Fencepost gateway. Arcade's tool matcher reads this and
# selects tools automatically — see docs.arcade.dev/en/guides/mcp-gateways.
READ_ONLY_CAPABILITIES = (
    "Read-only seam reconciliation: list and read GitHub repository "
    "metadata, commit history, releases, tags, issues, pull requests, "
    "repository activity, individual file contents, milestones, pull "
    "request review comments, and stargazer counts, and read a connected "
    "user's own X (Twitter) tweet history, mentions, and account identity "
    "— solely to compare the two timelines and surface gaps between what "
    "shipped and what was announced. Never create, update, merge, label, "
    "delete, post, reply, send, or modify anything on any connected "
    "account."
)

# Every REQUIRED_SCOPES tool (imported live above, never a second hand-typed
# copy) mapped to the keyword phrase that must appear, case-insensitive, in
# READ_ONLY_CAPABILITIES for a forker's gateway to actually be provisioned
# with that tool. Prose can't quote a CamelCase tool name and still read
# like a capabilities request to Arcade's matcher, so this mapping is the
# one place a human states which phrase stands for which tool.
_SCOPE_KEYWORDS: dict[str, dict[str, str]] = {
    "github": {
        "GetRepository": "repository metadata",
        "ListRepoCommits": "commit history",
        "ListIssues": "issues",
        "GetIssue": "issues",
        "ListPullRequests": "pull requests",
        "GetPullRequest": "pull requests",
        "ListRepositoryActivities": "repository activity",
        "CountStargazers": "stargazer",
        "GetLatestRelease": "release",
        "GetFileContents": "file contents",
        "ListMilestones": "milestone",
        "ListReviewCommentsInARepository": "review comments",
        "ListTags": "tag",
        "ListReleases": "release",
    },
    "x": {
        "GetUserTweets": "tweet history",
        "GetMyMentions": "mentions",
        "WhoAmI": "identity",
    },
}


def required_scopes_covered_by_capabilities(
    text: str | None = None,
    required_scopes: dict[str, frozenset[str]] | None = None,
) -> dict[str, list[str]]:
    """Return, per toolkit, the ``REQUIRED_SCOPES`` tool names ``text`` does
    NOT name a covering keyword for — an empty list per toolkit means full
    coverage. Pure function, no I/O, same shape as ``is_read_only_capabilities``.

    Only checks toolkits present in ``_SCOPE_KEYWORDS`` (github, x) — gmail
    and google_calendar are v0.2, not yet part of this gateway's own oath.

    Task 372: a ``REQUIRED_SCOPES`` tool with NO entry at all in
    ``_SCOPE_KEYWORDS[toolkit]`` used to fall through ``keywords.get(tool,
    "")`` to an empty-string default — and an empty string is trivially a
    substring of every string, so ``"" not in lowered`` is always ``False``.
    A brand-new scope added to ``REQUIRED_SCOPES`` (consent.py) with nobody
    remembering to also add its keyword here silently read as "covered" by
    this function instead of "missing" — the exact false negative this
    function exists to prevent, just one layer up from the string itself.
    That is precisely what happened: task 371 added ``GetFileContents`` to
    ``REQUIRED_SCOPES["github"]`` for the fifth recipe but never touched
    this file, and ``test_the_towns_own_capabilities_string_covers_every_
    required_scope`` kept passing anyway. A tool absent from ``keywords``
    is now always a reported gap, never a silent pass.
    """
    text = READ_ONLY_CAPABILITIES if text is None else text
    required_scopes = REQUIRED_SCOPES if required_scopes is None else required_scopes
    lowered = text.lower()
    missing: dict[str, list[str]] = {}
    for toolkit, keywords in _SCOPE_KEYWORDS.items():
        gaps = [
            tool
            for tool in required_scopes.get(toolkit, frozenset())
            if tool not in keywords or keywords[tool].lower() not in lowered
        ]
        if gaps:
            missing[toolkit] = sorted(gaps)
    return missing

# The real Arcade surfaces a forker lands on to build and connect a gateway.
# Quoted verbatim in CONNECT.md and docs/fencepost/connect.html so the
# walkthrough links straight into the actual OAuth connect flow, not a stand-in.
ARCADE_GATEWAY_DASHBOARD_URL = "https://api.arcade.dev/dashboard/mcp-gateways"
ARCADE_CONNECT_CLIENTS_DOC_URL = "https://docs.arcade.dev/en/get-started/mcp-clients"
ARCADE_CREATE_VIA_AI_DOC_URL = "https://docs.arcade.dev/en/guides/mcp-gateways/create-via-ai"
ARCADE_MCP_URL_TEMPLATE = "https://api.arcade.dev/mcp/<YOUR-GATEWAY-SLUG>"

# Verbs that, unnegated, would ask Arcade's tool matcher for write-capable
# tools. Mirrors the FORBIDDEN_TOOLS spirit of test_onboarding_doctrine.py
# but at the level of the capabilities *request*, not a tool name.
_WRITE_VERBS = (
    "create",
    "update",
    "merge",
    "delete",
    "post",
    "reply",
    "send",
    "modify",
    "write",
    "remove",
    "label",
    "draft",
    "trash",
    "invite",
    "revoke",
    "publish",
    "share",
)

# A verb only counts as a live ask if it isn't itself being ruled out.
_NEGATION_CUES = ("never", "not ", "cannot", "may not", "won't", "no ")

_LEADING_CUE_RE = re.compile(
    r"^(?:" + "|".join(re.escape(c.strip()) for c in _NEGATION_CUES) + r")\b\s*"
)
_LEADING_CONJ_RE = re.compile(r"^(?:and|or)\b\s*")
_BARE_VERB_RE = re.compile(r"^(?:" + "|".join(_WRITE_VERBS) + r")\w*$")


def _is_bare_verb_item(segment: str) -> bool:
    """True iff ``segment`` is nothing but a (optionally cue/conjunction-
    prefixed) single write verb — one bare item of an enumerated list like
    "Never create, update, ... or modify", not an independent clause with
    its own object (e.g. "delete the connected account entirely")."""
    s = segment.strip().lower()
    s = _LEADING_CUE_RE.sub("", s, count=1)
    s = _LEADING_CONJ_RE.sub("", s, count=1)
    return bool(_BARE_VERB_RE.match(s))


# A contrastive/causal conjunction ("but", "though", "since", ...) reverses
# or breaks negation scope exactly the way a comma splice joining two
# independent asks already does below — "It will never sit idle since it
# will actually create new issues automatically" has "never" appear before
# "create" in the very same comma-less sentence, but "never" negates "sit
# idle", not the unrelated "create" ask "since" introduces afterward.
# `is_read_only_capabilities`'s own scope check only ever looks at whether
# a cue appears anywhere earlier in the same clause (see its docstring: "a
# negation earlier in the same clause covers a verb that follows it") —
# with no comma to trigger `_split_clauses`' existing clause boundary, nothing
# stopped an unrelated earlier "never" from laundering a real, unnegated ask
# on the far side of one of these conjunctions. Confirmed live pre-fix:
# `is_read_only_capabilities("It will never merely watch idly since it will
# actually create new issues automatically.")` returned `True`. Splitting on
# these conjunctions too — the comma-less sibling of the existing comma
# boundary — closes it.
_CONTRAST_CONJUNCTIONS = (
    "but", "though", "although", "however", "yet", "since", "because", "while", "except",
)
_CONTRAST_BOUNDARY_RE = re.compile(
    r"\b(?:" + "|".join(_CONTRAST_CONJUNCTIONS) + r")\b", re.IGNORECASE
)


def _split_on_contrast(clause: str) -> list[str]:
    """Further split one clause on a contrastive/causal conjunction — see
    `_CONTRAST_BOUNDARY_RE`'s own comment. Empty/whitespace-only pieces (left
    behind by a leading conjunction, or two adjacent ones) are dropped."""
    return [p for p in _CONTRAST_BOUNDARY_RE.split(clause) if p.strip()]


def _split_clauses(text: str) -> list[str]:
    """Split ``text`` into clauses for negation-scope checking.

    A sentence that is one bare, comma-separated list of write verbs
    sharing a single trailing object ("Never create, update, ... or modify
    anything on any connected account") stays one clause, so a leading
    negation covers the whole list. Any OTHER comma inside a sentence is a
    genuine clause boundary: a comma splice joining two independent asks
    ("Never trash old drafts, delete the connected account entirely") must
    not let the first ask's negation launder the second, unrelated one —
    the comma-joined sibling of the semicolon/period case below. Each
    resulting clause is then further split on a contrastive/causal
    conjunction (`_split_on_contrast`) — the comma-less sibling of the same
    problem, see `_CONTRAST_BOUNDARY_RE`'s own comment.
    """
    clauses = []
    for sentence in re.split(r"[.;]\s*", text):
        segments = re.split(r",\s*", sentence)
        if len(segments) == 1 or all(_is_bare_verb_item(seg) for seg in segments[:-1]):
            clauses.append(sentence)
        else:
            clauses.extend(segments)
    out: list[str] = []
    for clause in clauses:
        out.extend(_split_on_contrast(clause))
    return out


def is_read_only_capabilities(text: str) -> bool:
    """True iff ``text`` never asks, unnegated, for a write-capable tool.

    Pure function, no I/O — the same shape of law as ranking.py's confidence
    bar: a capabilities string ships only if every write verb in it is
    itself preceded, within the same clause, by a negation cue. Splits on
    sentence-ish boundaries (and, per ``_split_clauses``, on any comma that
    isn't just enumerating a bare verb list) so a negation earlier in the
    same clause covers a verb that follows it, but neither a negation in a
    *different* clause nor one that only trails a verb later in the *same*
    clause (e.g. "Post the daily report, but never trust automation
    blindly") can launder a real, unnegated ask — the cue must actually
    come first.
    """
    for clause in _split_clauses(text):
        lowered = clause.lower()
        for verb in _WRITE_VERBS:
            for m in re.finditer(rf"\b{verb}\w*\b", lowered):
                before = lowered[: m.start()]
                if not any(cue in before for cue in _NEGATION_CUES):
                    return False
    return True


def gateway_url(slug: str) -> str:
    """The real Arcade MCP URL a connected gateway is reachable at."""
    if not slug or "/" in slug or " " in slug:
        raise ValueError(f"not a valid gateway slug: {slug!r}")
    return f"https://api.arcade.dev/mcp/{slug}"
