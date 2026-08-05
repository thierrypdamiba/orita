"""Task 548. Proves tools/quoted_citation.py's shared is_quoted_citation()
behaves correctly on its own, and that the five sibling checks it was
extracted from (no_grading_check, star_covenant_check, arcade_hero_check,
hand_lore_check, rider_check) each now name that exact shared function
object -- not a separate copy that happens to behave the same today.

Found by the same AST-hash duplicate-function sweep task 546 used
(constants normalized before hashing): all five siblings defined the
identical `_is_quoted_citation(text, match_start)` body and the identical
`_QUOTE_CHARS = set('"\\'\u201c\u2018')` constant, confirmed byte-for-byte by
direct diff before this file was written, not assumed from the hash alone.
Unlike violation_format.py's six siblings (task 546, each parameterized by
its own label/detail text), this shared function needed no per-file
parameter at all -- the quote-character set never varied -- so each
sibling now names the shared function object directly (`_is_quoted_citation
= quoted_citation.is_quoted_citation`), the same bare-alias shape
star_covenant_check.py's own `_iter_public_files = scan_files.
iter_public_files` already uses, mirroring tests/test_scan_files.py's own
"identity, not equality" discipline: two functions that behave the same on
every input today can silently re-fork into separate copies tomorrow with
zero test failure unless the test asserts they are the SAME object.
"""
import importlib.util
import os
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


qc = _load("quoted_citation", os.path.join(TOOLS, "quoted_citation.py"))

SIBLINGS = [
    "no_grading_check",
    "star_covenant_check",
    "arcade_hero_check",
    "hand_lore_check",
    "rider_check",
]


class SharedFunctionCase(unittest.TestCase):
    """The shared function itself, exercised directly."""

    def test_true_when_immediately_preceded_by_a_quote_char(self):
        text = 'the phrase "please star" is quoted'
        # match_start points at "p" in please, index 12; char before is '"'
        self.assertTrue(qc.is_quoted_citation(text, text.index("please")))

    def test_false_when_not_preceded_by_a_quote_char(self):
        text = "please star this repo"
        self.assertFalse(qc.is_quoted_citation(text, 0))

    def test_false_at_start_of_string(self):
        self.assertFalse(qc.is_quoted_citation("please star", 0))

    def test_recognizes_every_default_quote_char(self):
        for ch in ('"', "'", "\u201c", "\u2018"):
            text = f"{ch}please star"
            with self.subTest(quote_char=ch):
                self.assertTrue(qc.is_quoted_citation(text, 1))

    def test_custom_quote_chars_override_the_default(self):
        text = "<please star"
        self.assertFalse(qc.is_quoted_citation(text, 1))
        self.assertTrue(qc.is_quoted_citation(text, 1, quote_chars={"<"}))


class SiblingIdentityCase(unittest.TestCase):
    """Each sibling's own `_is_quoted_citation` name IS the shared function
    object, not a separate copy that behaves the same today."""

    def test_every_sibling_names_the_shared_function(self):
        for name in SIBLINGS:
            with self.subTest(sibling=name):
                mod = _load(name, os.path.join(TOOLS, f"{name}.py"))
                self.assertIs(
                    mod._is_quoted_citation,
                    qc.is_quoted_citation,
                    f"{name}._is_quoted_citation is a separate copy again, "
                    "not the shared tools/quoted_citation.py function",
                )

    def test_no_sibling_carries_its_own_quote_chars_constant(self):
        """The consolidation removed each sibling's own `_QUOTE_CHARS`
        module global -- if one silently returned, the sibling has
        re-forked back into its own copy even if `_is_quoted_citation`
        still happens to alias the shared function."""
        for name in SIBLINGS:
            with self.subTest(sibling=name):
                mod = _load(name, os.path.join(TOOLS, f"{name}.py"))
                self.assertFalse(
                    hasattr(mod, "_QUOTE_CHARS"),
                    f"{name} still defines its own _QUOTE_CHARS",
                )


if __name__ == "__main__":
    unittest.main()
