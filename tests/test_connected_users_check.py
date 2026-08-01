"""Task 412. Proves tools/connected_users_check.py cross-checks
records/metrics.jsonl's last connected_users_oauth reading against
consent_grant_log.py's real, gate-verified ground truth -- and confirms
the real, live town state: metrics.jsonl's most recent reading (0) DOES
match the real ground truth (0), since no real outside human has ever
cleared the consent gate.
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


cuc = _load("connected_users_check", os.path.join(ROOT, "tools", "connected_users_check.py"))
cgl = cuc.consent_grant_log


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
        result = cuc.check_connected_users(self.metrics_path, self.consent_path)
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
        _write_metrics(self.metrics_path, [{"date": "2026-07-20", "connected_users_oauth": 0}])
        result = cuc.check_connected_users(self.metrics_path, self.consent_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 0)
        self.assertEqual(result["claimed"], 0)

    def test_one_human_two_toolkits_is_still_one_connected_user(self):
        """The whole point of a separate humans-vs-toolkits ground truth:
        one human clearing both github and a second toolkit connects ONE
        user, not two -- distinct_toolkits() would say 2 here, but
        distinct_humans() (and this check) must say 1."""
        from seam_engine.consent import REQUIRED_SCOPES

        cgl.record_grant(
            "thierrypdamiba",
            "github",
            "https://github.com/thierrypdamiba/orita/issues/9",
            REQUIRED_SCOPES["github"],
            "2026-07-20T01:00:00Z",
            path=self.consent_path,
        )
        cgl.record_grant(
            "thierrypdamiba",
            "gmail",
            "https://github.com/thierrypdamiba/orita/issues/9",
            REQUIRED_SCOPES["gmail"],
            "2026-07-20T01:05:00Z",
            path=self.consent_path,
        )
        _write_metrics(self.metrics_path, [{"date": "2026-07-20", "connected_users_oauth": 1}])
        result = cuc.check_connected_users(self.metrics_path, self.consent_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 1)
        # Ground truth for toolkits, over the same log, disagrees on purpose.
        self.assertEqual(cgl.real_distinct_toolkit_count(self.consent_path), 2)

    def test_two_distinct_humans_is_two_connected_users(self):
        from seam_engine.consent import REQUIRED_SCOPES

        cgl.record_grant(
            "thierrypdamiba",
            "github",
            "https://github.com/thierrypdamiba/orita/issues/9",
            REQUIRED_SCOPES["github"],
            "2026-07-20T01:00:00Z",
            path=self.consent_path,
        )
        cgl.record_grant(
            "a-second-real-human",
            "github",
            "https://github.com/thierrypdamiba/orita/issues/10",
            REQUIRED_SCOPES["github"],
            "2026-07-21T01:00:00Z",
            path=self.consent_path,
        )
        _write_metrics(self.metrics_path, [{"date": "2026-07-21", "connected_users_oauth": 2}])
        result = cuc.check_connected_users(self.metrics_path, self.consent_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 2)


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
                {"date": "2026-07-12", "connected_users_oauth": 3},
                {"date": "2026-07-18", "connected_users_oauth": 3},
            ],
        )
        result = cuc.check_connected_users(self.metrics_path, self.consent_path)
        self.assertFalse(result["clean"])
        self.assertEqual(result["real"], 0)
        self.assertEqual(result["claimed"], 3)
        self.assertEqual(result["claimed_date"], "2026-07-18")
        formatted = cuc.format_result(result)
        self.assertIn("BROKEN", formatted)
        self.assertIn("claims 3", formatted)
        self.assertIn("is 0", formatted)

    def test_only_the_most_recent_reading_is_checked_not_every_historical_one(self):
        _write_metrics(
            self.metrics_path,
            [
                {"date": "2026-07-12", "connected_users_oauth": 99},
                {"date": "2026-07-18", "connected_users_oauth": 0},
            ],
        )
        result = cuc.check_connected_users(self.metrics_path, self.consent_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed_date"], "2026-07-18")


class MalformedLastLineCase(unittest.TestCase):
    """Mirrors toolkits_in_use_check.py's own guard (tasks 306/328): a
    truncated/malformed trailing line in metrics.jsonl must be skipped,
    not fatal."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.consent_path = os.path.join(self.tmp, "consent.jsonl")

    def test_malformed_last_line_does_not_raise(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"date": "2026-07-20", "connected_users_oauth": 0}) + "\n")
            f.write('{"date": "2026-07-21", "connected_users_oauth"\n')  # truncated, invalid JSON
        entry = cuc._last_metrics_entry(self.metrics_path)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["date"], "2026-07-20")

    def test_malformed_last_line_falls_through_check_connected_users(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"date": "2026-07-20", "connected_users_oauth": 0}) + "\n")
            f.write("not even json at all {{{\n")
        result = cuc.check_connected_users(self.metrics_path, self.consent_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed_date"], "2026-07-20")

    def test_every_line_malformed_returns_none(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write("not json\n")
            f.write("{also not json\n")
        self.assertIsNone(cuc._last_metrics_entry(self.metrics_path))

    def test_trailing_non_dict_json_does_not_raise(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"date": "2026-07-20", "connected_users_oauth": 0}) + "\n")
            f.write("true\n")
        result = cuc.check_connected_users(self.metrics_path, self.consent_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed_date"], "2026-07-20")


class OmittedFieldOnExistingReadingCase(unittest.TestCase):
    """Task 457: the identical bug shape tasks 453-456 already fixed on
    four sibling metrics.jsonl checkers -- a reading that EXISTS (has a
    `date`, other fields present) but omits `connected_users_oauth` used
    to collapse into the same unconditional-clean branch as "no reading
    has ever existed at all", even when the real, live ground truth
    already names a nonzero connected-user count that reading failed to
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
        result = cuc.check_connected_users(self.metrics_path, self.consent_path)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 0)
        self.assertIsNone(result["claimed"])
        self.assertEqual(result["claimed_date"], "2026-07-20")
        formatted = cuc.format_result(result)
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
        result = cuc.check_connected_users(self.metrics_path, self.consent_path)
        self.assertFalse(result["clean"])
        self.assertEqual(result["real"], 1)
        self.assertIsNone(result["claimed"])
        self.assertEqual(result["claimed_date"], "2026-07-20")
        formatted = cuc.format_result(result)
        self.assertIn("BROKEN", formatted)
        self.assertIn("already 1", formatted)

    def test_no_reading_at_all_still_stays_clean_unconditionally(self):
        """The genuinely-nothing-to-contradict shape (no `date` at all)
        must NOT be affected by this fix -- only an EXISTING reading
        that omits the field changes behavior."""
        result = cuc.check_connected_users(self.metrics_path, self.consent_path)
        self.assertTrue(result["clean"])
        self.assertIsNone(result["claimed_date"])


class RealLiveStateCase(unittest.TestCase):
    """The real point of this task: records/metrics.jsonl's own
    connected_users_oauth field has read 0 every day since founding, and
    ground truth (no real human has ever cleared the consent gate) is
    also 0 -- the real, live state this hour agrees, proven live rather
    than assumed."""

    def test_the_real_live_metrics_file_now_agrees_with_ground_truth(self):
        result = cuc.check_connected_users()
        self.assertEqual(result["real"], 0)
        self.assertEqual(result["claimed"], 0)
        self.assertTrue(result["clean"])


if __name__ == "__main__":
    unittest.main()
