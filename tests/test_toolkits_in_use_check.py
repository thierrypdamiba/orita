"""Task 145. Proves tools/toolkits_in_use_check.py cross-checks
records/metrics.jsonl's last distinct_toolkits_in_use reading against
consent_grant_log.py's real, gate-verified ground truth -- and confirms
the real, live town state: metrics.jsonl's most recent reading (2) does
NOT match the real ground truth (0), the exact flattering-number gap
this task exists to catch.
"""
import importlib.util
import json
import os
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


tiu = _load("toolkits_in_use_check", os.path.join(ROOT, "tools", "toolkits_in_use_check.py"))
cgl = tiu.consent_grant_log


def _write_metrics(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


class NoMetricsReadingCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.consent_path = os.path.join(self.tmp, "consent.jsonl")

    def test_missing_metrics_file_is_clean_nothing_to_contradict(self):
        result = tiu.check_toolkits_in_use(self.metrics_path, self.consent_path)
        self.assertTrue(result["clean"])
        self.assertIsNone(result["claimed"])
        self.assertEqual(result["real"], 0)


class AgreementCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.consent_path = os.path.join(self.tmp, "consent.jsonl")

    def test_claimed_matches_real_zero_is_clean(self):
        _write_metrics(self.metrics_path, [{"date": "2026-07-20", "distinct_toolkits_in_use": 0}])
        result = tiu.check_toolkits_in_use(self.metrics_path, self.consent_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 0)
        self.assertEqual(result["claimed"], 0)

    def test_claimed_matches_real_nonzero_is_clean(self):
        from seam_engine.consent import REQUIRED_SCOPES

        cgl.record_grant(
            "thierrypdamiba",
            "github",
            "https://github.com/thierrypdamiba/orita/issues/9",
            REQUIRED_SCOPES["github"],
            "2026-07-20T01:00:00Z",
            path=self.consent_path,
        )
        _write_metrics(self.metrics_path, [{"date": "2026-07-20", "distinct_toolkits_in_use": 1}])
        result = tiu.check_toolkits_in_use(self.metrics_path, self.consent_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 1)


class MismatchCase(unittest.TestCase):
    """The mutation-based proof: a synthetic metrics.jsonl claiming a
    number that disagrees with real ground truth is flagged, named
    exactly, and the real (unmutated) matching case stays clean."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.consent_path = os.path.join(self.tmp, "consent.jsonl")

    def test_claimed_disagrees_with_real_flips_broken_and_names_both_numbers(self):
        _write_metrics(
            self.metrics_path,
            [
                {"date": "2026-07-12", "distinct_toolkits_in_use": 2},
                {"date": "2026-07-18", "distinct_toolkits_in_use": 2},
            ],
        )
        result = tiu.check_toolkits_in_use(self.metrics_path, self.consent_path)
        self.assertFalse(result["clean"])
        self.assertEqual(result["real"], 0)
        self.assertEqual(result["claimed"], 2)
        self.assertEqual(result["claimed_date"], "2026-07-18")
        formatted = tiu.format_result(result)
        self.assertIn("BROKEN", formatted)
        self.assertIn("claims 2", formatted)
        self.assertIn("is 0", formatted)

    def test_only_the_most_recent_reading_is_checked_not_every_historical_one(self):
        _write_metrics(
            self.metrics_path,
            [
                {"date": "2026-07-12", "distinct_toolkits_in_use": 99},
                {"date": "2026-07-18", "distinct_toolkits_in_use": 0},
            ],
        )
        result = tiu.check_toolkits_in_use(self.metrics_path, self.consent_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed_date"], "2026-07-18")


class MalformedLastLineCase(unittest.TestCase):
    """Task 306: a truncated/malformed trailing line in metrics.jsonl
    (a crashed daily-aggregate append, a bad hand-edit) must be skipped,
    not fatal -- `_last_metrics_entry()` used to call `json.loads()` on
    the last line unguarded and crash with an uncaught JSONDecodeError."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.consent_path = os.path.join(self.tmp, "consent.jsonl")

    def test_malformed_last_line_does_not_raise(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"date": "2026-07-20", "distinct_toolkits_in_use": 0}) + "\n")
            f.write('{"date": "2026-07-21", "distinct_toolkits_in_use"\n')  # truncated, invalid JSON
        entry = tiu._last_metrics_entry(self.metrics_path)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["date"], "2026-07-20")

    def test_malformed_last_line_falls_through_check_toolkits_in_use(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"date": "2026-07-20", "distinct_toolkits_in_use": 0}) + "\n")
            f.write("not even json at all {{{\n")
        result = tiu.check_toolkits_in_use(self.metrics_path, self.consent_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed_date"], "2026-07-20")

    def test_every_line_malformed_returns_none(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write("not json\n")
            f.write("{also not json\n")
        self.assertIsNone(tiu._last_metrics_entry(self.metrics_path))


class ValidJsonNonDictLastLineCase(unittest.TestCase):
    """Task 328: a trailing line that parses as valid JSON but is not a
    JSON object (`true`, `42`, `3.14`, `null`, a bare array) sailed past
    task 306's `json.JSONDecodeError` guard -- `_last_metrics_entry()`
    happily returned the scalar/list, and `check_toolkits_in_use()`'s
    unconditional `"distinct_toolkits_in_use" not in last` then raised
    an uncaught `TypeError` for int/float/bool/None (`in` is undefined
    for those types), instead of being skipped the same way a
    JSON-decode failure already is."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.consent_path = os.path.join(self.tmp, "consent.jsonl")

    def _write_good_then(self, trailing_json_line):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"date": "2026-07-20", "distinct_toolkits_in_use": 0}) + "\n")
            f.write(trailing_json_line + "\n")

    def test_trailing_bool_does_not_raise_and_falls_back_to_prior_reading(self):
        self._write_good_then("true")
        entry = tiu._last_metrics_entry(self.metrics_path)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["date"], "2026-07-20")
        result = tiu.check_toolkits_in_use(self.metrics_path, self.consent_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed_date"], "2026-07-20")

    def test_trailing_int_does_not_raise(self):
        self._write_good_then("42")
        result = tiu.check_toolkits_in_use(self.metrics_path, self.consent_path)
        self.assertEqual(result["claimed_date"], "2026-07-20")

    def test_trailing_float_does_not_raise(self):
        self._write_good_then("3.14")
        result = tiu.check_toolkits_in_use(self.metrics_path, self.consent_path)
        self.assertEqual(result["claimed_date"], "2026-07-20")

    def test_trailing_null_does_not_raise(self):
        self._write_good_then("null")
        result = tiu.check_toolkits_in_use(self.metrics_path, self.consent_path)
        self.assertEqual(result["claimed_date"], "2026-07-20")

    def test_trailing_json_array_does_not_raise(self):
        self._write_good_then("[1, 2, 3]")
        result = tiu.check_toolkits_in_use(self.metrics_path, self.consent_path)
        self.assertEqual(result["claimed_date"], "2026-07-20")

    def test_only_scalars_and_dicts_are_ever_returned_never_a_bare_list(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write("[1, 2, 3]\n")
        self.assertIsNone(tiu._last_metrics_entry(self.metrics_path))


class OmittedFieldOnExistingReadingCase(unittest.TestCase):
    """Task 454: the same bug shape task 453 found and fixed one field
    over in `gap_true_positive_check.py` -- a reading that EXISTS (has a
    `date`, other fields present) but omits `distinct_toolkits_in_use`
    used to collapse into the identical unconditional-clean branch as
    "no reading has ever existed at all", even when the real, live
    ground truth already names a nonzero count that reading failed to
    carry. Proves both the honest-omission (real is 0, nothing yet to
    have missed) and the broken-omission (real is nonzero, a real count
    went unrecorded) shapes."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.consent_path = os.path.join(self.tmp, "consent.jsonl")

    def test_omitted_field_against_zero_real_is_honestly_clean(self):
        _write_metrics(self.metrics_path, [{"date": "2026-07-20", "reports_shipped_today": 1}])
        result = tiu.check_toolkits_in_use(self.metrics_path, self.consent_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 0)
        self.assertIsNone(result["claimed"])
        self.assertEqual(result["claimed_date"], "2026-07-20")
        formatted = tiu.format_result(result)
        self.assertIn("clean", formatted)
        self.assertIn("nothing omitted", formatted)

    def test_omitted_field_against_a_real_nonzero_count_is_broken(self):
        from seam_engine.consent import REQUIRED_SCOPES

        cgl.record_grant(
            "thierrypdamiba",
            "github",
            "https://github.com/thierrypdamiba/orita/issues/9",
            REQUIRED_SCOPES["github"],
            "2026-07-20T01:00:00Z",
            path=self.consent_path,
        )
        _write_metrics(self.metrics_path, [{"date": "2026-07-20", "reports_shipped_today": 1}])
        result = tiu.check_toolkits_in_use(self.metrics_path, self.consent_path)
        self.assertFalse(result["clean"])
        self.assertEqual(result["real"], 1)
        self.assertIsNone(result["claimed"])
        self.assertEqual(result["claimed_date"], "2026-07-20")
        formatted = tiu.format_result(result)
        self.assertIn("BROKEN", formatted)
        self.assertIn("already 1", formatted)

    def test_no_reading_at_all_still_stays_clean_unconditionally(self):
        """The genuinely-nothing-to-contradict shape (no `date` at all)
        must NOT be affected by this fix -- only an EXISTING reading
        that omits the field changes behavior."""
        result = tiu.check_toolkits_in_use(self.metrics_path, self.consent_path)
        self.assertTrue(result["clean"])
        self.assertIsNone(result["claimed_date"])


class RealLiveStateCase(unittest.TestCase):
    """The real point of this task: records/metrics.jsonl had recorded
    `distinct_toolkits_in_use: 2` every single day since 2026-07-12 --
    definitionally wrong (ground truth is 0, no real outside human has
    ever cleared the consent gate) -- and this task corrected every
    historical entry to the honest 0 rather than leaving a live
    misreport standing. The real, live state this hour now agrees."""

    def test_the_real_live_metrics_file_now_agrees_with_ground_truth(self):
        result = tiu.check_toolkits_in_use()
        self.assertEqual(result["real"], 0)
        self.assertEqual(result["claimed"], 0)
        self.assertTrue(result["clean"])


if __name__ == "__main__":
    unittest.main()
