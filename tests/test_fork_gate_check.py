"""Task 1356. Proves tools/fork_gate_check.py actually catches drift
between PLATFORM.md's "What is Orita's alone" content list and the
fork-my-own-society.md issue template's own hand-typed enumeration of it
-- not just asserts "clean" against today's files, which would pass even
if the parser silently matched nothing.
"""
import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


fgc = _load("fork_gate_check", os.path.join(ROOT, "tools", "fork_gate_check.py"))

REAL_PLATFORM = os.path.join(ROOT, "PLATFORM.md")
REAL_TEMPLATE = os.path.join(ROOT, ".github", "ISSUE_TEMPLATE", "fork-my-own-society.md")

GOOD_PLATFORM = """# Fork Your Own Society

## What travels free (mechanism)

These are yours the moment you fork.

1. **The Road** -- the design rule.
2. **The Ledger pattern** -- an append-only chain.

## What is Orita's alone (content) -- rename or replace, don't inherit

1. **The pantheon.** Your fork writes its own.
2. **The vault.** Private to this town.
3. **The ledger's own entries.** Not the mechanism.
4. **The flagship.** Yours can be anything.
5. **Iron Rules content.** Write your own.

## The five steps

1. **Fork** the repo.
"""

GOOD_TEMPLATE = """
does not (content, your pantheon, your vault, your ledger's own entries, your flagship, your Iron Rules content):
"""


class NormalizeItemCase(unittest.TestCase):
    def test_the_prefixed_period_suffixed_label_strips_both(self):
        self.assertEqual(fgc.normalize_item("The pantheon."), "pantheon")

    def test_your_prefixed_label_strips_the_prefix(self):
        self.assertEqual(fgc.normalize_item("your pantheon"), "pantheon")

    def test_multiword_label_lowercases_and_keeps_apostrophe(self):
        self.assertEqual(fgc.normalize_item("The ledger's own entries."), "ledger's own entries")
        self.assertEqual(fgc.normalize_item("your ledger's own entries"), "ledger's own entries")

    def test_a_future_item_normalizes_with_no_code_change(self):
        self.assertEqual(fgc.normalize_item("The Oracle desk."), "oracle desk")
        self.assertEqual(fgc.normalize_item("your Oracle desk"), "oracle desk")


class ParsePlatformContentItemsCase(unittest.TestCase):
    def test_parses_only_the_content_section_items_in_order(self):
        items = fgc.parse_platform_content_items(GOOD_PLATFORM)
        self.assertEqual(
            items,
            ["pantheon", "vault", "ledger's own entries", "flagship", "iron rules content"],
        )

    def test_mechanism_section_items_are_not_parsed(self):
        items = fgc.parse_platform_content_items(GOOD_PLATFORM)
        self.assertNotIn("road", items)

    def test_missing_section_returns_empty(self):
        self.assertEqual(fgc.parse_platform_content_items("# nothing here"), [])


class ParseTemplateContentItemsCase(unittest.TestCase):
    def test_parses_every_item_in_order(self):
        items = fgc.parse_template_content_items(GOOD_TEMPLATE)
        self.assertEqual(
            items,
            ["pantheon", "vault", "ledger's own entries", "flagship", "iron rules content"],
        )

    def test_missing_parenthetical_returns_empty(self):
        self.assertEqual(fgc.parse_template_content_items("nothing to see here"), [])


