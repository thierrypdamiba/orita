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
"""
from __future__ import annotations

import re

# The exact string to paste into Arcade's Gateway Assistant, or into the
# "Description" field on https://api.arcade.dev/dashboard/mcp-gateways, when
# building your own Fencepost gateway. Arcade's tool matcher reads this and
# selects tools automatically — see docs.arcade.dev/en/guides/mcp-gateways.
READ_ONLY_CAPABILITIES = (
    "Read-only seam reconciliation: list and read GitHub commit history, "
    "releases, issues, and pull requests, and read a connected user's own "
    "X (Twitter) tweet history and mentions — solely to compare the two "
    "timelines and surface gaps between what shipped and what was "
    "announced. Never create, update, merge, label, delete, post, reply, "
    "send, or modify anything on any connected account."
)

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
