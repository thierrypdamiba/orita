"""Tests for `seam_engine.thanks` -- the shared "thanks/thank you @handle"
tweet-grammar law.

`contributor-thanked-not-credited/detector.py` (task 371) and `readme-
credited-not-thanked/detector.py` (task 385) each carried their own,
textually-identical `_THANKS_RE` regex -- the second file's own comment
claimed it was "identical grammar... reused verbatim", but nothing
imported one from the other. This is the same "reused verbatim... not a
second copy of it drifting apart" gap task 389 found and fixed for `#N`
extraction (`seam_engine.references`), task 390 found and fixed a second
time for the "milestone #N" claim phrase (`seam_engine.milestone_claims`),
task 393 found and fixed a third time for the "ships/includes/merges/via
#N" claim phrase (`seam_engine.pr_claims`), and task 394 found and fixed a
fourth time for the GitHub closing-keyword grammar
(`seam_engine.closing_keywords`), found here a fifth time (task 396) and
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

from seam_engine.thanks import THANKS_RE, thanked_handle

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]

# NOTE on why the regression class below reads source text rather than
# comparing `detector._THANKS_RE is THANKS_RE`: Python's `re.compile`
# memoizes -- two independently written `re.compile(same pattern, same
# flags)` calls anywhere in the process return the SAME cached Pattern
# object (task 394 confirmed this live for the closing-keyword regex; the
# same holds here). An `is` check on the regex object would therefore pass
# even if a detector went back to defining its own local copy with
# byte-identical source -- exactly the false-negative task 394's own
# closing note exists to prevent. The real regression signal has to come
# from the source text: does the file import the shared name, and does it
# NOT also define its own `re.compile` for it.


def _load_detector(recipe_slug: str, test_module_name: str):
    """Load a recipe's `detector.py` the same way `seam_engine.recipes.
    load_detector` loads any recipe at runtime -- same discipline as
    `test_pr_claims.py`'s and `test_closing_keywords.py`'s own
    `_load_detector`."""
    path = FENCEPOST_ROOT / "RECIPES" / recipe_slug / "detector.py"
    spec = importlib.util.spec_from_file_location(test_module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[test_module_name] = module
    spec.loader.exec_module(module)
    return module


def _detector_source(recipe_slug: str) -> str:
    return (FENCEPOST_ROOT / "RECIPES" / recipe_slug / "detector.py").read_text()


class TestThankedHandle:
    def test_thanks_no_you(self) -> None:
        assert thanked_handle("thanks @mortal-fixer for the patch") == "mortal-fixer"

    def test_thank_you(self) -> None:
        assert thanked_handle("thank you @river-keeper, seriously") == "river-keeper"

    def test_case_insensitive(self) -> None:
        assert thanked_handle("THANKS @Loud-One") == "Loud-One"

    def test_far_gap_within_forty_chars(self) -> None:
        text = "thanks so much for the patch, seriously @patient-one"
        assert thanked_handle(text) == "patient-one"

    def test_no_thanks_language_is_not_a_match(self) -> None:
        assert thanked_handle("shoutout to @mortal-fixer") is None

    def test_bare_mention_is_not_a_match(self) -> None:
        assert thanked_handle("@mortal-fixer opened a great issue") is None

    def test_no_handle_at_all(self) -> None:
        assert thanked_handle("thanks everyone, this was a team effort") is None

    def test_first_match_only(self) -> None:
        text = "thanks @first-one and also thanks @second-one"
        assert thanked_handle(text) == "first-one"


class TestNegatedThanksIsNotAMatch:
    """Task 610 (Kwaku Ananse): a thanks-shaped phrase immediately preceded
    by a negation word is a decline, not credit -- reproduced live pre-fix
    (`thanked_handle("no thanks @user, wrong fix")` returned `"user"`),
    the exact false-positive shape STRATEGY.md's Ogun's law exists to
    catch. See `seam_engine.thanks`'s own docstring for the full
    reproduction and the deliberately narrow scope of the fix."""

    def test_no_thanks_is_not_a_match(self) -> None:
        assert thanked_handle("no thanks @user, wrong fix") is None

    def test_not_thanks_is_not_a_match(self) -> None:
        assert thanked_handle("not thanks @user") is None

    def test_no_comma_thanks_is_not_a_match(self) -> None:
        assert thanked_handle("no, thanks @user") is None

    def test_never_thanks_is_not_a_match(self) -> None:
        assert thanked_handle("never thanks @user, does it") is None

    def test_a_negated_first_candidate_falls_through_to_a_real_later_one(self) -> None:
        text = "no thanks @nobody, real credit goes to thanks @real-one"
        assert thanked_handle(text) == "real-one"

    def test_a_no_that_is_part_of_a_compound_word_is_not_a_negation(self) -> None:
        # A real, ordinary phrase -- the "no" inside "no-brainer" is its own
        # hyphen-bounded word but sits well before "thanks", not in the
        # narrow prefix window this check actually looks at.
        assert thanked_handle("thanks for the no-brainer fix, @user") == "user"

    def test_genuine_thanks_still_matches_unaffected(self) -> None:
        assert thanked_handle("thanks @mortal-fixer for the patch") == "mortal-fixer"

    def test_doesnt_thank_is_not_a_match(self) -> None:
        # Live reproduction: `_NEGATION_PREFIX_RE` here only ever matched
        # the whole words "no"/"not"/"never" -- an "n't" contraction right
        # in front of "thank(s)" ("doesn't thank @user") slipped past it
        # entirely, the exact same false-positive shape task 610 already
        # fixed for the bare-word case, just one contraction short of
        # complete. `seam_engine.negation.NEGATION_PREFIX_RE` (task 613,
        # consolidated for `pr_claims.py`/`milestone_claims.py`/
        # `duplicate_markers.py`) already covers `n't\b` -- this module was
        # never moved onto it.
        assert thanked_handle("doesn't thank @user for the fix") is None

    def test_didnt_thank_is_not_a_match(self) -> None:
        assert thanked_handle("didn't thank @user for the fix") is None

    def test_shouldnt_thank_is_not_a_match(self) -> None:
        assert thanked_handle("shouldn't thank @user for this") is None


