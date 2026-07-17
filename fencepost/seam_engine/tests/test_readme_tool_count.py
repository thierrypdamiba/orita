"""Tests for ROADMAP.md #118: README.md's "The engine" paragraph named
"Five read-only tools" after task 113 registered a sixth (`combined_scan_
preview`), while `BADGE.json` already said 6/6. Mirrors `test_badge.py`'s
introspection pattern: read the ACTUAL registered `seam_engine.server.app`
catalog rather than trusting a docstring, and structurally cross-check
README's own prose against it so the two can't drift apart again.
"""
from __future__ import annotations

import re
from pathlib import Path

from seam_engine.server import app

README = Path(__file__).resolve().parents[2] / "README.md"

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def _catalog_names() -> list[str]:
    return [mat_tool.definition.name for mat_tool in app._catalog]  # noqa: SLF001


def _engine_paragraph() -> str:
    text = README.read_text()
    match = re.search(r"## The engine\n\n(.+?)\n\n", text, re.DOTALL)
    assert match, "README.md has no '## The engine' paragraph to check"
    return match.group(1)


def test_readme_engine_paragraph_count_matches_the_live_catalog():
    paragraph = _engine_paragraph()
    match = re.search(r"\b([A-Za-z]+) read-only tools\b", paragraph)
    assert match, paragraph
    word = match.group(1).lower()
    assert word in _NUMBER_WORDS, f"unrecognized count word: {word!r}"
    stated_count = _NUMBER_WORDS[word]
    assert stated_count == len(_catalog_names()), (
        f"README says {word!r} ({stated_count}) tools, "
        f"but the live server registers {len(_catalog_names())}"
    )


def test_readme_engine_paragraph_names_combined_scan_preview():
    paragraph = _engine_paragraph()
    assert "combined_scan_preview" in paragraph, paragraph


def test_readme_no_longer_says_five_read_only_tools():
    assert "Five read-only tools" not in README.read_text()
