"""Task 413. Proves tools/gap_true_positive_check.py cross-checks
records/metrics.jsonl's last gap_true_positive_rate reading against the
real, live seam_engine.audit.audit_ledger() tally -- and confirms the
real, live town state: metrics.jsonl's most recent reading (1.0, i.e.
100%) DOES match the real ground truth, since every gap ever audited so
far has been CONFIRMED.
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


gtpc = _load("gap_true_positive_check", os.path.join(ROOT, "tools", "gap_true_positive_check.py"))
from seam_engine import ledger as seam_ledger  # noqa: E402


def _write_metrics(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def _at(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, 12, tzinfo=timezone.utc)


def _scan(*, primary: bool = True, confidence: float = 0.85, bar: float = 0.70) -> dict:
    p = None
    if primary:
        p = {
            "slug": "milestone-unannounced",
            "headline": "h",
            "detail": "d",
            "confidence": confidence,
            "evidence": ["https://github.com/x/orita/commit/0000000"],
            "label": "primary",
        }
    return {
        "generated_at": "t",
        "repo": "x/orita",
        "window_hours": 24,
        "confidence_bar": bar,
        "separation_margin": 0.15,
        "primary_gap": p,
        "tail": [{"slug": "coincidence-a", "confidence": 0.1, "label": "coincidence"}],
        "excluded": [],
    }


class NoMetricsReadingCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.ledger_base = Path(self.tmp) / "ledger"
        self.ledger_base.mkdir()

    def test_missing_metrics_file_is_clean_nothing_to_contradict(self):
        result = gtpc.check_gap_true_positive_rate(self.metrics_path, self.ledger_base)
        self.assertTrue(result["clean"])
        self.assertIsNone(result["claimed"])

    def test_no_reading_and_no_audited_gaps_is_clean(self):
        result = gtpc.check_gap_true_positive_rate(self.metrics_path, self.ledger_base)
        self.assertTrue(result["clean"])
        self.assertIsNone(result["real"])

    def test_a_reading_that_exists_but_names_no_rate_is_clean_when_the_ledger_also_has_none(self):
        # A real reading exists (unlike the missing-file case above), but
        # it explicitly names no rate -- the honest 2026-07-12 shape,
        # written before the self-audit tally existed. Still clean, since
        # the live ledger agrees there is nothing to report either.
        _write_metrics(
            self.metrics_path,
            [{"date": "2026-07-12", "gap_true_positive_rate": None}],
        )
        result = gtpc.check_gap_true_positive_rate(self.metrics_path, self.ledger_base)
        self.assertTrue(result["clean"])
        self.assertIsNone(result["real"])
        self.assertIsNone(result["claimed"])


class AgreementCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.ledger_base = Path(self.tmp) / "ledger"
        self.ledger_base.mkdir()

    def test_all_confirmed_matches_a_claimed_1_0(self):
        seam_ledger.append_scan(_scan(confidence=0.9), now=_at(2026, 7, 12), base=self.ledger_base)
        seam_ledger.append_scan(_scan(confidence=0.9), now=_at(2026, 7, 13), base=self.ledger_base)
        _write_metrics(self.metrics_path, [{"date": "2026-07-13", "gap_true_positive_rate": 1.0}])
        result = gtpc.check_gap_true_positive_rate(self.metrics_path, self.ledger_base)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 1.0)
        self.assertEqual(result["claimed"], 1.0)

    def test_a_fractional_rate_agrees_within_rounding(self):
        # 3 confirmed / 4 total = 0.75 -- one genuine false positive
        # (confidence 0.60 fails a 0.70 bar) alongside three confirmed.
        seam_ledger.append_scan(_scan(confidence=0.9), now=_at(2026, 7, 12), base=self.ledger_base)
        seam_ledger.append_scan(_scan(confidence=0.9), now=_at(2026, 7, 13), base=self.ledger_base)
        seam_ledger.append_scan(_scan(confidence=0.9), now=_at(2026, 7, 14), base=self.ledger_base)
        seam_ledger.append_scan(
            _scan(confidence=0.60, bar=0.70), now=_at(2026, 7, 15), base=self.ledger_base
        )
        _write_metrics(self.metrics_path, [{"date": "2026-07-15", "gap_true_positive_rate": 0.75}])
        result = gtpc.check_gap_true_positive_rate(self.metrics_path, self.ledger_base)
        self.assertTrue(result["clean"])
        self.assertEqual(result["real"], 0.75)


class MismatchCase(unittest.TestCase):
    """The mutation-based proof: a synthetic metrics.jsonl claiming a rate
    that disagrees with real ground truth is flagged, named exactly."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.ledger_base = Path(self.tmp) / "ledger"
        self.ledger_base.mkdir()

    def test_claimed_disagrees_with_real_flips_broken_and_names_both_numbers(self):
        # 3 confirmed / 4 total = 0.75 real, but yesterday's flattering
        # 1.0 got hand-copied forward instead of updated.
        seam_ledger.append_scan(_scan(confidence=0.9), now=_at(2026, 7, 12), base=self.ledger_base)
        seam_ledger.append_scan(_scan(confidence=0.9), now=_at(2026, 7, 13), base=self.ledger_base)
        seam_ledger.append_scan(_scan(confidence=0.9), now=_at(2026, 7, 14), base=self.ledger_base)
        seam_ledger.append_scan(
            _scan(confidence=0.60, bar=0.70), now=_at(2026, 7, 15), base=self.ledger_base
        )
        _write_metrics(
            self.metrics_path,
            [
                {"date": "2026-07-14", "gap_true_positive_rate": 1.0},
                {"date": "2026-07-15", "gap_true_positive_rate": 1.0},
            ],
        )
        result = gtpc.check_gap_true_positive_rate(self.metrics_path, self.ledger_base)
        self.assertFalse(result["clean"])
        self.assertEqual(result["real"], 0.75)
        self.assertEqual(result["claimed"], 1.0)
        self.assertEqual(result["claimed_date"], "2026-07-15")
        formatted = gtpc.format_result(result)
        self.assertIn("BROKEN", formatted)
        self.assertIn("claims 100.0%", formatted)
        self.assertIn("is 75.0%", formatted)

    def test_claiming_a_rate_when_nothing_has_ever_been_audited_is_broken(self):
        _write_metrics(self.metrics_path, [{"date": "2026-07-12", "gap_true_positive_rate": 1.0}])
        result = gtpc.check_gap_true_positive_rate(self.metrics_path, self.ledger_base)
        self.assertFalse(result["clean"])
        self.assertIsNone(result["real"])
        self.assertEqual(result["claimed"], 1.0)
        formatted = gtpc.format_result(result)
        self.assertIn("BROKEN", formatted)
        self.assertIn("no rate exists to claim", formatted)

    def test_null_rate_reading_against_a_real_confirmed_rate_is_broken(self):
        # The ledger already has a real rate to report (1.0), but the
        # most recent metrics.jsonl reading names no rate at all (the
        # 2026-07-12 shape, `null`, replayed on a day the ledger is no
        # longer empty) -- a real rate exists and was silently dropped,
        # not an honest pair of unknowns.
        seam_ledger.append_scan(_scan(confidence=0.9), now=_at(2026, 7, 12), base=self.ledger_base)
        _write_metrics(
            self.metrics_path,
            [{"date": "2026-07-13", "gap_true_positive_rate": None}],
        )
        result = gtpc.check_gap_true_positive_rate(self.metrics_path, self.ledger_base)
        self.assertFalse(result["clean"])
        self.assertEqual(result["real"], 1.0)
        self.assertIsNone(result["claimed"])
        self.assertEqual(result["claimed_date"], "2026-07-13")
        formatted = gtpc.format_result(result)
        self.assertIn("BROKEN", formatted)
        self.assertIn("names no rate", formatted)

    def test_only_the_most_recent_reading_is_checked_not_every_historical_one(self):
        seam_ledger.append_scan(_scan(confidence=0.9), now=_at(2026, 7, 12), base=self.ledger_base)
        _write_metrics(
            self.metrics_path,
            [
                {"date": "2026-07-11", "gap_true_positive_rate": 0.5},
                {"date": "2026-07-12", "gap_true_positive_rate": 1.0},
            ],
        )
        result = gtpc.check_gap_true_positive_rate(self.metrics_path, self.ledger_base)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed_date"], "2026-07-12")


