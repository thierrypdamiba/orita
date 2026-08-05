"""Task 552. Proves `tools/text_patterns.py`'s shared `bounded_section()`
behaves correctly on its own (see `BoundedSectionCase` in `tests/test_
text_patterns.py`), and that the three siblings it was extracted from
(`scopes_completeness_check.py`'s `_section`, `recipe_readme_check.py`'s
`_community_recipes_section`, `chronicle_readme_check.py`'s `_episodes_
section`) each now delegate to it rather than each carrying its own
byte-identical (once the header pattern is treated as a parameter) copy.

Found by an AST-hash sweep of every `tools/*.py` function body (constants
normalized before hashing, the technique tasks 538/546/548/551 each used):
all three defined the identical four-line "search header, slice to the
next `## ` header or end of string" body, and two of the three docstrings
already explicitly claimed to mirror one another's "bounded-section read"
-- neither had actually imported a shared function until now, the exact
"claimed shared shape, never actually factored out" gap tasks 546/548/551
each closed for other duplicate families.

Two kinds of proof, mirroring `tests/test_violation_format.py`'s own
discipline: (1) each sibling's real, unmodified section-reader function's
output is byte-identical, on both the header-found and header-missing
path, to what it produced before this refactor (frozen fixture strings,
not a re-derivation); (2) each sibling's own source calls `text_patterns.
bounded_section` exactly once, so a future edit that quietly reforks one
sibling back into its own copy is caught by inspection, not just by
today's passing output comparison.
"""
import ast
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


# (module_name, function_name, sample_text_with_section, sample_text_without_section)
# The with-section fixture carries a decoy section before and after the
# real one, proving the reader stops at the SECOND `## ` header rather than
# reading to end of file -- the same regression test_scopes_completeness_
# check.py's own SectionParsingCase already covers for its one sibling,
# repeated here across all three since this is the shared function's job now.
SIBLINGS = [
    (
        "scopes_completeness_check",
        "_section",
        "# SCOPES\n\n## Some Other Section\ndecoy body\n\n"
        "## Every connected app, accounted for\n\n"
        "| `arcade-github` | in use by fencepost |\n\n"
        "## Yet Another Section\ntail decoy\n",
        "\n| `arcade-github` | in use by fencepost |\n\n",
        "# SCOPES\n\n## Some Other Section\nonly this section exists\n",
        "",
    ),
    (
        "recipe_readme_check",
        "_community_recipes_section",
        "# README\n\n## Getting Started\ndecoy body\n\n"
        "## Community recipes\n\n"
        "[`RECIPES/example-slug/`](RECIPES/example-slug/)\n\n"
        "## Contributing\ntail decoy\n",
        "\n[`RECIPES/example-slug/`](RECIPES/example-slug/)\n\n",
        "# README\n\n## Getting Started\nonly this section exists\n",
        "",
    ),
    (
        "chronicle_readme_check",
        "_episodes_section",
        "# Chronicle\n\n## About\ndecoy body\n\n"
        "## Episodes\n\n"
        "[Episode 1: Founding](0001.md)\n\n"
        "## Archive\ntail decoy\n",
        "\n[Episode 1: Founding](0001.md)\n\n",
        "# Chronicle\n\n## About\nonly this section exists\n",
        "",
    ),
]


class FrozenOutputRegressionCase(unittest.TestCase):
    """Each sibling's real, unmodified section-reader still produces
    exactly the pre-refactor output on both the header-found and
    header-missing path."""

    def test_every_sibling_extracts_the_expected_section_body(self):
        for name, fn_name, text_with, expected_with, *_rest in SIBLINGS:
            with self.subTest(sibling=name):
                mod = _load(name, os.path.join(TOOLS, f"{name}.py"))
                fn = getattr(mod, fn_name)
                self.assertEqual(fn(text_with), expected_with)

    def test_every_sibling_returns_empty_string_when_header_missing(self):
        for name, fn_name, *_rest, text_without, expected_without in SIBLINGS:
            with self.subTest(sibling=name):
                mod = _load(name, os.path.join(TOOLS, f"{name}.py"))
                fn = getattr(mod, fn_name)
                self.assertEqual(fn(text_without), expected_without)


class SiblingDelegatesIdentityCase(unittest.TestCase):
    """Each sibling's own section-reader source calls text_patterns.
    bounded_section exactly once -- proof of delegation, not just output
    that happens to match today (the same discipline tests/test_violation_
    format.py established for its own six siblings)."""

    def test_every_sibling_calls_the_shared_function_exactly_once(self):
        for name, fn_name, *_rest in SIBLINGS:
            with self.subTest(sibling=name):
                path = os.path.join(TOOLS, f"{name}.py")
                with open(path, encoding="utf-8") as f:
                    tree = ast.parse(f.read())
                calls = 0
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == fn_name:
                        for sub in ast.walk(node):
                            if (
                                isinstance(sub, ast.Call)
                                and isinstance(sub.func, ast.Attribute)
                                and sub.func.attr == "bounded_section"
                                and isinstance(sub.func.value, ast.Name)
                                and sub.func.value.id == "text_patterns"
                            ):
                                calls += 1
                self.assertEqual(
                    calls, 1,
                    f"{name}.{fn_name} does not delegate to "
                    "text_patterns.bounded_section exactly once -- it may "
                    "have been re-forked into its own copy",
                )

    def test_no_sibling_still_hand_rolls_its_own_header_search_body(self):
        """Belt-and-suspenders: none of the three functions' own source
        should still contain a literal `.search(` call inside their body
        (the old hand-written implementation's own tell) now that each is
        a one-line delegating wrapper."""
        for name, fn_name, *_rest in SIBLINGS:
            with self.subTest(sibling=name):
                path = os.path.join(TOOLS, f"{name}.py")
                with open(path, encoding="utf-8") as f:
                    tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == fn_name:
                        source_lines = [
                            ast.dump(n) for n in ast.walk(node)
                            if isinstance(n, ast.Call)
                            and isinstance(n.func, ast.Attribute)
                            and n.func.attr == "search"
                        ]
                        self.assertEqual(
                            source_lines, [],
                            f"{name}.{fn_name} still calls .search() directly "
                            "-- it may have been re-forked into its own copy",
                        )


if __name__ == "__main__":
    unittest.main()