class TestNegationDoesNotCrossASentenceBoundary:
    """Task 693 (Retrya): the shared `seam_engine.negation.is_negated`
    window used to search straight through a sentence boundary -- a
    negation word in a PRIOR, unrelated sentence silently swallowed a
    genuine thanks in the sentence that followed it. Reproduced live
    pre-fix: `thanked_handle("It is not okay. thanks @user for the fix.")`
    returned `None`. See `seam_engine.negation`'s own docstring for the
    fix and the full blast radius."""

    def test_negation_in_a_prior_sentence_does_not_suppress_a_real_thanks(
        self,
    ) -> None:
        assert (
            thanked_handle("It is not okay. thanks @user for the fix.")
            == "user"
        )


class TestThanksRe:
    def test_pattern_source(self) -> None:
        assert THANKS_RE.pattern == r"thanks?(?:\s+you)?\b.{0,40}?@(\w[\w-]*)"


class TestBothDetectorsShareTheLaw:
    """The regression test: both thanks-shaped recipes must actually
    IMPORT `THANKS_RE` from `seam_engine.thanks` and must NOT also define
    their own local `re.compile` for it. Checked two ways for each
    detector: (1) the loaded module's own `_THANKS_RE` attribute still
    behaves exactly like the shared regex (functional parity -- cheap to
    keep even though it can't prove import-vs-coincidence on its own,
    since `re.compile` memoizes identical patterns to the same cached
    object); (2) the detector's SOURCE TEXT names the real import and
    contains no local `re.compile(` call of its own -- the actual
    regression signal, since a reverted detector would still pass (1) via
    `re`'s cache but would fail (2) immediately."""

    _SLUGS = ["contributor-thanked-not-credited", "readme-credited-not-thanked"]

    def test_functional_parity(self) -> None:
        for slug in self._SLUGS:
            detector = _load_detector(slug, f"seam_engine._recipe_{slug.replace('-', '_')}_thanks_test")
            local_re = detector._THANKS_RE
            assert local_re.pattern == THANKS_RE.pattern
            assert local_re.search("thanks @someone").group(1) == "someone"

    def test_source_imports_the_shared_module_not_a_local_copy(self) -> None:
        for slug in self._SLUGS:
            source = _detector_source(slug)
            assert "from seam_engine.thanks import" in source, (
                f"{slug}/detector.py no longer imports seam_engine.thanks"
            )
            assert "_THANKS_RE = re.compile(" not in source, (
                f"{slug}/detector.py defines its own local _THANKS_RE"
            )


class TestBothDetectorsCallTheSharedFunctionNotJustTheSharedRegex:
    """Task 610 (Kwaku Ananse): importing `THANKS_RE` was never the whole
    law -- both detectors imported the shared regex but then ran their own
    `_THANKS_RE.search(text)` right here, a second, independent
    reimplementation of `thanked_handle`'s own extract-and-return logic
    that `TestBothDetectorsShareTheLaw` above never caught, because it only
    ever checked the regex was shared, not the function built on it.
    Reproduced live pre-fix: `thanked_handle` (this module) correctly
    rejected `"no thanks @user"`, but `contributor-thanked-not-credited`'s
    own `_thanked_handle("no thanks @user")` still returned `"user"`,
    because it called `_THANKS_RE.search` directly instead of the shared
    function. These tests exercise each detector's OWN public function
    with the real negation cases -- the regression signal a source-text
    grep alone cannot give, since a reimplementation can name-match the
    shared function's behavior today and silently drift the next time
    either side changes without a shared call wiring them together."""

    def test_contributor_thanked_not_credited_delegates_the_negation_fix(self) -> None:
        detector = _load_detector(
            "contributor-thanked-not-credited",
            "seam_engine._recipe_contributor_thanked_not_credited_negation_test",
        )
        assert detector._thanked_handle("no thanks @user, wrong fix") is None
        assert detector._thanked_handle("thanks @mortal-fixer for the patch") == "mortal-fixer"

    def test_readme_credited_not_thanked_delegates_the_negation_fix(self) -> None:
        detector = _load_detector(
            "readme-credited-not-thanked",
            "seam_engine._recipe_readme_credited_not_thanked_negation_test",
        )

        class _FakeTweet:
            def __init__(self, text: str) -> None:
                self.text = text

        tweets = [_FakeTweet("no thanks @user, wrong fix"), _FakeTweet("thanks @mortal-fixer for the patch")]
        assert detector._thanked_handles(tweets) == {"mortal-fixer"}

    def test_source_imports_the_shared_function_not_just_the_shared_regex(self) -> None:
        for slug in [
            "contributor-thanked-not-credited",
            "readme-credited-not-thanked",
        ]:
            source = _detector_source(slug)
            assert "thanked_handle" in source.split("\n", 1)[-1], (
                f"{slug}/detector.py no longer names thanked_handle at all"
            )
            assert "from seam_engine.thanks import" in source and "thanked_handle" in source.split(
                "from seam_engine.thanks import", 1
            )[1].split("\n", 1)[0], f"{slug}/detector.py imports seam_engine.thanks but not thanked_handle itself"
