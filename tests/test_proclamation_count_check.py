"""Task 547. Proves tools/proclamation_count_check.py cross-checks
HAND/README.md's "There has/have been <word>." sentence against the real,
live count of HAND/proclamations/*.md files -- both the number and the
has/have grammar -- and that it actually catches a real drift rather than
just describing the shape of one.
"""
import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


pcc = _load("proclamation_count_check", os.path.join(ROOT, "tools", "proclamation_count_check.py"))


def _write_proclamations(tmp, names):
    d = os.path.join(tmp, "proclamations")
    os.makedirs(d)
    for name in names:
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            f.write("content\n")
    return d


def _write_readme(tmp, sentence):
    path = os.path.join(tmp, "README.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# The Hand\n\nSome prose. {sentence}\n")
    return path


class RealCountCase(unittest.TestCase):
    def test_finds_the_real_proclamations_directory(self):
        count = pcc._real_proclamation_count(pcc.DEFAULT_PROCLAMATIONS_DIR)
        self.assertGreaterEqual(count, 3)

    def test_only_counts_numbered_md_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _write_proclamations(tmp, ["0001-a.md", "0002-b.md", "not-numbered.md", "README.md"])
            self.assertEqual(pcc._real_proclamation_count(d), 2)


class FixtureFreshCase(unittest.TestCase):
    """Isolated tmp-dir fixtures -- no dependency on the live repo's real
    proclamation count, so these keep passing regardless of how many real
    proclamations exist tomorrow."""

    def test_matching_count_and_grammar_is_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _write_proclamations(tmp, ["0001-a.md", "0002-b.md", "0003-c.md"])
            readme = _write_readme(tmp, "There have been three.")
            result = pcc.check_proclamation_count(readme_path=readme, proclamations_dir=d)
            self.assertTrue(result["clean"], result)
            self.assertEqual(result["real_count"], 3)
            self.assertEqual(result["claimed_count"], 3)

    def test_singular_count_uses_has_not_have(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _write_proclamations(tmp, ["0001-a.md"])
            readme = _write_readme(tmp, "There has been one.")
            result = pcc.check_proclamation_count(readme_path=readme, proclamations_dir=d)
            self.assertTrue(result["clean"], result)

    def test_stale_count_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _write_proclamations(tmp, ["0001-a.md", "0002-b.md", "0003-c.md"])
            readme = _write_readme(tmp, "There has been one.")
            result = pcc.check_proclamation_count(readme_path=readme, proclamations_dir=d)
            self.assertFalse(result["clean"])
            self.assertEqual(result["real_count"], 3)
            self.assertEqual(result["claimed_count"], 1)
            self.assertIn("3 real file(s)", result["reason"])

    def test_wrong_grammar_with_correct_number_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _write_proclamations(tmp, ["0001-a.md", "0002-b.md"])
            readme = _write_readme(tmp, "There has been two.")
            result = pcc.check_proclamation_count(readme_path=readme, proclamations_dir=d)
            self.assertFalse(result["clean"])
            self.assertFalse(result["grammar_ok"])
            self.assertEqual(result["claimed_count"], 2)

    def test_missing_sentence_is_flagged_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _write_proclamations(tmp, ["0001-a.md"])
            readme = _write_readme(tmp, "No proclamation sentence here at all.")
            result = pcc.check_proclamation_count(readme_path=readme, proclamations_dir=d)
            self.assertFalse(result["clean"])
            self.assertIsNone(result["claimed_count"])

    def test_unrecognized_number_word_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _write_proclamations(tmp, ["0001-a.md"])
            readme = _write_readme(tmp, "There has been eleventy.")
            result = pcc.check_proclamation_count(readme_path=readme, proclamations_dir=d)
            self.assertFalse(result["clean"])
            self.assertIn("not a recognized number word", result["reason"])

    def test_zero_proclamations_uses_have(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "proclamations")
            os.makedirs(d)
            readme = _write_readme(tmp, "There have been zero.")
            result = pcc.check_proclamation_count(readme_path=readme, proclamations_dir=d)
            self.assertTrue(result["clean"], result)


class FormatResultCase(unittest.TestCase):
    def test_clean_message_names_the_real_count(self):
        text = pcc.format_result({"clean": True, "real_count": 3})
        self.assertIn("3 real proclamation(s)", text)
        self.assertIn("clean", text)

    def test_broken_message_carries_the_reason(self):
        text = pcc.format_result({"clean": False, "reason": "something specific drifted"})
        self.assertIn("BROKEN", text)
        self.assertIn("something specific drifted", text)


class RealLiveRepoCase(unittest.TestCase):
    """The real, live HAND/README.md and HAND/proclamations/ this task
    fixed -- proves the checker is clean against the actual repo state,
    not just isolated fixtures."""

    def test_real_repo_state_is_clean(self):
        result = pcc.check_proclamation_count()
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["real_count"], 3)
        self.assertEqual(result["claimed_count"], 3)

    def test_a_stale_one_proclamation_claim_against_the_real_directory_is_caught(self):
        """Mutation-based hand-verification, same discipline
        test_recipe_readme_check.py's own analogous doctrine tests hold
        themselves to: prove the checker actually flags the exact drift
        this task found, not just that it happens to pass today."""
        with tempfile.TemporaryDirectory() as tmp:
            readme = _write_readme(tmp, "There has been one.")
            result = pcc.check_proclamation_count(
                readme_path=readme, proclamations_dir=pcc.DEFAULT_PROCLAMATIONS_DIR
            )
            self.assertFalse(result["clean"])
            self.assertEqual(result["real_count"], 3)


if __name__ == "__main__":
    unittest.main()
