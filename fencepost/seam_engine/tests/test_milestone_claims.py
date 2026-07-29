"""Tests for `seam_engine.milestone_claims` -- the shared `milestone #N`
claim-phrase law.

`milestone-closed-never-released/detector.py` (task 383) and
`release-claims-open-milestone/detector.py` (task 385) each carried their
own, textually-identical `_CLAIM_RE` regex -- the second file's own
comment claimed it "mirrors ... verbatim", but nothing imported one from
the other. This is the same "reused verbatim... not a second copy of it
drifting apart" gap task 389 found and fixed for `#N` extraction
(`seam_engine.references`), found here a second time and fixed the same
way before a third recipe (`milestone-closed-not-tweeted`, task 390) could
make it worse by adding a fourth copy. This module is now the one real
source; these tests check its own behavior directly, and
`TestAllThreeDetectorsShareTheLaw` below is the regression test that would
go red the moment any of the three recipes' detectors goes back to
defining its own local copy instead of importing this one.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from seam_engine.milestone_claims import MILESTONE_CLAIM_RE, claimed_milestone_numbers

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]


def _load_detector(recipe_slug: str, test_module_name: str):
    """Load a recipe's `detector.py` the same way `seam_engine.recipes.
    load_detector` loads any recipe at runtime -- same discipline as
    `test_references.py`'s own `_load_detector`."""
    path = FENCEPOST_ROOT / "RECIPES" / recipe_slug / "detector.py"
    spec = importlib.util.spec_from_file_location(test_module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[test_module_name] = module
    spec.loader.exec_module(module)
    return module


class TestClaimedMilestoneNumbers:
    def test_single_claim(self) -> None:
        assert claimed_milestone_numbers("this ships milestone #12") == [12]

    def test_multiple_claims_in_order(self) -> None:
        assert claimed_milestone_numbers("milestone #1 and milestone #2 both shipped") == [1, 2]

    def test_no_claim(self) -> None:
        assert claimed_milestone_numbers("routine cleanup, nothing here") == []

    def test_bare_hash_with_no_milestone_word_is_not_a_claim(self) -> None:
        assert claimed_milestone_numbers("see #42 for background") == []

    def test_case_insensitive(self) -> None:
        assert claimed_milestone_numbers("MILESTONE #7 is done") == [7]

    def test_requires_whitespace_between_the_word_and_the_hash(self) -> None:
        assert claimed_milestone_numbers("milestone#7 is done") == []


class TestMilestoneClaimRe:
    def test_pattern_source(self) -> None:
        assert MILESTONE_CLAIM_RE.pattern == r"\bmilestone\s+#(\d+)\b"


class TestAllThreeDetectorsShareTheLaw:
    """The regression test: all three `milestone #N`-claim recipes must
    bind their own `_claimed_milestone_numbers` name to THIS module's
    function object, not to a second, independently-defined one --
    identity, not textual coincidence."""

    def test_milestone_closed_never_released_binds_the_shared_function(self) -> None:
        detector = _load_detector(
            "milestone-closed-never-released",
            "seam_engine._recipe_milestone_closed_never_released_claims_test",
        )
        assert detector._claimed_milestone_numbers is claimed_milestone_numbers

    def test_release_claims_open_milestone_binds_the_shared_function(self) -> None:
        detector = _load_detector(
            "release-claims-open-milestone",
            "seam_engine._recipe_release_claims_open_milestone_claims_test",
        )
        assert detector._claimed_milestone_numbers is claimed_milestone_numbers

    def test_milestone_closed_not_tweeted_binds_the_shared_function(self) -> None:
        detector = _load_detector(
            "milestone-closed-not-tweeted",
            "seam_engine._recipe_milestone_closed_not_tweeted_claims_test",
        )
        assert detector._claimed_milestone_numbers is claimed_milestone_numbers
