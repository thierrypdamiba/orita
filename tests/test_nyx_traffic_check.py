"""Task 465. Proves tools/nyx_traffic_check.py's weekly scan actually
counts real-calendar Mondays since founding against dated filenames in
`orita-vault/vault/nyx/traffic/` -- mirroring tests/test_what_moved_check.py's
own shape for the sibling cadence family it's built alongside (chronicle,
what-moved, thegap), and proving the live, real gap this module surfaces:
as of task 465, `orita-vault/vault/nyx/traffic/` does not exist at all and
every real Monday since founding is missed.
"""
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT_ROOT = os.path.join(os.path.dirname(ROOT), "orita-vault")
# dawn-run's workflow checks out only this public repo, never the private
# orita-vault sibling -- the same boundary test_journal_numbering_check.py's
# RealCheckoutCase and test_thegap_check.py's RealVaultCase already draw.
_VAULT_CHECKED_OUT = os.path.isdir(os.path.join(VAULT_ROOT, "vault"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ntc = _load("nyx_traffic_check", os.path.join(ROOT, "tools", "nyx_traffic_check.py"))


class FixtureCadenceCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.vault = os.path.join(self.tmp, "orita-vault")

    def _traffic_dir(self):
        return os.path.join(self.vault, "vault", "nyx", "traffic")

    def _report(self, date_iso, slug=None, ext="md", content="x"):
        name = f"{date_iso}-{slug}.{ext}" if slug else f"{date_iso}.{ext}"
        path = os.path.join(self._traffic_dir(), name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_no_directory_at_all_misses_every_real_monday(self):
        # The real live shape orita-vault/vault/nyx/traffic/ is in as of
        # task 465: the directory does not exist at all.
        result = ntc.compute_cadence(self.vault, today=date(2026, 7, 29))
        self.assertEqual(result["total_reports_on_record"], 0)
        self.assertIsNone(result["latest_report"])
        self.assertEqual(result["mondays_due"], ["2026-07-13", "2026-07-20", "2026-07-27"])
        self.assertEqual(result["missed_mondays"], ["2026-07-13", "2026-07-20", "2026-07-27"])

    def test_empty_directory_is_the_same_as_no_directory(self):
        os.makedirs(self._traffic_dir())
        result = ntc.compute_cadence(self.vault, today=date(2026, 7, 29))
        self.assertEqual(result["total_reports_on_record"], 0)
        self.assertEqual(result["missed_mondays"], ["2026-07-13", "2026-07-20", "2026-07-27"])

    def test_founding_day_itself_owes_nothing(self):
        result = ntc.compute_cadence(self.vault, today=date(2026, 7, 11))
        self.assertEqual(result["mondays_due"], [])
        self.assertEqual(result["missed_mondays"], [])

    def test_one_report_inside_each_mondays_week_is_clean(self):
        self._report("2026-07-14")
        self._report("2026-07-21")
        # Two real Mondays owed by 07-22 (07-13, 07-20); a report landing
        # anywhere inside each Monday's own calendar week (Mon-Sun) covers
        # it, not only the Monday's exact date.
        result = ntc.compute_cadence(self.vault, today=date(2026, 7, 22))
        self.assertEqual(result["mondays_due"], ["2026-07-13", "2026-07-20"])
        self.assertEqual(result["total_reports_on_record"], 2)
        self.assertEqual(result["missed_mondays"], [])

    def test_partial_catch_up_names_only_the_still_missing_monday(self):
        self._report("2026-07-14")
        result = ntc.compute_cadence(self.vault, today=date(2026, 7, 29))
        self.assertEqual(result["missed_mondays"], ["2026-07-20", "2026-07-27"])

    def test_slug_suffix_and_json_extension_both_parse(self):
        self._report("2026-07-14", slug="views-referrers", ext="json")
        result = ntc.compute_cadence(self.vault, today=date(2026, 7, 15))
        self.assertEqual(result["total_reports_on_record"], 1)
        self.assertEqual(result["missed_mondays"], [])

    def test_latest_report_is_the_most_recent_dated_file(self):
        self._report("2026-07-14")
        self._report("2026-07-28")
        self._report("2026-07-21")
        result = ntc.compute_cadence(self.vault, today=date(2026, 7, 29))
        self.assertEqual(result["latest_report"], "2026-07-28")

    def test_non_dated_filename_is_ignored_not_fatal(self):
        os.makedirs(self._traffic_dir())
        with open(os.path.join(self._traffic_dir(), "README.md"), "w") as f:
            f.write("x")
        result = ntc.compute_cadence(self.vault, today=date(2026, 7, 15))
        self.assertEqual(result["total_reports_on_record"], 0)

    def test_content_of_a_matched_file_is_never_read(self):
        # Proclamation 0001 boundary: this module reads filenames only.
        # A file whose content would raise if opened as text (or as JSON)
        # still parses cleanly by name alone.
        self._report("2026-07-14", content="\xff\xfe not valid utf-8 text as bytes would be")
        result = ntc.compute_cadence(self.vault, today=date(2026, 7, 15))
        self.assertEqual(result["total_reports_on_record"], 1)

    def test_format_cadence_clean(self):
        result = {
            "total_reports_on_record": 2,
            "latest_report": "2026-07-28",
            "mondays_due": ["2026-07-13", "2026-07-20"],
            "missed_mondays": [],
            "today": "2026-07-29",
        }
        line = ntc.format_cadence(result)
        self.assertIn("current", line)
        self.assertIn("2 report(s)", line)

    def test_format_cadence_lapsed(self):
        result = {
            "total_reports_on_record": 0,
            "latest_report": None,
            "mondays_due": ["2026-07-13", "2026-07-20", "2026-07-27"],
            "missed_mondays": ["2026-07-13", "2026-07-20", "2026-07-27"],
            "today": "2026-07-29",
        }
        line = ntc.format_cadence(result)
        self.assertIn("3 Cluster Days lapsed", line)
        self.assertIn("2026-07-13, 2026-07-20, 2026-07-27", line)
        self.assertIn("never carried a dated report", line)

    def test_default_vault_dir_falls_back_to_the_real_sibling_path(self):
        # No override: DEFAULT_VAULT_DIR resolves to the real orita-vault
        # sibling checkout path (proven structurally, not by requiring it
        # to actually exist in every environment this test runs in).
        expected = os.path.join(os.path.dirname(ROOT), "orita-vault")
        self.assertEqual(ntc.DEFAULT_VAULT_DIR, expected)


class RealVaultCase(unittest.TestCase):
    """The live gap this module exists to surface, provable only where
    the real orita-vault sibling checkout is actually present (a
    developer's machine, this session) -- never in public CI, which
    checks out only this repo (the same boundary
    test_journal_numbering_check.py's RealCheckoutCase and
    test_thegap_check.py's RealVaultCase already draw)."""

    @unittest.skipUnless(
        _VAULT_CHECKED_OUT,
        "orita-vault sibling checkout not present (expected in public CI, which checks out only orita)",
    )
    def test_real_live_vault_today_reproduces_the_named_gap(self):
        # As of task 465, orita-vault/vault/nyx/traffic/ has never
        # existed -- every real Monday since founding through today is
        # missed, honestly, not backfilled.
        result = ntc.compute_cadence(VAULT_ROOT, today=date(2026, 8, 1))
        self.assertEqual(result["total_reports_on_record"], 0)
        self.assertEqual(result["missed_mondays"], ["2026-07-13", "2026-07-20", "2026-07-27"])


if __name__ == "__main__":
    unittest.main()
