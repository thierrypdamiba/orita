"""Tests for `seam_engine.mention_number` -- the shared "bare `#N`
mentioned in text" digit-boundary law.

`issue-closed-not-tweeted/detector.py` and `merged-pr-not-tweeted/
detector.py` each carried their own, textually-identical
`_find_announcing_tweet` -- each file's own comment even named the other
as the sibling that "already guards against" the identical short-inside-
long collision, but nothing imported one from the other, and
`tools/duplicate_regex_check.py`'s own literal-only AST scan cannot see a
pattern built by string concatenation, so it read the pre-fix tree as
clean. See `seam_engine.mention_number`'s own docstring for the full
account. This module is now the one real source; these tests check its
own behavior directly, and `TestBothDetectorsShareTheLaw` below is the
regression test that would go red the moment either recipe's detector
goes back to defining its own local copy instead of importing this one.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from seam_engine.mention_number import number_mentioned

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]

_SLUGS = ["issue-closed-not-tweeted", "merged-pr-not-tweeted"]


def _load_detector(recipe_slug: str, test_module_name: str):
    """Load a recipe's `detector.py` the same way `seam_engine.recipes.
    load_detector` loads any recipe at runtime -- same discipline as
    `test_thanks.py`'s own `_load_detector`."""
    path = FENCEPOST_ROOT / "RECIPES" / recipe_slug / "detector.py"
    spec = importlib.util.spec_from_file_location(test_module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[test_module_name] = module
    spec.loader.exec_module(module)
    return module


def _detector_source(recipe_slug: str) -> str:
    return (FENCEPOST_ROOT / "RECIPES" / recipe_slug / "detector.py").read_text()


class TestNumberMentioned:
    def test_exact_bare_match(self) -> None:
        assert number_mentioned("#13 shipped a hotfix.", 13) is True

    def test_not_satisfied_by_a_longer_number_containing_it(self) -> None:
        assert number_mentioned("#123 shipped a batch of fixes today.", 12) is False

    def test_not_satisfied_by_a_shorter_number_it_extends(self) -> None:
        assert number_mentioned("#12 shipped a hotfix.", 1) is False

    def test_not_satisfied_by_a_bare_numeral_with_no_hash(self) -> None:
        assert number_mentioned("Batch 112 processed clean.", 12) is False

    def test_multi_digit_boundary_both_sides(self) -> None:
        assert number_mentioned("#13010 shipped a batch of fixes today.", 1301) is False
        assert number_mentioned("#1301 shipped a hotfix.", 1301) is True

    def test_no_mention_at_all(self) -> None:
        assert number_mentioned("nothing shipped today", 42) is False


class TestBothDetectorsShareTheLaw:
    """The regression test: both detectors must actually IMPORT
    `number_mentioned` from `seam_engine.mention_number` and must NOT also
    define their own local `re.compile` for the digit-boundary pattern.
    Checked two ways, same discipline as `test_thanks.py`'s own
    `TestBothDetectorsShareTheLaw`: (1) the loaded module's own
    `_find_announcing_tweet` still behaves exactly like the shared
    function (functional parity); (2) the detector's SOURCE TEXT names the
    real import and contains no local digit-boundary `re.compile(` call of
    its own -- the actual regression signal, since `re.compile` memoizes
    identical patterns to the same cached object, so an `is`/pattern-
    string check alone could pass even after a detector reverted to its
    own byte-identical local copy."""

    def test_functional_parity(self) -> None:
        for slug in _SLUGS:
            detector = _load_detector(slug, f"seam_engine._recipe_{slug.replace('-', '_')}_mention_test")

            class _FakeTweet:
                def __init__(self, text: str) -> None:
                    self.text = text
                    self.id = "t1"
                    self.url = "https://x.com/oritatown/status/1"
                    from datetime import datetime, timezone

                    self.created_at = datetime.now(timezone.utc)

            assert detector._find_announcing_tweet(12, [_FakeTweet("#123 shipped today")]) is None
            hit = _FakeTweet("#12 shipped today")
            assert detector._find_announcing_tweet(12, [hit]) is hit

    def test_source_imports_the_shared_function_not_a_local_pattern(self) -> None:
        for slug in _SLUGS:
            source = _detector_source(slug)
            assert "from seam_engine.mention_number import number_mentioned" in source, (
                f"{slug}/detector.py no longer imports seam_engine.mention_number"
            )
            assert 're.compile(r"(?<!\\d)#"' not in source, (
                f"{slug}/detector.py defines its own local digit-boundary pattern"
            )
            assert "\nimport re\n" not in source, (
                f"{slug}/detector.py still imports re directly -- the shared "
                "module owns the pattern now"
            )
