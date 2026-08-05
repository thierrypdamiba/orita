"""Tests for `seam_engine.checklist` -- the shared GitHub task-list
checkbox ("- [ ] #N" / "- [x] #N") law.

`issue-closed-subissue-still-open` (task 530) first wrote this grammar as
its own local `_CHECKLIST_RE`/`_checklist_targets`. `issue-checklist-
complete-still-open` (task 558) needed the identical grammar for the
mirror-image seam one quadrant over and would have retyped it a second
time -- the same "textually identical... nothing stopping them from
drifting apart" shape `test_closing_keywords.py` already guards for the
closing-keyword family. Extracted to this shared module instead; both real
consumers import `checklist_targets` from here, aliased to their own
existing `_checklist_targets` module-level name.

`TestBothDetectorsShareTheLaw` below is the regression test: it is
supposed to go red the moment either recipe's detector goes back to
defining its own local copy instead of importing this one -- checked the
same two ways `test_closing_keywords.py`'s own regression class checks its
nine consumers: functional parity (cheap, but `re.compile` memoizes
identical patterns so this alone can't prove import-vs-coincidence), and
the detector's own SOURCE TEXT naming the real import with no local
`re.compile(` of its own (the actual regression signal).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from seam_engine.checklist import CHECKLIST_RE, checklist_targets

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]


def _load_detector(recipe_slug: str, test_module_name: str):
    """Load a recipe's `detector.py` the same way `seam_engine.recipes.
    load_detector` loads any recipe at runtime -- same discipline as
    `test_closing_keywords.py`'s own `_load_detector`."""
    path = FENCEPOST_ROOT / "RECIPES" / recipe_slug / "detector.py"
    spec = importlib.util.spec_from_file_location(test_module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[test_module_name] = module
    spec.loader.exec_module(module)
    return module


def _detector_source(recipe_slug: str) -> str:
    return (FENCEPOST_ROOT / "RECIPES" / recipe_slug / "detector.py").read_text()


class TestChecklistTargets:
    def test_extracts_a_single_checked_and_unchecked_reference(self) -> None:
        assert checklist_targets("- [ ] #1\n- [x] #2\n") == [1, 2]

    def test_ignores_a_bare_mention_with_no_checkbox(self) -> None:
        assert checklist_targets("See #5 for related context.") == []

    def test_tolerates_leading_whitespace_and_mixed_case_mark(self) -> None:
        assert checklist_targets("  - [X] #7\n") == [7]

    def test_empty_body_yields_no_targets(self) -> None:
        assert checklist_targets("") == []

    def test_duplicate_reference_is_kept_not_deduplicated(self) -> None:
        # Duplicates kept -- see module docstring. Callers dedupe at their
        # own call site if their own seam needs the distinct set.
        assert checklist_targets("- [x] #9\n- [x] #9\n- [x] #3\n") == [9, 9, 3]

    def test_checked_and_unchecked_marks_both_match(self) -> None:
        assert CHECKLIST_RE.findall("- [ ] #1\n- [x] #2\n- [X] #3\n") == [
            (" ", "1"), ("x", "2"), ("X", "3"),
        ]


class TestBothDetectorsShareTheLaw:
    """The regression test -- see module docstring."""

    _CASES = [
        "issue-closed-subissue-still-open",
        "issue-checklist-complete-still-open",
    ]

    def test_functional_parity(self) -> None:
        for slug in self._CASES:
            detector = _load_detector(
                slug, f"seam_engine._recipe_{slug.replace('-', '_')}_checklist_test"
            )
            local_fn = detector._checklist_targets
            assert local_fn("- [ ] #1\n- [x] #1\n") == checklist_targets("- [ ] #1\n- [x] #1\n")
            assert local_fn("- [ ] #1\n- [x] #1\n") == [1, 1]

    def test_source_imports_the_shared_module_not_a_local_copy(self) -> None:
        for slug in self._CASES:
            source = _detector_source(slug)
            assert "from seam_engine.checklist import checklist_targets" in source, (
                f"{slug}/detector.py no longer imports seam_engine.checklist"
            )
            assert "_CHECKLIST_RE = re.compile(" not in source, (
                f"{slug}/detector.py defines its own local _CHECKLIST_RE "
                "again instead of importing the shared one"
            )
