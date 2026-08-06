"""Task 548. Proves tools/sentence_negation.py's shared
iter_sentences()/is_negated_prefix() behave correctly on their own, and
that the two sibling checks they were extracted from (hand_lore_check,
rider_check) each now delegate to them rather than carrying their own
byte-identical `_sentences`/`_is_negated` copies.

Found by the same AST-hash duplicate-function sweep task 546/this task's
own quoted_citation.py used (constants normalized before hashing):
hand_lore_check.py's and rider_check.py's `_sentences`/`_is_negated` were
byte-identical bodies (only the docstrings differed, each claiming to
mirror the other). Unlike quoted_citation.is_quoted_citation, these two
genuinely need a parameter per call -- `_SENTENCE_BOUNDARY`/
`_NEGATION_CUES` are deliberately tuned per file (task 467's documented
on-purpose divergence) -- so each sibling keeps a thin one-line wrapper
closing over its own module-level regex, the same shape violation_format.
py's six siblings use (task 546), proven here by output match against a
frozen pre-refactor fixture plus an AST identity check that each wrapper
still calls straight through to the shared function.

Task 569: this module's own docstring named a second, sibling shape at
task 548 and explicitly deferred it as "a larger and riskier refactor
than one hour should reach for alongside this one" -- `no_grading_check.
py`/`star_covenant_check.py`/`arcade_hero_check.py`'s own
`_is_negated_or_predictive`, a fourth AST-identical body (scan the full
text backward for the nearest sentence boundary, then search only that
slice) confirmed still standing, live, by the same normalized-constants
AST-hash sweep this task ran before touching anything. Consolidated into
`sentence_negation.is_negated_or_predictive(text, match_start,
sentence_boundary, negation_cues)`, the same thin-wrapper-per-sibling
shape as `iter_sentences`/`is_negated_prefix` above -- each sibling keeps
its own, genuinely different (task 467) `_SENTENCE_BOUNDARY`/
`_NEGATION_CUES` globals, only the scan-and-slice control flow moved.
Pre-refactor byte-identical output confirmed live via `git stash` against
seven fixed text/needle pairs (including the exact "mortals will star the
repo" / arcade_hero_check's own `will`-less word list divergence each
sibling's own docstring already named) before a single line of the three
call sites changed.
"""
import ast
import importlib.util
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


sn = _load("sentence_negation", os.path.join(TOOLS, "sentence_negation.py"))

SIBLINGS = ["hand_lore_check", "rider_check"]

_BOUNDARY = re.compile(r"[.!?;]|\n{2,}")
_CUES = re.compile(r"\b(never|not|no)\b", re.IGNORECASE)


