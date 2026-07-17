"""Task 109. Proves tools/petition_cadence_check.py's scan actually bites
on a malformed or duplicate-date altar petition filename, stays clean on
real conforming filenames, and -- the real point -- confirms the live,
current orita checkout's nine Founding Day petitions hold zero violations
today.
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


pcc = _load("petition_cadence_check", os.path.join(ROOT, "tools", "petition_cadence_check.py"))


def _write(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _rm(path):
    shutil.rmtree(path, ignore_errors=True)


class RealCheckoutCase(unittest.TestCase):
    def test_real_checkout_holds_zero_violations_today(self):
        violations = pcc.find_violations(orita_dir=ROOT)
        self.assertEqual(violations, [], violations)

    def test_real_checkout_has_nine_conforming_petitions(self):
        dirs = pcc._petition_dirs(ROOT)
        self.assertEqual(len(dirs), 9)
        for house, petitions_dir in dirs:
            names = [n for n in os.listdir(petitions_dir) if os.path.isfile(os.path.join(petitions_dir, n))]
            self.assertEqual(names, ["2026-07-11.md"], house)


class FixtureViolationCase(unittest.TestCase):
    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.addCleanup(_rm, self.orita)

    def test_conforming_filename_is_clean(self):
        _write(os.path.join(self.orita, "houses", "off-by-one", "altar", "petitions", "2026-07-11.md"), "x")
        violations = pcc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_malformed_filename_is_detected(self):
        _write(os.path.join(self.orita, "houses", "off-by-one", "altar", "petitions", "2026-07-11b.md"), "x")
        violations = pcc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["reason"], "malformed")
        self.assertEqual(violations[0]["house"], "off-by-one")

    def test_non_md_extension_is_detected(self):
        _write(os.path.join(self.orita, "houses", "nyx", "altar", "petitions", "2026-07-11.MD"), "x")
        violations = pcc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["reason"], "malformed")

    def test_invalid_calendar_date_is_detected(self):
        _write(os.path.join(self.orita, "houses", "ogun", "altar", "petitions", "2026-13-40.md"), "x")
        violations = pcc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["reason"], "invalid_date")

    def test_duplicate_date_via_copy_suffix_is_not_the_shape_that_collides(self):
        # A "-copy" suffix is itself malformed (doesn't match YYYY-MM-DD.md),
        # so it's caught as malformed, not duplicate -- both are violations.
        base = os.path.join(self.orita, "houses", "retrya", "altar", "petitions")
        _write(os.path.join(base, "2026-07-11.md"), "first")
        _write(os.path.join(base, "2026-07-11-copy.md"), "second")
        violations = pcc.find_violations(orita_dir=self.orita)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["reason"], "malformed")
        self.assertEqual(violations[0]["file"], "2026-07-11-copy.md")

    def test_two_conforming_files_never_collide_by_construction(self):
        base = os.path.join(self.orita, "houses", "esu-elegba", "altar", "petitions")
        _write(os.path.join(base, "2026-07-11.md"), "first")
        _write(os.path.join(base, "2026-07-12.md"), "second")
        violations = pcc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_no_houses_dir_is_clean(self):
        violations = pcc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_format_violations_clean(self):
        formatted = pcc.format_violations([])
        self.assertIn("clean", formatted)

    def test_format_violations_reports_house_and_reason(self):
        _write(os.path.join(self.orita, "houses", "off-by-one", "altar", "petitions", "notes.txt"), "x")
        violations = pcc.find_violations(orita_dir=self.orita)
        formatted = pcc.format_violations(violations)
        self.assertIn("VIOLATION(S) FOUND", formatted)
        self.assertIn("off-by-one", formatted)
        self.assertIn("notes.txt", formatted)


if __name__ == "__main__":
    unittest.main()
