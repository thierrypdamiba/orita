"""Tests for `seam_engine.references` — the shared `#N` extraction law.

Task 389: `dangling-issue-reference/detector.py` (task 368) and
`mention-dangling-reference/detector.py` (task 388) each carried their own,
textually-identical, independently-typed `_REF_RE` regex, despite the
second file's own docstring claiming they were "reused verbatim... not a
second copy of it drifting apart." Nothing in the code enforced that claim.
This module is now the one real source; these tests check its own behavior
directly, and `test_both_detectors_bind_the_shared_function` below is the
regression test that would go red the moment either recipe's detector goes
back to defining its own local copy instead of importing this one.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from seam_engine.references import REF_RE, referenced_numbers

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]


def _load_detector(recipe_slug: str, test_module_name: str):
    """Load a recipe's `detector.py` the same way `seam_engine.recipes.
    load_detector` loads any recipe at runtime -- same discipline as
    `test_dangling_issue_reference_detector.py` and
    `test_mention_dangling_reference_detector.py`."""
    path = FENCEPOST_ROOT / "RECIPES" / recipe_slug / "detector.py"
    spec = importlib.util.spec_from_file_location(test_module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[test_module_name] = module
    spec.loader.exec_module(module)
    return module


class TestReferencedNumbers:
    def test_single_reference(self) -> None:
        assert referenced_numbers("part of #12") == [12]

    def test_multiple_references_in_order(self) -> None:
        assert referenced_numbers("relates to #1 and #2") == [1, 2]

    def test_no_reference(self) -> None:
        assert referenced_numbers("routine cleanup, nothing here") == []

    def test_cross_repo_reference_excluded(self) -> None:
        assert referenced_numbers("see arcadeai/gasstation#42") == []

    def test_bare_repo_hash_excluded(self) -> None:
        assert referenced_numbers("see repo#42") == []

    def test_reference_at_start_of_text(self) -> None:
        assert referenced_numbers("#7 fixed") == [7]

    def test_reference_in_parens(self) -> None:
        assert referenced_numbers("(see #7)") == [7]

    def test_reference_followed_by_word_character_not_matched(self) -> None:
        # `#42a` is not GitHub's `#N` shorthand at all -- the `\b` boundary
        # in REF_RE keeps a trailing word character from being silently
        # dropped into a false #42 match.
        assert referenced_numbers("build#42a failed") == []


class TestRefRe:
    def test_ref_re_is_a_compiled_pattern_with_expected_source(self) -> None:
        assert REF_RE.pattern == r"(?<![\w/])#(\d+)\b"


class TestBothDetectorsShareTheLaw:
    """The regression test: both `#N`-extraction recipes must bind their
    own `_referenced_numbers` name to THIS module's function object, not
    to a second, independently-defined one. This is what actually makes
    task 388's "not a second copy of it drifting apart" claim true --
    identity, not textual coincidence."""

    def test_dangling_issue_reference_detector_binds_the_shared_function(self) -> None:
        dangling_detector = _load_detector(
            "dangling-issue-reference", "seam_engine._recipe_dangling_issue_reference_refs_test"
        )
        assert dangling_detector._referenced_numbers is referenced_numbers

    def test_mention_dangling_reference_detector_binds_the_shared_function(self) -> None:
        mention_detector = _load_detector(
            "mention-dangling-reference", "seam_engine._recipe_mention_dangling_reference_refs_test"
        )
        assert mention_detector._referenced_numbers is referenced_numbers
