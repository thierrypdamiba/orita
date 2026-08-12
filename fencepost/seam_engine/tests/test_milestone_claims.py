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


class TestNegatedClaimIsNotAClaim:
    """Task 613: `claimed_milestone_numbers` used to be a bare
    `MILESTONE_CLAIM_RE.findall()`, no negation check at all -- the sibling
    bug to `pr_claims.py`'s own (fixed the same task). A sentence that
    explicitly DENIES hitting a milestone still returned its number, the
    same false-positive shape task 610 fixed for `thanks.py` and task 612
    fixed for `duplicate_markers.py`. Reproduced live pre-fix: each case
    below returned the target number instead of an empty list."""

    def test_does_not_complete(self) -> None:
        assert claimed_milestone_numbers("This release does not complete milestone #12 yet.") == []

    def test_havent_hit(self) -> None:
        assert claimed_milestone_numbers("We haven't hit milestone #7 this sprint.") == []

    def test_never_milestone(self) -> None:
        assert claimed_milestone_numbers("Never milestone #99, cut for scope reasons.") == []

    def test_no_milestone(self) -> None:
        assert claimed_milestone_numbers("No milestone #3 claim here, unrelated prose.") == []

    def test_unnegated_claim_still_matches(self) -> None:
        # The negation check must not swallow a real, unnegated claim.
        assert claimed_milestone_numbers("this ships milestone #12") == [12]

    def test_falls_through_to_a_later_genuine_claim(self) -> None:
        # A denied claim earlier in the text must not stop the scan -- the
        # next, genuinely unnegated claim still returns, mirroring
        # `duplicate_markers.py`'s own fall-through test.
        assert claimed_milestone_numbers("not milestone #7, but genuinely milestone #12") == [12]

    def test_distant_negation_is_out_of_scope(self) -> None:
        # Documented residual limit (see module docstring): the negation
        # check only looks at the words immediately in front of the
        # literal word "milestone", not the whole text, so a denial
        # separated from its own claim by more than a few words can still
        # slip through.
        assert claimed_milestone_numbers(
            "we do not expect to complete milestone #7 this cycle"
        ) == [7]


class TestNegationDoesNotCrossASentenceBoundary:
    """Task 693 (Retrya): the shared `seam_engine.negation.is_negated`
    window used to search straight through a sentence boundary -- a
    negation word in a PRIOR, unrelated sentence silently swallowed a
    genuine milestone claim in the sentence that followed it. Reproduced
    live pre-fix: `claimed_milestone_numbers("Not today. milestone #7 is
    done.")` returned `[]`. See `seam_engine.negation`'s own docstring for
    the fix and the full blast radius."""

    def test_negation_in_a_prior_sentence_does_not_suppress_a_real_claim(
        self,
    ) -> None:
        assert claimed_milestone_numbers("Not today. milestone #7 is done.") == [7]


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
