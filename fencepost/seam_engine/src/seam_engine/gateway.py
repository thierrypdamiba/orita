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
    "metadata, commit history, releases, issues, pull requests, "
    "repository activity, and stargazer counts, and read a connected "
    "user's own X (Twitter) tweet history, mentions, and account "
    "identity — solely to compare the two timelines and surface gaps "
    "between what shipped and what was announced. Never create, update, "
    "merge, label, delete, post, reply, send, or modify anything on any "
    "connected account."
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
        "ListRepositoryActivities": "repository activity",
        "CountStargazers": "stargazer",
        "GetLatestRelease": "release",
    },
    "x": {
        "GetUserTweets": "tweet history",
        "GetMyMentions": "mentions",
        "WhoAmI": "identity",
    },
}


def required_scopes_covered_by_capabilities(
    text: str = None,
    required_scopes: dict = None,
) -> dict[str, list[str]]:
    """Return, per toolkit, the ``REQUIRED_SCOPES`` tool names ``text`` does
    NOT name a covering keyword for — an empty list per toolkit means full
    coverage. Pure function, no I/O, same shape as ``is_read_only_capabilities``.

    Only checks toolkits present in ``_SCOPE_KEYWORDS`` (github, x) — gmail
    and google_calendar are v0.2, not yet part of this gateway's own oath.
    """
    text = READ_ONLY_CAPABILITIES if text is None else text
    required_scopes = REQUIRED_SCOPES if required_scopes is None else required_scopes
    lowered = text.lower()
    missing: dict[str, list[str]] = {}
    for toolkit, keywords in _SCOPE_KEYWORDS.items():
        gaps = [
            tool
            for tool in required_scopes.get(toolkit, frozenset())
            if keywords.get(tool, "").lower() not in lowered
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
)

# A verb only counts as a live ask if it isn't itself being ruled out.
_NEGATION_CUES = ("never", "not ", "cannot", "may not", "won't", "no ")


def is_read_only_capabilities(text: str) -> bool:
    """True iff ``text`` never asks, unnegated, for a write-capable tool.

    Pure function, no I/O — the same shape of law as ranking.py's confidence
    bar: a capabilities string ships only if every write verb in it appears
    strictly inside a negating clause (a sentence containing a negation cue).
    Splits on sentence-ish boundaries so a negation earlier in the same
    clause covers the verb, but a negation in a *different* sentence does not
    launder an unrelated ask.
    """
    clauses = re.split(r"[.;]\s*", text)
    for clause in clauses:
        lowered = clause.lower()
        negated = any(cue in lowered for cue in _NEGATION_CUES)
        if negated:
            continue
        for verb in _WRITE_VERBS:
            if re.search(rf"\b{verb}\w*\b", lowered):
                return False
    return True


def gateway_url(slug: str) -> str:
    """The real Arcade MCP URL a connected gateway is reachable at."""
    if not slug or "/" in slug or " " in slug:
        raise ValueError(f"not a valid gateway slug: {slug!r}")
    return f"https://api.arcade.dev/mcp/{slug}"
