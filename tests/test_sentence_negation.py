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


if __name__ == "__main__":
    unittest.main()
