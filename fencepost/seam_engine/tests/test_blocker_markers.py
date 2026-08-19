"""Tests for `seam_engine.blocker_markers` -- the shared "blocked by #N" /
"blocked on #N" marker law.

Task 593 (`unblocked-issue-still-open/detector.py`, the sixty-first real
recipe) first wrote this regex. ROADMAP.md #869
(`unblocked-pr-still-open/detector.py`) needs the identical grammar for a
second data source (a PR body instead of an issue body). This module is
now the one real source; these tests check its own behavior directly, and
`TestBothDetectorsShareTheLaw` below is the regression test that would go
red the moment either recipe's detector goes back to defining its own
local copy instead of importing this one -- the identical shape
`test_duplicate_markers.py` already holds for the "duplicate of #N"
family.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from seam_engine.blocker_markers import BLOCKER_MARKER_RE, named_blocker_of

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]


def _load_detector(recipe_slug: str, test_module_name: str):
    path = FENCEPOST_ROOT / "RECIPES" / recipe_slug / "detector.py"
    spec = importlib.util.spec_from_file_location(test_module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[test_module_name] = module
    spec.loader.exec_module(module)
    return module


class TestNamedBlockerOf:
    def test_blocked_by_hash_n(self) -> None:
        assert named_blocker_of("Blocked by #900") == 900

    def test_blocked_on_hash_n(self) -> None:
        assert named_blocker_of("blocked on #903") == 903

    def test_blocked_colon_hash_n(self) -> None:
        assert named_blocker_of("Blocked: #905") == 905

    def test_bare_blocked_hash_n(self) -> None:
        assert named_blocker_of("blocked #905") == 905

    def test_no_marker_returns_none(self) -> None:
        assert named_blocker_of("A regular bug report, no blocker mention at all.") is None

    def test_unblocked_does_not_false_positive(self) -> None:
        # "unblocked" contains "blocked" as a literal substring but is not
        # the same word -- the leading `\b` must not let this slip
        # through, since there is no word boundary between "un" and
        # "blocked".
        assert named_blocker_of("This issue is now unblocked, see #900 for context") is None

    def test_blocks_forward_direction_does_not_match(self) -> None:
        # "blocks #N" (this record blocks another) is a different claim in
        # the opposite direction -- this grammar only reads a *self*-
        # declared dependency ("I am blocked by/on"), never the inverse.
        assert named_blocker_of("This blocks #900, not the other way around") is None


class TestNegatedBlockerMarkerIsNotAClaim:
    """A body that explicitly denies still being blocked must not be read
    as naming a live blocker anyway -- the same false-positive shape task
    612 fixed for `duplicate_markers.py`'s "duplicate of #N"."""

    def test_a_negated_blocker_marker_is_not_a_claim(self) -> None:
        assert named_blocker_of("This is not blocked by #10 anymore, we are good to go.") is None

    def test_no_longer_blocked_is_not_a_claim(self) -> None:
        assert named_blocker_of("No longer blocked by #10.") is None

    def test_isnt_blocked_is_not_a_claim(self) -> None:
        assert named_blocker_of("This isn't blocked on #12, go ahead.") is None

    def test_unnegated_marker_still_matches(self) -> None:
        # The negation check must not swallow a real, unnegated marker.
        assert named_blocker_of("Blocked by #900") == 900

    def test_negation_does_not_launder_a_later_genuine_marker(self) -> None:
        # A denial of one thing must not swallow an unrelated, real marker
        # sitting further along in the same body -- `finditer` keeps
        # walking past a skipped (negated) candidate to the next one.
        assert named_blocker_of("Not a fan of this, blocked by #10 for real.") == 10


class TestNegationDoesNotCrossASentenceBoundary:
    """Task 693 (Retrya): the shared `seam_engine.negation.is_negated`
    window used to search straight through a sentence boundary -- a
    negation word in a PRIOR, unrelated sentence silently swallowed a
    genuine blocker marker in the sentence that followed it. Reproduced
    live pre-fix: `named_blocker_of("Not fine. blocked by #10 anymore.")`
    returned `None`. See `seam_engine.negation`'s own docstring for the
    fix and the full blast radius."""

    def test_negation_in_a_prior_sentence_does_not_suppress_a_real_marker(self) -> None:
        assert named_blocker_of("Not fine. blocked by #10 anymore.") == 10


class TestBlockerMarkerRe:
    def test_pattern_source(self) -> None:
        assert BLOCKER_MARKER_RE.pattern == r"\bblocked\s*(?:by|on|:)?\s+#(\d+)\b"


class TestBothDetectorsShareTheLaw:
    """Object identity, not regex-pattern identity -- `re.compile()`
    memoizes identical patterns to the same cached object, so a regex-
    object identity check can stay green even after an import is broken.
    Checking the bound FUNCTION object avoids that trap -- the identical
    discipline `test_duplicate_markers.py::TestBothDetectorsShareTheLaw`
    already holds for the "duplicate of #N" family."""

    def test_unblocked_issue_still_open_detector_binds_the_shared_function(self) -> None:
        detector = _load_detector(
            "unblocked-issue-still-open", "seam_engine._recipe_unblocked_issue_still_open_markers_test"
        )
        assert detector._named_blocker_of is named_blocker_of

    def test_unblocked_pr_still_open_detector_binds_the_shared_function(self) -> None:
        detector = _load_detector(
            "unblocked-pr-still-open", "seam_engine._recipe_unblocked_pr_still_open_markers_test"
        )
        assert detector._named_blocker_of is named_blocker_of
