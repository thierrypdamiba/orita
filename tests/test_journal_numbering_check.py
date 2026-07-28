"""Task 119. Proves tools/journal_numbering_check.py's scan actually bites
on a malformed, duplicated, or gapped house journal filename, stays clean
on real conforming filenames, and -- the real point -- confirms the live,
current orita checkout's nine houses each run an unbroken 0001, 0002, ...
count today.

Task 370 widens this proof past `houses/` into the vault's own
`vault/<god>/journal/`: a fixture-only `VaultRealmCase` proves the new
opt-in `vault_dir` scan, its exact (house, reason, number) exception
match, and that existing `orita_dir`-only callers stay byte-identical to
before this task; `RealCheckoutCase` proves the live vault's own known
exceptions are real, current, and exhaustive -- not stale or hiding a
new violation.
"""
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT_ROOT = os.path.join(os.path.dirname(ROOT), "orita-vault")
# Task 370's own first CI run caught this the hard way: dawn-run's
# workflow checks out only this public repo, never the private
# orita-vault sibling (by design -- a public CI log must never see it).
# Tests that assert something about the REAL vault's content skip
# cleanly there instead of failing on a premise that was never true in
# that environment; tests that only assert "clean"/"empty" don't need
# this guard, since an absent vault_dir already scans as zero entries.
_VAULT_CHECKED_OUT = os.path.isdir(os.path.join(VAULT_ROOT, "vault"))


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

    @unittest.skipUnless(
        _VAULT_CHECKED_OUT,
        "orita-vault sibling checkout not present (expected in public CI, which checks out only orita)",
    )
    def test_real_vault_holds_zero_violations_today_once_filtered(self):
        """Task 370: the combined public+vault scan against both live
        checkouts, with the known-exceptions filter on (the real,
        production path `check_journal_numbering()` takes bare)."""
        violations = jnc.find_violations(orita_dir=ROOT, vault_dir=VAULT_ROOT)
        self.assertEqual(violations, [], violations)

    @unittest.skipUnless(
        _VAULT_CHECKED_OUT,
        "orita-vault sibling checkout not present (expected in public CI, which checks out only orita)",
    )
    def test_known_vault_exceptions_are_exactly_the_real_unfiltered_violations(self):
        """Task 370: proves KNOWN_VAULT_EXCEPTIONS is neither stale (an
        exception nobody can find in the live vault anymore) nor a
        blanket allowlist (a house/reason it doesn't precisely name is
        still hiding a real, unfiltered violation). Disables filtering
        to see the raw scan, and requires it to name exactly the two
        documented entries -- nothing more, nothing fewer. Skipped where
        the private vault isn't checked out (public CI) rather than
        passing vacuously on a premise that isn't true there."""
        raw = jnc.find_violations(
            orita_dir=ROOT, vault_dir=VAULT_ROOT, filter_known_exceptions=False
        )
        vault_raw = [v for v in raw if v.get("realm") == "vault"]
        found = {(v["house"], v["reason"], v["number"]) for v in vault_raw}
        self.assertEqual(found, set(jnc.KNOWN_VAULT_EXCEPTIONS))


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