class MalformedLastLineCase(unittest.TestCase):
    """Mirrors connected_users_check.py's own guard (task 412, itself
    following tasks 306/328): a truncated/malformed trailing line in
    metrics.jsonl must be skipped, not fatal."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)
        self.metrics_path = os.path.join(self.tmp, "metrics.jsonl")
        self.ledger_base = Path(self.tmp) / "ledger"
        self.ledger_base.mkdir()

    def test_malformed_last_line_does_not_raise(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"date": "2026-07-20", "gap_true_positive_rate": 1.0}) + "\n")
            f.write('{"date": "2026-07-21", "gap_true_positive_rate"\n')  # truncated, invalid JSON
        entry = gtpc._last_metrics_entry(self.metrics_path)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["date"], "2026-07-20")

    def test_malformed_last_line_falls_through_check(self):
        seam_ledger.append_scan(_scan(confidence=0.9), now=_at(2026, 7, 20), base=self.ledger_base)
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"date": "2026-07-20", "gap_true_positive_rate": 1.0}) + "\n")
            f.write("not even json at all {{{\n")
        result = gtpc.check_gap_true_positive_rate(self.metrics_path, self.ledger_base)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed_date"], "2026-07-20")

    def test_every_line_malformed_returns_none(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write("not json\n")
            f.write("{also not json\n")
        self.assertIsNone(gtpc._last_metrics_entry(self.metrics_path))

    def test_trailing_non_dict_json_does_not_raise(self):
        with open(self.metrics_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"date": "2026-07-20", "gap_true_positive_rate": 1.0}) + "\n")
            f.write("true\n")
        seam_ledger.append_scan(_scan(confidence=0.9), now=_at(2026, 7, 20), base=self.ledger_base)
        result = gtpc.check_gap_true_positive_rate(self.metrics_path, self.ledger_base)
        self.assertTrue(result["clean"])
        self.assertEqual(result["claimed_date"], "2026-07-20")


class RealLiveStateCase(unittest.TestCase):
    """The real point of this task: records/metrics.jsonl's own
    gap_true_positive_rate field has read 1.0 every recorded day, and
    ground truth (seam_engine.audit.audit_ledger(), the real fencepost
    Ledger) also reads 100% CONFIRMED -- the real, live state this hour
    agrees, proven live rather than assumed."""

    def test_the_real_live_metrics_file_now_agrees_with_ground_truth(self):
        result = gtpc.check_gap_true_positive_rate()
        self.assertEqual(result["claimed"], 1.0)
        self.assertEqual(result["real"], 1.0)
        self.assertTrue(result["clean"])


if __name__ == "__main__":
    unittest.main()