class FindDriftCase(unittest.TestCase):
    def test_matching_lists_have_no_drift(self):
        items = ["pantheon", "vault", "flagship"]
        self.assertEqual(fgc.find_drift(items, list(items)), [])

    def test_an_item_missing_from_the_template_is_flagged(self):
        problems = fgc.find_drift(["pantheon", "vault", "flagship"], ["pantheon", "vault"])
        self.assertEqual(len(problems), 1)
        self.assertIn("flagship", problems[0])

    def test_an_extra_item_in_the_template_is_flagged(self):
        problems = fgc.find_drift(["pantheon", "vault"], ["pantheon", "vault", "oracle desk"])
        self.assertEqual(len(problems), 1)
        self.assertIn("oracle desk", problems[0])

    def test_a_duplicate_item_on_the_platform_side_is_flagged(self):
        problems = fgc.find_drift(["pantheon", "pantheon", "vault"], ["pantheon", "vault"])
        self.assertTrue(any("PLATFORM.md" in p and "pantheon" in p for p in problems))

    def test_a_duplicate_item_on_the_template_side_is_flagged(self):
        problems = fgc.find_drift(["pantheon", "vault"], ["pantheon", "pantheon", "vault"])
        self.assertTrue(any("template" in p and "pantheon" in p for p in problems))


class CheckCase(unittest.TestCase):
    def test_good_pair_is_clean(self):
        ok, msg = fgc.check(
            platform_path=self._write(GOOD_PLATFORM, "platform.md"),
            template_path=self._write(GOOD_TEMPLATE, "template.md"),
        )
        self.assertTrue(ok, msg)

    def test_renamed_platform_item_is_caught(self):
        drifted = GOOD_PLATFORM.replace("**The pantheon.**", "**The pantheons.**")
        ok, msg = fgc.check(
            platform_path=self._write(drifted, "platform.md"),
            template_path=self._write(GOOD_TEMPLATE, "template.md"),
        )
        self.assertFalse(ok)
        self.assertIn("pantheon", msg)

    def test_missing_content_header_is_caught(self):
        drifted = GOOD_PLATFORM.replace("## What is Orita's alone (content)", "## Renamed section")
        ok, msg = fgc.check(
            platform_path=self._write(drifted, "platform.md"),
            template_path=self._write(GOOD_TEMPLATE, "template.md"),
        )
        self.assertFalse(ok)
        self.assertIn("no such header", msg)

    def test_missing_platform_file_is_named_honestly(self):
        ok, msg = fgc.check(
            platform_path="/nonexistent/PLATFORM.md",
            template_path=self._write(GOOD_TEMPLATE, "template.md"),
        )
        self.assertFalse(ok)
        self.assertIn("not found", msg)

    def test_missing_template_file_is_named_honestly(self):
        ok, msg = fgc.check(
            platform_path=self._write(GOOD_PLATFORM, "platform.md"),
            template_path="/nonexistent/template.md",
        )
        self.assertFalse(ok)
        self.assertIn("not found", msg)

    _tmp_files: list[str] = []

    def _write(self, text: str, name: str) -> str:
        import tempfile

        path = os.path.join(tempfile.mkdtemp(), name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path


class RealLiveStateCase(unittest.TestCase):
    """The actual point: today's real PLATFORM.md really does match today's
    real fork-my-own-society.md, checked structurally, not by re-asserting
    the claim."""

    def test_the_real_files_agree(self):
        ok, msg = fgc.check(REAL_PLATFORM, REAL_TEMPLATE)
        self.assertTrue(ok, msg)

    def test_the_real_platform_content_section_has_five_items(self):
        with open(REAL_PLATFORM, encoding="utf-8") as f:
            items = fgc.parse_platform_content_items(f.read())
        self.assertEqual(len(items), 5)
        self.assertEqual(len(items), len(set(items)))


class CliCase(unittest.TestCase):
    def test_check_on_the_real_files_exits_zero(self):
        self.assertEqual(fgc.main(["check", REAL_PLATFORM, REAL_TEMPLATE]), 0)

    def test_check_with_defaults_exits_zero(self):
        self.assertEqual(fgc.main(["check"]), 0)

    def test_missing_file_exits_nonzero(self):
        self.assertEqual(fgc.main(["check", "/nonexistent/PLATFORM.md"]), 1)

    def test_no_args_exits_with_usage(self):
        self.assertEqual(fgc.main([]), 2)


if __name__ == "__main__":
    unittest.main()
