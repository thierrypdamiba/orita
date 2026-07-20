"""Tests for ROADMAP.md #165: ONBOARDING.md's minute-1 paragraph told a
first-time forker running `curl -LsSf https://astral.sh/uv/install.sh | sh`,
`uv sync --extra dev`, `uv run python -m pytest -q` verbatim to expect it
would "print something like `42 passed`" -- real once (an early count),
never updated as the suite grew task by task, and never checked against the
live suite by anything: grep finds zero references to "42 passed" anywhere
in `tests/` before this task, unlike the sibling "four tools"/"Six
read-only tools" claims tasks 118/127 already guarded the same way for
ONBOARDING.md's own minute-3 paragraph and CONNECT.md's step 4.

Live, today: `uv run python -m pytest -q` from a clean `.venv` actually
prints "582 passed", not "42 passed" -- over 13x off, and it sits in the
exact paragraph whose stated purpose is "prove the engine is real before
you trust it," so a wildly wrong number undercuts the reassurance a
first-time forker is there to get.

Fixes the stale number to the real, live count and adds a structural
cross-check so it can't go stale silently again: the claimed number is
extracted from ONBOARDING.md's own minute-1 paragraph via regex (never
hand-typed twice), and the real count comes from actually invoking
pytest's own collector against this repo's real, live `tests/` tree
(`--collect-only -q`, parsed from its own real summary line), never a
second hand-typed number -- the same "read the live thing, not a belief
about it" discipline `test_readme_tool_count.py`/`test_onboarding_tool_
count.py` already hold for the sibling tool-count claims.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SEAM_ENGINE_ROOT = Path(__file__).resolve().parents[1]
ONBOARDING = SEAM_ENGINE_ROOT.parent / "ONBOARDING.md"


def _minute_one_paragraph() -> str:
    text = ONBOARDING.read_text()
    match = re.search(r"### minute 1.*?\n\n```.*?```\n\n(.+?)\n\n", text, re.DOTALL)
    assert match, "ONBOARDING.md has no 'minute 1' paragraph to check"
    return match.group(1)


def _claimed_test_count(paragraph: str) -> int:
    match = re.search(r"`(\d+) passed`", paragraph)
    assert match, f"no '`N passed`' claim found in: {paragraph!r}"
    return int(match.group(1))


def _live_collected_test_count() -> int:
    """Actually invoke pytest's own collector against the real tests/ tree
    -- never a hand-typed number standing in for it."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=SEAM_ENGINE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    match = re.search(r"(\d+) tests? collected", result.stdout)
    assert match, f"could not parse a collected-count summary from:\n{result.stdout}"
    return int(match.group(1))


def test_minute_one_paragraph_has_a_passed_count_claim():
    paragraph = _minute_one_paragraph()
    assert "passed" in paragraph, paragraph


def test_minute_one_claimed_count_matches_the_live_suite():
    claimed = _claimed_test_count(_minute_one_paragraph())
    live = _live_collected_test_count()
    assert claimed == live, (
        f"ONBOARDING.md's minute-1 paragraph says 'something like "
        f"`{claimed} passed`', but the real, live suite collects {live} "
        "tests today -- update the doc to match reality"
    )


def test_onboarding_no_longer_says_42_passed():
    # Regression pin: the real, historical stale claim this task fixed.
    assert "`42 passed`" not in ONBOARDING.read_text()


def test_claimed_test_count_extraction_is_structural_not_a_coincidence():
    # Prove the regex reads the number, not a hardcoded belief about it,
    # against synthetic text the real file can't coincidentally satisfy.
    synthetic = "that should print something like `999 passed`. trust it."
    assert _claimed_test_count(synthetic) == 999
