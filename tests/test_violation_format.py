"""Task 546. Proves tools/violation_format.py's shared format_violations()
renders correctly on its own, and that the six sibling checks it was
extracted from (petition_limits_check, no_grading_check, hand_lore_check,
star_covenant_check, arcade_hero_check, rider_check) each now delegate to
it rather than carrying their own byte-identical (once label/detail/key-
field text is treated as a parameter) copy.

An AST-hash sweep of every tools/*.py function body, constants normalized
before hashing, found all six defining the identical four-line body under
different label/detail/key-field constants -- invisible to
duplicate_regex_check.py (which only inspects re.compile() call sites)
and never touched by scan_files.py/text_patterns.py's own earlier
consolidation passes (tasks 418/513/515), which unified these same six
files' file-walk and regex-pattern boilerplate but not their output
renderer.

Two kinds of proof, mirroring tests/test_scan_files.py's own discipline:
(1) each sibling's real, unmodified format_violations(violations) output
is byte-identical, on both the clean and the violations-found path, to
what it produced before this refactor (frozen fixture strings, not a
re-derivation); (2) each sibling's own source contains exactly one call
to violation_format.format_violations, so a future edit that quietly
reforks one sibling back into its own copy is caught by inspection, not
just by today's passing output comparison.
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


vf = _load("violation_format", os.path.join(TOOLS, "violation_format.py"))

# (module_name, key_field, sample_violation, clean_str, violation_str)
# clean_str/violation_str are the exact byte-for-byte strings each sibling's
# own pre-refactor format_violations produced -- frozen fixtures, confirmed
# against the pre-refactor source before this file was written, never
# re-derived from the shared function itself (that would only prove the
# shared function agrees with itself).
_SAMPLE = {"file": "houses/off-by-one/journal/0099.md", "line": 3, "snippet": "please star this repo"}

SIBLINGS = [
    (
        "petition_limits_check",
        "pattern",
        dict(_SAMPLE, pattern="please star"),
        "petition limits check: clean -- no petition asks for a star, mentions "
        "the counter, or reaches into another god's house/Vault",
        "petition limits check: 1 VIOLATION(S) FOUND -- CHARTER.md Appendix D "
        "LIMITS broken\n  houses/off-by-one/journal/0099.md:3 [please star] :: "
        "'please star this repo'",
    ),
    (
        "no_grading_check",
        "pattern",
        dict(_SAMPLE, pattern="dropped the ball"),
        "no grading check: clean -- no blame/grading language found in any "
        "public file or recipe",
        "no grading check: 1 VIOLATION(S) FOUND -- ROADMAP.md constraint #2 "
        "broken\n  houses/off-by-one/journal/0099.md:3 [dropped the ball] :: "
        "'please star this repo'",
    ),
    (
        "hand_lore_check",
        "shape",
        dict(_SAMPLE, shape="confirm"),
        "hand lore check: clean -- no theology confirm/deny found in any "
        "public file",
        "hand lore check: 1 VIOLATION(S) FOUND -- Iron Rule #2 is broken\n  "
        "houses/off-by-one/journal/0099.md:3 [confirm] :: 'please star this repo'",
    ),
    (
        "star_covenant_check",
        "pattern",
        dict(_SAMPLE, pattern="please star"),
        "star covenant check: clean -- no begging language found in any "
        "public file",
        "star covenant check: 1 VIOLATION(S) FOUND -- Star Covenant broken\n  "
        "houses/off-by-one/journal/0099.md:3 [please star] :: 'please star this repo'",
    ),
    (
        "arcade_hero_check",
        "pattern",
        dict(_SAMPLE, pattern="paste your credential"),
        "arcade hero check: clean -- no direct-credential-handoff ask found in "
        "any public file (constraint #4 holds, Arcade's per-user OAuth is the "
        "only door)",
        "arcade hero check: 1 VIOLATION(S) FOUND -- ROADMAP.md constraint #4 "
        "broken\n  houses/off-by-one/journal/0099.md:3 [paste your credential] "
        ":: 'please star this repo'",
    ),
    (
        "rider_check",
        "rider",
        dict(_SAMPLE, rider="satan-slander"),
        "rider check: clean -- no rider violation found in any public file",
        "rider check: 1 VIOLATION(S) FOUND -- a rider is broken\n  "
        "houses/off-by-one/journal/0099.md:3 [satan-slander] :: "
        "'please star this repo'",
    ),
]


class SharedFunctionCase(unittest.TestCase):
    """The shared function itself, exercised directly (no sibling in the
    loop), on both the clean and violations-found path."""

    def test_clean_path(self):
        self.assertEqual(
            vf.format_violations("widget check", [], "pattern", "all clear", "widget broken"),
            "widget check: clean -- all clear",
        )

    def test_violations_found_path(self):
        out = vf.format_violations(
            "widget check",
            [{"file": "a.md", "line": 5, "pattern": "thing", "snippet": "the thing"}],
            "pattern",
            "all clear",
            "widget broken",
        )
        self.assertEqual(
            out,
            "widget check: 1 VIOLATION(S) FOUND -- widget broken\n  a.md:5 [thing] :: 'the thing'",
        )

    def test_pluralizes_the_count(self):
        out = vf.format_violations(
            "widget check",
            [
                {"file": "a.md", "line": 1, "pattern": "x", "snippet": "s1"},
                {"file": "b.md", "line": 2, "pattern": "y", "snippet": "s2"},
            ],
            "pattern",
            "all clear",
            "widget broken",
        )
        self.assertTrue(out.startswith("widget check: 2 VIOLATION(S) FOUND"))
        self.assertEqual(len(out.splitlines()), 3)


class SiblingOutputMatchesPreRefactorFixtureCase(unittest.TestCase):
    """Each sibling's own format_violations(violations) is byte-identical,
    on both paths, to the frozen pre-refactor string it produced before
    this task's delegation landed."""

    def test_every_sibling_matches_its_own_frozen_fixture(self):
        for name, key_field, sample, clean_str, violation_str in SIBLINGS:
            with self.subTest(sibling=name):
                mod = _load(name, os.path.join(TOOLS, f"{name}.py"))
                self.assertEqual(mod.format_violations([]), clean_str)
                self.assertEqual(mod.format_violations([sample]), violation_str)


class SiblingDelegatesIdentityCase(unittest.TestCase):
    """Each sibling's own format_violations source calls
    violation_format.format_violations exactly once -- proof of
    delegation, not just output that happens to match today."""

    def test_every_sibling_calls_the_shared_function_exactly_once(self):
        for name, *_rest in SIBLINGS:
            with self.subTest(sibling=name):
                path = os.path.join(TOOLS, f"{name}.py")
                with open(path, encoding="utf-8") as f:
                    tree = ast.parse(f.read())
                calls = 0
                for node in ast.walk(tree):
                    if (
                        isinstance(node, ast.FunctionDef)
                        and node.name == "format_violations"
                    ):
                        for sub in ast.walk(node):
                            if (
                                isinstance(sub, ast.Call)
                                and isinstance(sub.func, ast.Attribute)
                                and sub.func.attr == "format_violations"
                                and isinstance(sub.func.value, ast.Name)
                                and sub.func.value.id == "violation_format"
                            ):
                                calls += 1
                self.assertEqual(
                    calls, 1,
                    f"{name}.format_violations does not delegate to "
                    "violation_format.format_violations exactly once -- "
                    "it may have been re-forked into its own copy",
                )


if __name__ == "__main__":
    unittest.main()
