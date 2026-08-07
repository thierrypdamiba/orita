"""ROADMAP.md #584. `docs/fencepost/connect.html`'s walkthrough step 2 tells
a forker to "Confirm every tool offered starts with `Get`, `List`, `Read`,
`Search`, `Count`, or is `WhoAmI` — the same law SCOPES.md swears to." That
sentence is a second, hand-typed copy of `SCOPES.md`'s own oath bullet
(`Get*`, `List*`, `Read*`, `Search*`, `Count*`, `WhoAmI` — and nothing
else.), cited as identical to it but never structurally checked against it.

`test_connect_doctrine.py` already proves the page quotes
`gateway.READ_ONLY_CAPABILITIES` verbatim and names the dedicated demo
account -- it never touches this second, independent verb list.
`test_recipes_doctrine.py` already has a structural parser for SCOPES.md's
oath bullet, but only ever points it at recipe manifests, never at this
page. The exact "two authors independently typing the same six tokens"
class of bug this codebase has closed before (task 156's recipe count,
task 160's connect URL) -- open here until now.

This file parses both sides structurally (never a third hardcoded copy of
the six tokens) and proves a real drift in either source flips it red.
"""
from __future__ import annotations

import re
from pathlib import Path

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = FENCEPOST_ROOT.parent
SCOPES_MD = FENCEPOST_ROOT / "SCOPES.md"
CONNECT_HTML = REPO_ROOT / "docs" / "fencepost" / "connect.html"

# Same regex shape as test_recipes_doctrine.py's _parse_oath_line -- each
# doctrine file re-derives structurally from the source of truth rather than
# importing another test file's private parser (the established discipline
# test_recipes_doctrine.py's own comment names for test_consent_doctrine.py
# and scopes_completeness_check.py).
_OATH_LINE_RE = re.compile(r"^-\s*((?:`[^`]+`,?\s*)+)—\s*and nothing else\.\s*$", re.MULTILINE)
_BACKTICK_TOKEN_RE = re.compile(r"`([^`]+)`")

# connect.html's own sentence: "Confirm every tool offered starts with
# <code>Get</code>, <code>List</code>, ..., or is <code>WhoAmI</code> —"
_WALKTHROUGH_VERB_SENTENCE_RE = re.compile(
    r"Confirm every tool offered\s+starts with(.+?)the\s+same law", re.DOTALL
)
_CODE_TOKEN_RE = re.compile(r"<code>([^<]+)</code>")


def _parse_oath_tokens(scopes_text: str) -> tuple[frozenset[str], frozenset[str]]:
    """SCOPES.md's oath bullet -> (prefixes with trailing '*' stripped,
    exact-match tokens)."""
    match = _OATH_LINE_RE.search(scopes_text)
    assert match, (
        "SCOPES.md's oath bullet ('...— and nothing else.') was not found or "
        "has been reshaped -- this parser needs updating before it can be trusted"
    )
    tokens = _BACKTICK_TOKEN_RE.findall(match.group(1))
    assert tokens, "SCOPES.md's oath bullet matched but no backtick-quoted tokens were found inside it"
    prefixes = frozenset(t[:-1] for t in tokens if t.endswith("*"))
    exact = frozenset(t for t in tokens if not t.endswith("*"))
    return prefixes, exact


def _parse_walkthrough_verb_tokens(html: str) -> frozenset[str]:
    """connect.html's "Confirm every tool offered starts with ... the same
    law" sentence -> the set of bare <code>...</code> verb tokens inside it
    (order- and whitespace-insensitive; the sentence itself supplies "or is"
    for the one exact-match token, so no prefix/exact distinction is parsed
    on this side -- see test below for why that's still a sound check)."""
    match = _WALKTHROUGH_VERB_SENTENCE_RE.search(html)
    assert match, (
        "connect.html's 'Confirm every tool offered starts with ... the "
        "same law' sentence was not found or has been reshaped -- this "
        "parser needs updating before it can be trusted"
    )
    tokens = _CODE_TOKEN_RE.findall(match.group(1))
    assert tokens, "the walkthrough verb sentence matched but no <code>...</code> tokens were found inside it"
    return frozenset(tokens)


def _scopes_md_text() -> str:
    assert SCOPES_MD.exists(), "SCOPES.md must exist"
    return SCOPES_MD.read_text(encoding="utf-8")


def _connect_html_text() -> str:
    assert CONNECT_HTML.exists(), "connect.html must exist"
    return CONNECT_HTML.read_text(encoding="utf-8")


def test_scopes_oath_parses_today():
    prefixes, exact = _parse_oath_tokens(_scopes_md_text())
    assert prefixes == frozenset({"Get", "List", "Read", "Search", "Count"})
    assert exact == frozenset({"WhoAmI"})


def test_walkthrough_verb_sentence_parses_today():
    tokens = _parse_walkthrough_verb_tokens(_connect_html_text())
    assert tokens == frozenset({"Get", "List", "Read", "Search", "Count", "WhoAmI"})


def test_walkthrough_verb_list_matches_scopes_oath_exactly():
    """The real check: connect.html's hand-typed verb list must name
    exactly the same tokens as SCOPES.md's oath bullet -- no fewer (a
    forker under-confirming and missing a real write tool), no more (a
    forker told to accept a verb the oath never actually allows)."""
    prefixes, exact = _parse_oath_tokens(_scopes_md_text())
    walkthrough_tokens = _parse_walkthrough_verb_tokens(_connect_html_text())
    assert walkthrough_tokens == (prefixes | exact)


def test_a_dropped_oath_verb_would_flip_this_check_red():
    """Mutation-based hand-verification: SCOPES.md loses a verb (the
    plausible future edit the recipe family keeps growing into -- see
    ROADMAP.md #581's `issue-comment-dangling-reference`), connect.html
    stays as it is today -- the two must disagree."""
    mutated_scopes = _scopes_md_text().replace("`Search*`, ", "")
    prefixes, exact = _parse_oath_tokens(mutated_scopes)
    assert "Search" not in prefixes
    walkthrough_tokens = _parse_walkthrough_verb_tokens(_connect_html_text())
    assert walkthrough_tokens != (prefixes | exact)


def test_a_stale_walkthrough_sentence_would_flip_this_check_red():
    """The inverse mutation: connect.html's own sentence loses a verb,
    SCOPES.md stays as it is today -- the two must disagree."""
    mutated_html = _connect_html_text().replace("<code>Count</code>, ", "", 1)
    prefixes, exact = _parse_oath_tokens(_scopes_md_text())
    walkthrough_tokens = _parse_walkthrough_verb_tokens(mutated_html)
    assert walkthrough_tokens != (prefixes | exact)
