"""Tests for ONBOARDING.md — Ogun's oath, checked on the guide that tells

strangers it is safe to connect their own accounts. A reassurance page that
quietly documents a write scope is worse than no page at all: it would be
the one place a fork-er is told to trust us. These tests fail red the moment
that trust is misplaced.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ONBOARDING = Path(__file__).resolve().parents[2] / "ONBOARDING.md"

# Every write-capable tool name SCOPES.md swears Fencepost never touches.
# If one of these substrings shows up in ONBOARDING.md, it may only appear
# on a line that also negates it (never/cannot/may not/won't/not/stop).
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
    "Trash",
    "Modify",
    "CreateEvent",
    "UpdateEvent",
    "DeleteEvent",
)

NEGATION_CUES = ("never", "cannot", "may not", "won't", "not ", "stop")


def _text() -> str:
    assert ONBOARDING.exists(), f"missing {ONBOARDING} — the guide task isn't done until this file exists"
    return ONBOARDING.read_text(encoding="utf-8")


def test_onboarding_file_exists_and_is_not_a_stub():
    text = _text()
    assert len(text) > 2000, "ONBOARDING.md reads like a stub, not a guide"


def test_onboarding_names_the_read_only_oath():
    text = _text()
    assert "SCOPES.md" in text
    assert "read-only" in text.lower() or "read only" in text.lower()


def test_onboarding_explains_the_road_no_god_holds_a_key():
    text = _text()
    # The reassurance section must ground itself in the town's own
    # architecture doc, not just assert trust-me.
    assert "Mortal World" in text or "the Road" in text


def test_onboarding_covers_revocation():
    text = _text()
    assert "revoke" in text.lower() or "revocable" in text.lower()


def test_onboarding_has_a_five_minute_self_host_walkthrough():
    text = _text()
    lowered = text.lower()
    for marker in ("minute 0", "minute 1", "minute 2"):
        assert marker in lowered, f"missing self-host step: {marker}"
    # Real, runnable commands — not just prose about commands.
    assert "uv sync" in text
    assert "pytest" in text


def test_onboarding_names_the_current_v0_boundary_honestly():
    text = _text()
    # Ogun's law forbids overclaiming: the guide must say what's not built
    # yet (Gmail/Calendar seam), not just what is.
    assert "v0.2" in text or "not built yet" in text.lower() or "isn't built yet" in text.lower()


@pytest.mark.parametrize("tool", FORBIDDEN_TOOLS)
def test_no_forbidden_write_tool_is_documented_as_usable(tool: str):
    text = _text()
    for line in text.splitlines():
        if tool in line:
            lowered = line.lower()
            assert any(cue in lowered for cue in NEGATION_CUES), (
                f"ONBOARDING.md mentions the write-capable tool {tool!r} on a line "
                f"that does not negate it: {line!r}"
            )


def test_onboarding_never_instructs_the_reader_to_grant_a_write_scope():
    text = _text().lower()
    for phrase in ("grant write access", "allow it to send", "allow it to post", "allow it to delete"):
        assert phrase not in text
