"""Tests for `seam_engine.pr_claims` -- the shared "ships/includes/merges/
via #N" PR-claim-phrase law.

`release-claims-unmerged-pr/detector.py` (task 378) and `merged-pr-never-
released/detector.py` (task 381) each carried their own, textually-
identical `_CLAIM_RE` regex -- the second file's own comment claimed it was
"identical... on purpose", but nothing imported one from the other. This is
the same "reused verbatim... not a second copy of it drifting apart" gap
task 389 found and fixed for `#N` extraction (`seam_engine.references`) and
task 390 found and fixed a second time for the "milestone #N" claim phrase
(`seam_engine.milestone_claims`), found here a third time (task 393) and
fixed the same way. This module is now the one real source; these tests
check its own behavior directly, and `TestBothDetectorsShareTheLaw` below
is the regression test that would go red the moment either recipe's
detector goes back to defining its own local copy instead of importing
this one.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from seam_engine.pr_claims import PR_CLAIM_RE, claimed_pr_numbers

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]


def _load_detector(recipe_slug: str, test_module_name: str):
    """Load a recipe's `detector.py` the same way `seam_engine.recipes.
    load_detector` loads any recipe at runtime -- same discipline as
    `test_references.py`'s and `test_milestone_claims.py`'s own
    `_load_detector`."""
    path = FENCEPOST_ROOT / "RECIPES" / recipe_slug / "detector.py"
    spec = importlib.util.spec_from_file_location(test_module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[test_module_name] = module
    spec.loader.exec_module(module)
    return module


class TestClaimedPrNumbers:
    def test_single_claim_ships(self) -> None:
        assert claimed_pr_numbers("this ships #901") == [901]

    def test_single_claim_includes(self) -> None:
        assert claimed_pr_numbers("includes #902 this time") == [902]

    def test_single_claim_merges(self) -> None:
        assert claimed_pr_numbers("merges #903") == [903]

    def test_single_claim_via(self) -> None:
        assert claimed_pr_numbers("shipped via #904") == [904]

    def test_case_insensitive(self) -> None:
        assert claimed_pr_numbers("SHIPS #905") == [905]

    def test_multiple_claims_in_order(self) -> None:
        assert claimed_pr_numbers("ships #901. includes #902.") == [901, 902]

    def test_no_claim(self) -> None:
        assert claimed_pr_numbers("routine cleanup, nothing here") == []

    def test_bare_hash_with_no_claim_verb_is_not_a_claim(self) -> None:
        assert claimed_pr_numbers("see #906 for background") == []

    def test_duplicate_claim_of_same_number(self) -> None:
        assert claimed_pr_numbers("ships #901 and via #901 again") == [901, 901]


class TestNegatedClaimIsNotAClaim:
    """Task 613: `claimed_pr_numbers` used to be a bare `PR_CLAIM_RE.
    findall()`, no negation check at all -- a body that explicitly DENIES
    shipping/merging/including a PR ("does not ship #N") still returned N,
    the exact false-positive shape task 610 fixed for `thanks.py`'s "no
    thanks @handle" and task 612 fixed for `duplicate_markers.py`'s "not a
    duplicate of #N". Reproduced live pre-fix: each case below returned
    the target number instead of an empty list."""

    def test_does_not_ship(self) -> None:
        assert claimed_pr_numbers("This release does not ship #45, deferred to next cycle.") == []

    def test_will_not_merge(self) -> None:
        assert claimed_pr_numbers("We will not merge #77 this sprint.") == []

    def test_doesnt_include(self) -> None:
        assert claimed_pr_numbers("Doesn't include #12 yet.") == []

    def test_never_ships(self) -> None:
        assert claimed_pr_numbers("Never ships #99, cut for scope reasons.") == []

    def test_wont_ship_contraction(self) -> None:
        assert claimed_pr_numbers("Won't ship #50 today.") == []

    def test_unnegated_claim_still_matches(self) -> None:
        # The negation check must not swallow a real, unnegated claim.
        assert claimed_pr_numbers("this ships #901") == [901]

    def test_falls_through_to_a_later_genuine_claim(self) -> None:
        # A denied claim earlier in the text must not stop the scan -- the
        # next, genuinely unnegated claim still returns, mirroring
        # `duplicate_markers.py`'s own "not a duplicate of #12, but
        # genuinely a duplicate of #45" fall-through test.
        assert claimed_pr_numbers("not merges #12 but genuinely merges #45") == [45]

    def test_distant_negation_is_out_of_scope(self) -> None:
        # Documented residual limit (see module docstring): the negation
        # check only looks at the words immediately in front of the claim
        # verb, not the whole text, so a denial separated from its own
        # claim by more than a few words can still slip through.
        assert claimed_pr_numbers(
            "There is no reason to hold this back any further, it ships #12"
        ) == [12]


class TestNegationDoesNotCrossASentenceBoundary:
    """Task 693 (Retrya): the shared `seam_engine.negation.is_negated`
    window used to search straight through a sentence boundary -- a
    negation word in a PRIOR, unrelated sentence silently swallowed a
    genuine PR claim in the sentence that followed it. Reproduced live
    pre-fix: `claimed_pr_numbers("Not today. ships #45 anyway.")` returned
    `[]`. See `seam_engine.negation`'s own docstring for the fix and the
    full blast radius."""

    def test_negation_in_a_prior_sentence_does_not_suppress_a_real_claim(
        self,
    ) -> None:
        assert claimed_pr_numbers("Not today. ships #45 anyway.") == [45]


class TestPrClaimRe:
    def test_pattern_source(self) -> None:
        assert PR_CLAIM_RE.pattern == r"\b(?:ships?|includes?|merges?|via)\s+#(\d+)\b"


class TestBothDetectorsShareTheLaw:
    """The regression test: all three "ships/includes/merges/via #N"-claim
    recipes must bind their own `_claimed_pr_numbers` name to THIS module's
    function object, not to a second, independently-defined one --
    identity, not textual coincidence."""

    def test_release_claims_unmerged_pr_binds_the_shared_function(self) -> None:
        detector = _load_detector(
            "release-claims-unmerged-pr",
            "seam_engine._recipe_release_claims_unmerged_pr_pr_claims_test",
        )
        assert detector._claimed_pr_numbers is claimed_pr_numbers

    def test_merged_pr_never_released_binds_the_shared_function(self) -> None:
        detector = _load_detector(
            "merged-pr-never-released",
            "seam_engine._recipe_merged_pr_never_released_pr_claims_test",
        )
        assert detector._claimed_pr_numbers is claimed_pr_numbers

    def test_tweet_claims_unmerged_pr_binds_the_shared_function(self) -> None:
        detector = _load_detector(
            "tweet-claims-unmerged-pr",
            "seam_engine._recipe_tweet_claims_unmerged_pr_pr_claims_test",
        )
        assert detector._claimed_pr_numbers is claimed_pr_numbers