class SharedFunctionCase(unittest.TestCase):
    """The two shared functions, exercised directly."""

    def test_iter_sentences_splits_on_every_boundary_match(self):
        text = "First one. Second one! Third one?"
        spans = list(sn.iter_sentences(text, _BOUNDARY))
        rendered = [text[s:e] for s, e in spans]
        self.assertEqual(rendered, ["First one.", " Second one!", " Third one?"])

    def test_iter_sentences_yields_a_trailing_fragment_with_no_terminator(self):
        text = "Only one sentence, no terminator"
        spans = list(sn.iter_sentences(text, _BOUNDARY))
        self.assertEqual(spans, [(0, len(text))])
        self.assertEqual(text[spans[0][0]:spans[0][1]], text)

    def test_iter_sentences_on_empty_text_yields_nothing(self):
        self.assertEqual(list(sn.iter_sentences("", _BOUNDARY)), [])

    def test_is_negated_prefix_true_when_cue_precedes_match(self):
        sentence = "we never say the Hand is Thierry"
        match_start = sentence.index("the Hand is Thierry")
        self.assertTrue(sn.is_negated_prefix(sentence, match_start, _CUES))

    def test_is_negated_prefix_false_when_cue_only_follows_match(self):
        sentence = "the Hand is Thierry, never doubt it"
        match_start = sentence.index("the Hand is Thierry")
        self.assertFalse(sn.is_negated_prefix(sentence, match_start, _CUES))

    def test_is_negated_prefix_false_with_no_cue_at_all(self):
        sentence = "the Hand is Thierry"
        self.assertFalse(sn.is_negated_prefix(sentence, len(sentence), _CUES))

    def test_is_negated_or_predictive_true_when_cue_precedes_match_same_sentence(self):
        text = "we never say the Hand is Thierry. The Hand is Thierry, in fact."
        match_start = text.index("the Hand is Thierry")
        self.assertTrue(sn.is_negated_or_predictive(text, match_start, _BOUNDARY, _CUES))

    def test_is_negated_or_predictive_false_when_cue_is_only_in_a_prior_sentence(self):
        text = "we never lie about anything. The Hand is Thierry, in fact."
        match_start = text.index("The Hand is Thierry")
        self.assertFalse(sn.is_negated_or_predictive(text, match_start, _BOUNDARY, _CUES))

    def test_is_negated_or_predictive_false_when_cue_only_follows_match(self):
        text = "the Hand is Thierry, never doubt it"
        match_start = text.index("the Hand is Thierry")
        self.assertFalse(sn.is_negated_or_predictive(text, match_start, _BOUNDARY, _CUES))

    def test_is_negated_or_predictive_scans_the_full_text_not_a_pre_cut_sentence(self):
        # Unlike is_negated_prefix (which needs an already-cut sentence and
        # a match_start relative to IT), is_negated_or_predictive takes the
        # full text and a match_start relative to the WHOLE text -- proven
        # here by a match_start that is not at the very start of its
        # sentence's own local offset.
        text = "First sentence here. we never say the Hand is Thierry"
        match_start = text.index("the Hand is Thierry")
        self.assertTrue(sn.is_negated_or_predictive(text, match_start, _BOUNDARY, _CUES))


class SiblingOutputMatchesPreRefactorFixtureCase(unittest.TestCase):
    """Each sibling's own `_sentences`/`_is_negated` output is unchanged
    from before the refactor, exercised through the module's own real
    `_SENTENCE_BOUNDARY`/`_NEGATION_CUES` globals."""

    def test_hand_lore_check_sentences_and_negation(self):
        mod = _load("hand_lore_check", os.path.join(TOOLS, "hand_lore_check.py"))
        text = "We never say the Hand is Thierry. The Hand is Thierry, in fact."
        spans = list(mod._sentences(text))
        self.assertEqual(len(spans), 2)
        first_sentence = text[spans[0][0]:spans[0][1]]
        second_sentence = text[spans[1][0]:spans[1][1]]
        self.assertTrue(mod._is_negated(first_sentence, first_sentence.index("the Hand is Thierry")))
        self.assertFalse(mod._is_negated(second_sentence, second_sentence.index("The Hand is Thierry")))

    def test_rider_check_sentences_and_negation(self):
        mod = _load("rider_check", os.path.join(TOOLS, "rider_check.py"))
        text = "Ogun is never violent. Ogun is violent, some say."
        spans = list(mod._sentences(text))
        self.assertEqual(len(spans), 2)
        first_sentence = text[spans[0][0]:spans[0][1]]
        second_sentence = text[spans[1][0]:spans[1][1]]
        self.assertTrue(mod._is_negated(first_sentence, first_sentence.index("violent")))
        self.assertFalse(mod._is_negated(second_sentence, second_sentence.index("violent")))


# Task 569: the second sibling family, each carrying its own
# `_is_negated_or_predictive` rather than `_sentences`/`_is_negated` --
# a different calling shape (scan the full text, never a pre-cut
# sentence), so it gets its own fixture pairs and its own delegation
# check below rather than being folded into SIBLINGS/PREDICTIVE_CASES.
PREDICTIVE_SIBLINGS = ["star_covenant_check", "no_grading_check", "arcade_hero_check"]

