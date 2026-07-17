"""Task 119. Proves tools/journal_numbering_check.py's scan actually bites
on a malformed, duplicated, or gapped house journal filename, stays clean
on real conforming filenames, and -- the real point -- confirms the live,
current orita checkout's nine houses each run an unbroken 0001, 0002, ...
count today.
"""
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


jnc = _load("journal_numbering_check", os.path.join(ROOT, "tools", "journal_numbering_check.py"))


def _write(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _rm(path):
    shutil.rmtree(path, ignore_errors=True)


class RealCheckoutCase(unittest.TestCase):
    def test_real_checkout_holds_zero_violations_today(self):
        violations = jnc.find_violations(orita_dir=ROOT)
        self.assertEqual(violations, [], violations)

    def test_real_checkout_has_nine_houses_with_journals(self):
        dirs = jnc._journal_dirs(ROOT)
        self.assertEqual(len(dirs), 9)
        for house, journal_dir in dirs:
            names = [n for n in os.listdir(journal_dir) if os.path.isfile(os.path.join(journal_dir, n))]
            self.assertTrue(names, house)
            self.assertTrue(all(jnc._NUMBERED_NAME.match(n) for n in names), (house, names))


class FixtureViolationCase(unittest.TestCase):
    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(_rm, self.orita)

    def test_conforming_sequence_is_clean(self):
        base = os.path.join(self.orita, "houses", "off-by-one", "journal")
        _write(os.path.join(base, "0001-founding-day.md"), "x")
        _write(os.path.join(base, "0002-2026-07-12.md"), "y")
        _write(os.path.join(base, "0003-2026-07-13.md"), "z")
        violations = jnc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_malformed_filename_is_detected(self):
        base = os.path.join(self.orita, "houses", "nyx", "journal")
        _write(os.path.join(base, "0001-founding-day.md"), "x")
        _write(os.path.join(base, "founding-day.md"), "y")
        violations = jnc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["reason"], "malformed")
        self.assertEqual(violations[0]["file"], "founding-day.md")

    def test_three_digit_prefix_is_malformed(self):
        base = os.path.join(self.orita, "houses", "ogun", "journal")
        _write(os.path.join(base, "001-2026-07-11.md"), "x")
        violations = jnc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["reason"], "malformed")

    def test_duplicate_number_is_detected(self):
        base = os.path.join(self.orita, "houses", "retrya", "journal")
        _write(os.path.join(base, "0001-founding-day.md"), "first")
        _write(os.path.join(base, "0001-the-coin.md"), "second")
        violations = jnc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["reason"], "duplicate_number")
        self.assertIn("0001-founding-day.md", violations[0]["detail"])

    def test_gap_in_sequence_is_detected(self):
        base = os.path.join(self.orita, "houses", "esu-elegba", "journal")
        _write(os.path.join(base, "0001-founding-day.md"), "x")
        _write(os.path.join(base, "0003-2026-07-13.md"), "y")
        violations = jnc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["reason"], "missing_number")
        self.assertEqual(violations[0]["file"], "0002-*.md")

    def test_two_conforming_houses_never_collide_across_houses(self):
        _write(os.path.join(self.orita, "houses", "nisaba", "journal", "0001-founding-day.md"), "x")
        _write(os.path.join(self.orita, "houses", "kwaku-ananse", "journal", "0001-founding-day.md"), "y")
        violations = jnc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_no_houses_dir_is_clean(self):
        violations = jnc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_empty_journal_dir_is_clean(self):
        os.makedirs(os.path.join(self.orita, "houses", "zashiki-warashi", "journal"))
        violations = jnc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])


class CLICase(unittest.TestCase):
    def test_format_violations_empty(self):
        self.assertIn("clean", jnc.format_violations([]))

    def test_format_violations_nonempty(self):
        v = [{"house": "ogun", "file": "0002-*.md", "reason": "missing_number", "detail": "gap"}]
        formatted = jnc.format_violations(v)
        self.assertIn("VIOLATION(S) FOUND", formatted)
        self.assertIn("houses/ogun/journal/0002-*.md", formatted)


if __name__ == "__main__":
    unittest.main()
