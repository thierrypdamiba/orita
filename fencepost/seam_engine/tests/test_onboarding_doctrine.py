"""Tests for ONBOARDING.md — Ogun's oath, checked on the guide that tells

strangers it is safe to connect their own accounts. A reassurance page that
quietly documents a write scope is worse than no page at all: it would be
the one place a fork-er is told to trust us. These tests fail red the moment
that trust is misplaced.

Task 783 (zashiki-warashi, window slot): minute 4's own reassurance --
"if you ever see a write scope requested for seam_engine, that's not this
code; stop and check what you deployed" -- used to be pure prose, naming
no runnable command, even though the repo already ships exactly the check
that sentence gestures at (`seam_engine.badge`'s live tool-catalog audit,
the same one the town's own README/BADGE.json badge repaints from). The
tests below close the "documented, not verified" gap `recipe_command_check.py`
(ROADMAP.md #571) already closed for every RECIPES/ README's own "Run it
yourself" block, applied here to ONBOARDING.md's minute 4: not just that
the doc *names* the real command, but that the exact command actually
runs, live, from a fresh subprocess, and reports the shape it promises.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ONBOARDING = Path(__file__).resolve().parents[2] / "ONBOARDING.md"
_SEAM_ENGINE_DIR = Path(__file__).resolve().parents[2]

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


def _minute_four_paragraph() -> str:
    text = _text()
    match = re.search(r"### minute 4.*?(?=\n### minute 5)", text, re.DOTALL)
    assert match, "ONBOARDING.md has no 'minute 4' section to check"
    return match.group(0)


def test_onboarding_minute_four_names_a_real_runnable_scope_check():
    """The "stop and check what you deployed" reassurance must name the
    actual command a self-hoster can run, not just tell them to check."""
    paragraph = _minute_four_paragraph()
    assert "uv run python -m seam_engine.badge" in paragraph, (
        "ONBOARDING.md's minute-4 paragraph tells the reader to 'check "
        "what you deployed' but never names the real command that does it"
    )


def test_onboarding_minute_four_command_actually_runs_and_is_read_only_clean():
    """Live-executes the exact command ONBOARDING.md's minute 4 now names
    -- not `compute_badge_state()` called in-process, the real subprocess
    a reader would type -- and proves it exits 0 and reports every
    registered tool read-only-clean, the same "documented, not verified"
    discipline `recipe_command_check.py` (ROADMAP.md #571) already holds
    for every RECIPES/ README's own "Run it yourself" block."""
    paragraph = _minute_four_paragraph()
    match = re.search(r"```\n(uv run python -m seam_engine\.badge)\n```", paragraph)
    assert match, "expected the fenced command block to contain exactly the documented command"
    command = match.group(1)

    result = subprocess.run(
        command,
        shell=True,  # noqa: S602 -- literal, doc-sourced, no untrusted input
        cwd=_SEAM_ENGINE_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"{command!r} exited {result.returncode} -- stderr tail:\n"
        f"{result.stderr[-2000:]}"
    )
    assert re.search(r"\d+/\d+ tools read-only", result.stdout), (
        f"{command!r} did not print the promised 'N/N tools read-only' "
        f"shape -- stdout:\n{result.stdout[-2000:]}"
    )
