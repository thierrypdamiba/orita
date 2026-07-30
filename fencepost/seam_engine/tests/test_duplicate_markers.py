"""Tests for `seam_engine.duplicate_markers` -- the shared "duplicate of
#N" marker law.

Task 400: `duplicate-issue-still-open/detector.py` first wrote this regex
(the seventh real recipe). `duplicate-pr-still-open/detector.py` (task 400)
needs the identical grammar for a second data source (a PR body instead of
an issue body). This module is now the one real source; these tests check
its own behavior directly, and `TestBothDetectorsShareTheLaw` below is the
regression test that would go red the moment either recipe's detector goes
back to defining its own local copy instead of importing this one.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from seam_engine.duplicate_markers import DUPLICATE_MARKER_RE, named_duplicate_of

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]


def _load_detector(recipe_slug: str, test_module_name: str):
    path = FENCEPOST_ROOT / "RECIPES" / recipe_slug / "detector.py"
    spec = importlib.util.spec_from_file_location(test_module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[test_module_name] = module
    spec.loader.exec_module(module)
    return module


class TestNamedDuplicateOf:
    def test_duplicate_of_hash(self) -> None:
        assert named_duplicate_of("Duplicate of #700") == 700

    def test_dup_of_hash(self) -> None:
        assert named_duplicate_of("dup of #703") == 703

    def test_duplicate_colon_hash(self) -> None:
        assert named_duplicate_of("Duplicate: #705") == 705

    def test_duplicate_bare_hash(self) -> None:
        assert named_duplicate_of("duplicate #705") == 705

    def test_no_marker(self) -> None:
        assert named_duplicate_of("A regular bug report, no duplicate mention at all.") is None

    def test_dupe_word_not_matched(self) -> None:
        # "dupe" is not "dup"/"duplicate" -- the `\b` boundary right after
        # "dup" keeps this from misfiring on ordinary prose.
        assert named_duplicate_of("This is not a dupe situation, see #700 for a different reason") is None


class TestDuplicateMarkerRe:
    def test_pattern_source(self) -> None:
        assert DUPLICATE_MARKER_RE.pattern == r"\bdup(?:licate)?\s*(?:of|:)?\s+#(\d+)\b"


class TestBothDetectorsShareTheLaw:
    """Object identity, not regex-pattern identity -- `re.compile()` memoizes
    identical patterns to the same cached object, so a regex-object identity
    check can stay green even after an import is broken (task 394's own
    lesson). Checking the bound FUNCTION object avoids that trap."""

    def test_duplicate_issue_still_open_detector_binds_the_shared_function(self) -> None:
        detector = _load_detector(
            "duplicate-issue-still-open", "seam_engine._recipe_duplicate_issue_still_open_markers_test"
        )
        assert detector._named_duplicate_of is named_duplicate_of

    def test_duplicate_pr_still_open_detector_binds_the_shared_function(self) -> None:
        detector = _load_detector(
            "duplicate-pr-still-open", "seam_engine._recipe_duplicate_pr_still_open_markers_test"
        )
        assert detector._named_duplicate_of is named_duplicate_of
