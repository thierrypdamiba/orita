"""Tests for `seam_engine.negation` -- the shared negation-prefix law
extracted (task 613) from `duplicate_markers.py`'s own pattern once
`pr_claims.py` and `milestone_claims.py` both needed the identical
`re.compile(...)` this same task and `tools/duplicate_regex_check.py`
caught the resulting hand-typed triplicate live. These tests check the
module's own behavior directly; `test_duplicate_markers.py`,
`test_pr_claims.py`, and `test_milestone_claims.py` each already exercise
it indirectly through their own callers.
"""
from __future__ import annotations

from seam_engine.negation import NEGATION_PREFIX_RE, is_negated


class TestIsNegated:
    def test_not_within_window(self) -> None:
        text = "does not ship #45"
        start = text.index("ship")
        assert is_negated(text, start, window=20) is True

    def test_never_within_window(self) -> None:
        text = "never ships #45"
        start = text.index("ships")
        assert is_negated(text, start, window=20) is True

    def test_no_within_window(self) -> None:
        text = "No milestone #3"
        start = text.index("milestone")
        assert is_negated(text, start, window=20) is True

    def test_contraction_within_window(self) -> None:
        text = "doesn't ship #45"
        start = text.index("ship")
        assert is_negated(text, start, window=20) is True

    def test_unnegated_returns_false(self) -> None:
        text = "this ships #901"
        start = text.index("ships")
        assert is_negated(text, start, window=20) is False

    def test_negation_outside_window_is_not_seen(self) -> None:
        # A narrow window is deliberate -- see every caller's own
        # docstring for why. A negation word far enough back falls
        # outside the window and is correctly not seen.
        text = "not " + ("x" * 30) + " ships #45"
        start = text.index("ships")
        assert is_negated(text, start, window=10) is False

    def test_window_clamped_at_string_start(self) -> None:
        # A match near the very start of the text must not crash on a
        # negative slice start.
        text = "ships #1"
        assert is_negated(text, 0, window=20) is False


class TestSentenceBoundaryStopsTheWindow:
    """Task 693: a negation word belonging to an earlier, unrelated
    sentence must not be able to negate a claim in the sentence that
    follows it just because both happen to fall inside a fixed character
    window -- see this module's own docstring for the live pre-fix
    reproduction across all four real callers."""

    def test_negation_in_a_prior_sentence_is_not_seen(self) -> None:
        text = "It is not okay. thanks @user for the fix."
        start = text.index("thanks")
        # "not" sits well inside a 10-char window, but a period ends its
        # own sentence first -- the claim after it is genuinely unnegated.
        assert is_negated(text, start, window=10) is False

    def test_negation_in_the_same_sentence_after_the_boundary_still_seen(
        self,
    ) -> None:
        text = "It is fine. not fine, ships #45 anyway."
        start = text.index("ships")
        # The nearer "not" (after the period) is in the SAME sentence as
        # the claim and must still count.
        assert is_negated(text, start, window=30) is True

    def test_exclamation_and_question_mark_are_also_boundaries(self) -> None:
        for punct in ("!", "?"):
            text = f"Not this{punct} dup of #12 today."
            start = text.index("dup")
            assert is_negated(text, start, window=20) is False, punct

    def test_comma_is_not_a_boundary(self) -> None:
        # Every real caller relies on "no, thanks @user" / "no, not a
        # duplicate of #12" staying inside the same window -- a comma must
        # not end it.
        text = "no, thanks @user"
        start = text.index("thanks")
        assert is_negated(text, start, window=20) is True

    def test_boundary_uses_the_last_punctuation_not_the_first(self) -> None:
        # Two sentence boundaries inside the window -- only the text after
        # the LAST one is searched.
        text = "Not this. Also not this. ships #45 for real."
        start = text.index("ships")
        assert is_negated(text, start, window=len(text)) is False


class TestNegationPrefixRe:
    def test_pattern_source(self) -> None:
        assert NEGATION_PREFIX_RE.pattern == r"\b(?:not|never|no)\b|n't\b"