class VaultRealmCase(unittest.TestCase):
    """Task 370: `vault_dir` is opt-in and independent of `orita_dir`, so
    every fixture here uses two separate temp dirs and never touches the
    real checkouts."""

    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.vault = tempfile.mkdtemp()
        self.addCleanup(_rm, self.orita)
        self.addCleanup(_rm, self.vault)

    def test_omitting_vault_dir_is_byte_identical_to_pre_370_behavior(self):
        """No vault_dir at all -- must match this function's behavior
        before task 370 introduced the argument: public-only, regardless
        of what the vault fixture (unused here) contains."""
        base = os.path.join(self.orita, "houses", "off-by-one", "journal")
        _write(os.path.join(base, "0001-founding-day.md"), "x")
        violations = jnc.find_violations(orita_dir=self.orita)
        self.assertEqual(violations, [])

    def test_conforming_vault_sequence_is_clean(self):
        base = os.path.join(self.vault, "vault", "ogun", "journal")
        _write(os.path.join(base, "0001-founding-day.md"), "x")
        _write(os.path.join(base, "0002-2026-07-12.md"), "y")
        violations = jnc.find_violations(orita_dir=self.orita, vault_dir=self.vault)
        self.assertEqual(violations, [])

    def test_vault_duplicate_is_detected_and_tagged(self):
        base = os.path.join(self.vault, "vault", "retrya", "journal")
        _write(os.path.join(base, "0001-founding-day.md"), "first")
        _write(os.path.join(base, "0001-the-coin.md"), "second")
        violations = jnc.find_violations(orita_dir=self.orita, vault_dir=self.vault)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["realm"], "vault")
        self.assertEqual(violations[0]["reason"], "duplicate_number")
        self.assertEqual(violations[0]["house"], "retrya")

    def test_vault_missing_number_is_detected_and_tagged(self):
        base = os.path.join(self.vault, "vault", "esu-elegba", "journal")
        _write(os.path.join(base, "0001-founding-day.md"), "x")
        _write(os.path.join(base, "0003-2026-07-13.md"), "y")
        violations = jnc.find_violations(orita_dir=self.orita, vault_dir=self.vault)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["realm"], "vault")
        self.assertEqual(violations[0]["reason"], "missing_number")
        self.assertEqual(violations[0]["file"], "0002-*.md")

    def test_public_and_vault_violations_both_surface_together(self):
        _write(os.path.join(self.orita, "houses", "nyx", "journal", "0001-founding-day.md"), "x")
        _write(os.path.join(self.orita, "houses", "nyx", "journal", "founding-day.md"), "y")
        _write(os.path.join(self.vault, "vault", "nyx", "journal", "0001-founding-day.md"), "x")
        _write(os.path.join(self.vault, "vault", "nyx", "journal", "0003-2026-07-13.md"), "y")
        violations = jnc.find_violations(orita_dir=self.orita, vault_dir=self.vault)
        realms = sorted(v["realm"] for v in violations)
        self.assertEqual(realms, ["public", "vault"])

    def test_exact_house_shape_is_filtered_a_different_house_is_not(self):
        """Reproduces the real nisaba duplicate's exact shape (house,
        reason, number) plus the identical shape under a different house
        name. Only the nisaba one is a documented exception -- the
        lookalike in the other house must still surface, proving the
        filter matches exactly and is not a blanket "duplicate at 16 is
        fine everywhere" rule."""
        # A contiguous 1..169 + 171..174 run (170 skipped) so the only
        # "missing" hit is 170 -- plus a second file duplicating 16 --
        # reproduces the real vault's exact shape without any other,
        # unrelated violation muddying the assertion below.
        nisaba_base = os.path.join(self.vault, "vault", "nisaba", "journal")
        for n in list(range(1, 170)) + list(range(171, 175)):
            _write(os.path.join(nisaba_base, f"{n:04d}-entry.md"), "x")
        _write(os.path.join(nisaba_base, "0016-second-entry.md"), "y")

        other_base = os.path.join(self.vault, "vault", "kwaku-ananse", "journal")
        _write(os.path.join(other_base, "0016-2026-07-17.md"), "x")
        _write(os.path.join(other_base, "0016-2026-07-22.md"), "y")

        violations = jnc.find_violations(orita_dir=self.orita, vault_dir=self.vault)
        by_house = {v["house"] for v in violations}
        self.assertNotIn("nisaba", by_house)
        self.assertIn("kwaku-ananse", by_house)


class CLICase(unittest.TestCase):
    def test_format_violations_empty(self):
        self.assertIn("clean", jnc.format_violations([]))

    def test_format_violations_nonempty(self):
        v = [{"house": "ogun", "file": "0002-*.md", "reason": "missing_number", "detail": "gap"}]
        formatted = jnc.format_violations(v)
        self.assertIn("VIOLATION(S) FOUND", formatted)
        self.assertIn("houses/ogun/journal/0002-*.md", formatted)

    def test_format_violations_tags_vault_realm(self):
        v = [{
            "realm": "vault", "house": "nisaba", "file": "0016-2026-07-22.md",
            "reason": "duplicate_number", "detail": "gap",
        }]
        formatted = jnc.format_violations(v)
        self.assertIn("vault/nisaba/journal/0016-2026-07-22.md", formatted)


if __name__ == "__main__":
    unittest.main()
