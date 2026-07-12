"""Tests for CONNECT.md and docs/fencepost/connect.html — the "Fork &

Connect your own" walkthrough (ROADMAP row 14). The capabilities string
quoted on the page is not free text: it must be the *exact* constant in
gateway.py, verbatim, in both the repo doc and the live site page, and the
page must say plainly that the town dogfoods a dedicated demo account and
never a real person's login. These fail red the moment doc and code drift,
or the safety framing goes soft.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from seam_engine.gateway import (
    ARCADE_CONNECT_CLIENTS_DOC_URL,
    ARCADE_GATEWAY_DASHBOARD_URL,
    READ_ONLY_CAPABILITIES,
)

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
CONNECT_MD = FENCEPOST_ROOT / "CONNECT.md"
CONNECT_HTML = FENCEPOST_ROOT.parent / "docs" / "fencepost" / "connect.html"
INDEX_HTML = FENCEPOST_ROOT.parent / "docs" / "fencepost" / "index.html"

FORBIDDEN_TOOLS = (
    "CreateFile",
    "UpdateFileLines",
    "CreateIssue",
    "MergePullRequest",
    "CreateRelease",
    "ManageLabels",
    "PostTweet",
    "ReplyToTweet",
    "SendEmail",
    "CreateDraft",
    "CreateEvent",
    "UpdateEvent",
    "DeleteEvent",
)

NEGATION_CUES = ("never", "cannot", "may not", "won't", "not ", "stop")


def _connect_md() -> str:
    assert CONNECT_MD.exists(), f"missing {CONNECT_MD} — task 14 isn't done until this file exists"
    return CONNECT_MD.read_text(encoding="utf-8")


def _connect_html() -> str:
    assert CONNECT_HTML.exists(), f"missing {CONNECT_HTML} — the walkthrough must be ON the site"
    return CONNECT_HTML.read_text(encoding="utf-8")


def _index_html() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")


# --- CONNECT.md -------------------------------------------------------------


def test_connect_md_exists_and_is_not_a_stub():
    assert len(_connect_md()) > 2000, "CONNECT.md reads like a stub, not a walkthrough"


def test_connect_md_quotes_the_capabilities_string_verbatim():
    assert READ_ONLY_CAPABILITIES in _connect_md(), (
        "CONNECT.md must quote seam_engine.gateway.READ_ONLY_CAPABILITIES "
        "verbatim, not a paraphrase that can silently drift from the code"
    )


def test_connect_md_names_the_dedicated_demo_account_never_personal():
    text = _connect_md()
    assert "the-hand" in text
    lowered = text.lower()
    assert "dedicated" in lowered and ("demo account" in lowered or "demo project" in lowered)
    assert "personal" in lowered


def test_connect_md_links_straight_to_the_arcade_oauth_connect_flow():
    text = _connect_md()
    assert ARCADE_GATEWAY_DASHBOARD_URL in text
    assert ARCADE_CONNECT_CLIENTS_DOC_URL in text


def test_connect_md_covers_revocation():
    assert "revoke" in _connect_md().lower()


def test_connect_md_points_at_scopes_and_the_engine():
    text = _connect_md()
    assert "SCOPES.md" in text
    assert "gateway.py" in text


@pytest.mark.parametrize("tool", FORBIDDEN_TOOLS)
def test_connect_md_never_documents_a_forbidden_write_tool_as_usable(tool: str):
    text = _connect_md()
    for line in text.splitlines():
        if tool in line:
            lowered = line.lower()
            assert any(cue in lowered for cue in NEGATION_CUES), (
                f"CONNECT.md mentions the write-capable tool {tool!r} on a line "
                f"that does not negate it: {line!r}"
            )


# --- docs/fencepost/connect.html (the live site) -----------------------------


def test_connect_html_exists_on_the_site():
    assert len(_connect_html()) > 1500, "connect.html reads like a stub, not a walkthrough"


def test_connect_html_quotes_the_capabilities_string_verbatim():
    assert READ_ONLY_CAPABILITIES in _connect_html(), (
        "the live site page must quote the exact same capabilities string as "
        "the code and CONNECT.md, not a rephrasing"
    )


def test_connect_html_links_straight_to_the_arcade_oauth_connect_flow():
    html = _connect_html()
    assert f'href="{ARCADE_GATEWAY_DASHBOARD_URL}"' in html
    assert "the Arcade OAuth connect flow" in html


def test_connect_html_names_the_dedicated_demo_account_never_personal():
    html = _connect_html().lower()
    assert "the-hand" in html
    assert "dedicated" in html and "demo account" in html
    assert "personal" in html


def test_index_html_links_to_the_connect_walkthrough():
    index = _index_html()
    assert 'href="connect.html"' in index
