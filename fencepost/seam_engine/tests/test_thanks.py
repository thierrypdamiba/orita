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
