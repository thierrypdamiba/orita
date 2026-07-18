"""Tests for ROADMAP.md #127: ONBOARDING.md's "minute 3" and CONNECT.md's
step 4 each hand-type "four tools" naming the non-WIP subset of
`seam_engine.server`'s registered catalog (`list_repo_commits`,
`get_latest_release`, `get_recent_x_posts`, `seam_scan`) -- the identical
drift risk `test_readme_tool_count.py` (ROADMAP.md #118) already closed for
README.md's "Six read-only tools" claim, just never extended to these two
other hand-typed counts. `gmail_calendar_scan` and `combined_scan_preview`
are deliberately left out of both documents (ROADMAP.md #16/#113: fixture-
only, not a live read) -- correct today, but nothing structural enforced it,
so a third tool graduating out of WIP (or a new tool landing) could drift
these counts silently, the exact "two authors independently typing the same
thing" failure `wall.py`'s own docstring warns about.

Nothing here hardcodes the four names a second time. The "core" (non-WIP)
subset is derived structurally off each tool's own `ToolOutput.description`
-- the same WIP-labeled-return-annotation signal ROADMAP.md #113 built into
`gmail_calendar_scan`/`combined_scan_preview` on purpose (both start their
description with the literal word "WIP") -- so these tests read the live
catalog, not a belief about it, the same introspection pattern
`badge.py`/`test_readme_tool_count.py` already use.
"""
from __future__ import annotations

import re
from pathlib import Path

from seam_engine.server import app

_FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
ONBOARDING = _FENCEPOST_ROOT / "ONBOARDING.md"
CONNECT = _FENCEPOST_ROOT / "CONNECT.md"

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def _all_tool_names() -> set[str]:
    """Every tool's real python function name, WIP or not."""
    return {mat_tool.tool.__name__ for mat_tool in app._catalog}  # noqa: SLF001 -- same boundary badge.py/test_readme_tool_count.py already use


def _core_tool_names() -> list[str]:
    """The live catalog's non-WIP tools, by real function name -- WIP-ness
    read off each tool's own `ToolOutput.description` (must start with the
    literal word "WIP"), never a second hardcoded list."""
    names = []
    for mat_tool in app._catalog:  # noqa: SLF001
        description = mat_tool.definition.output.description or ""
        if description.startswith("WIP"):
            continue
        names.append(mat_tool.tool.__name__)
    return names


def _onboarding_minute_three_paragraph() -> str:
    text = ONBOARDING.read_text()
    match = re.search(r"### minute 3.*?\n\n```.*?```\n\n(.+?)\n\n", text, re.DOTALL)
    assert match, "ONBOARDING.md has no 'minute 3' paragraph to check"
    return match.group(1)


def _connect_step_four_paragraph() -> str:
    text = CONNECT.read_text()
    match = re.search(r"### 4 —.*?\n\n```.*?```\n\n(.+?)\n\n", text, re.DOTALL)
    assert match, "CONNECT.md has no step 4 paragraph to check"
    return match.group(1)


def test_onboarding_minute_three_tool_count_matches_the_live_core_catalog():
    paragraph = _onboarding_minute_three_paragraph()
    match = re.search(r"\b([A-Za-z]+) tools come up\b", paragraph)
    assert match, paragraph
    word = match.group(1).lower()
    assert word in _NUMBER_WORDS, f"unrecognized count word: {word!r}"
    stated_count = _NUMBER_WORDS[word]
    core = _core_tool_names()
    assert stated_count == len(core), (
        f"ONBOARDING.md says {word!r} ({stated_count}) tools come up, "
        f"but the live catalog's non-WIP tools are {core} ({len(core)})"
    )


def test_onboarding_minute_three_names_exactly_the_core_tools():
    paragraph = _onboarding_minute_three_paragraph()
    quoted = set(re.findall(r"`([a-z_]+)`", paragraph))
    named_tools = quoted & _all_tool_names()
    assert named_tools == set(_core_tool_names()), (
        f"ONBOARDING.md's minute-3 paragraph names {sorted(named_tools)}, "
        f"but the live catalog's non-WIP core is {sorted(_core_tool_names())}"
    )


def test_connect_step_four_tool_count_matches_the_live_core_catalog():
    paragraph = _connect_step_four_paragraph()
    match = re.search(r"\b([A-Za-z]+) tools documented\b", paragraph)
    assert match, paragraph
    word = match.group(1).lower()
    assert word in _NUMBER_WORDS, f"unrecognized count word: {word!r}"
    stated_count = _NUMBER_WORDS[word]
    core = _core_tool_names()
    assert stated_count == len(core), (
        f"CONNECT.md says {word!r} ({stated_count}) tools documented, "
        f"but the live catalog's non-WIP tools are {core} ({len(core)})"
    )


def test_wip_tools_are_excluded_from_both_documents():
    onboarding_paragraph = _onboarding_minute_three_paragraph()
    connect_paragraph = _connect_step_four_paragraph()
    wip_names = _all_tool_names() - set(_core_tool_names())
    assert wip_names, "expected at least one WIP tool in the live catalog"
    for name in wip_names:
        assert name not in onboarding_paragraph, (
            f"ONBOARDING.md's minute-3 paragraph names WIP tool {name!r} "
            "as if it were live"
        )
        assert name not in connect_paragraph, (
            f"CONNECT.md's step-4 paragraph names WIP tool {name!r} "
            "as if it were live"
        )