# Seven fixed (text, needle) pairs, run live via `git stash` against the
# untouched pre-refactor bodies of all three siblings before this task
# changed a single call site -- output was byte-identical, this fixture
# is that frozen proof. Deliberately includes the one pair
# (`"mortals will star the repo"`) each sibling's own docstring already
# names as diverging: `arcade_hero_check.py`'s `_NEGATION_CUES` lacks
# "will" (task 467), so it alone reads False here where the other two
# read True -- proof this refactor preserved the divergence rather than
# accidentally unifying it.
PREDICTIVE_FIXTURE = [
    ("mortals will star the repo, someday", "star the repo",
     {"star_covenant_check": True, "no_grading_check": True, "arcade_hero_check": False}),
    ('never say "please star"', "please star",
     {"star_covenant_check": True, "no_grading_check": True, "arcade_hero_check": True}),
    ("please star the repo now", "please star",
     {"star_covenant_check": False, "no_grading_check": False, "arcade_hero_check": False}),
    ("we will never ask you to paste your API key", "paste your API key",
     {"star_covenant_check": True, "no_grading_check": True, "arcade_hero_check": True}),
    ("please paste your API key here", "paste your API key",
     {"star_covenant_check": False, "no_grading_check": False, "arcade_hero_check": False}),
    ("it never says anyone dropped the ball, ever", "dropped the ball",
     {"star_covenant_check": True, "no_grading_check": True, "arcade_hero_check": True}),
    ("they said we dropped the ball", "dropped the ball",
     {"star_covenant_check": False, "no_grading_check": False, "arcade_hero_check": False}),
]


class PredictiveSiblingOutputMatchesPreRefactorFixtureCase(unittest.TestCase):
    """Each of the three `_is_negated_or_predictive` siblings' output is
    unchanged from before the refactor, exercised through the module's
    own real `_SENTENCE_BOUNDARY`/`_NEGATION_CUES` globals -- the fixture
    above is the frozen `git stash`-verified pre-refactor record."""

    def test_every_sibling_matches_its_frozen_fixture(self):
        for name in PREDICTIVE_SIBLINGS:
            mod = _load(name, os.path.join(TOOLS, f"{name}.py"))
            for text, needle, expected in PREDICTIVE_FIXTURE:
                match_start = text.index(needle)
                with self.subTest(sibling=name, text=text):
                    self.assertEqual(
                        mod._is_negated_or_predictive(text, match_start),
                        expected[name],
                        f"{name}._is_negated_or_predictive drifted from its "
                        f"frozen pre-refactor fixture on {text!r}",
                    )


class SiblingDelegatesIdentityCase(unittest.TestCase):
    """Each sibling's own `_sentences`/`_is_negated` source calls straight
    through to tools/sentence_negation.py's shared functions exactly once
    -- proof of delegation, not just output that happens to match today."""

    def _assert_delegates(self, path, wrapper_name, shared_attr):
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        calls = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == wrapper_name:
                for sub in ast.walk(node):
                    if (
                        isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == shared_attr
                        and isinstance(sub.func.value, ast.Name)
                        and sub.func.value.id == "sentence_negation"
                    ):
                        calls += 1
        self.assertEqual(
            calls, 1,
            f"{os.path.basename(path)}.{wrapper_name} does not delegate to "
            f"sentence_negation.{shared_attr} exactly once -- it may have "
            "been re-forked into its own copy",
        )

    def test_every_sibling_delegates_both_functions(self):
        for name in SIBLINGS:
            path = os.path.join(TOOLS, f"{name}.py")
            with self.subTest(sibling=name, function="_sentences"):
                self._assert_delegates(path, "_sentences", "iter_sentences")
            with self.subTest(sibling=name, function="_is_negated"):
                self._assert_delegates(path, "_is_negated", "is_negated_prefix")

    def test_every_predictive_sibling_delegates_is_negated_or_predictive(self):
        for name in PREDICTIVE_SIBLINGS:
            path = os.path.join(TOOLS, f"{name}.py")
            with self.subTest(sibling=name):
                self._assert_delegates(
                    path, "_is_negated_or_predictive", "is_negated_or_predictive"
                )


if __name__ == "__main__":
    unittest.main()
