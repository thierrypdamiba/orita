"""Task 37's machinery: grading a cadence prediction the moment its window
closes, off the real BUILDLOG.md record, exactly once, never early.
"""
from __future__ import annotations

import datetime
import os
import sys
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORACLE_ENGINE_ROOT = os.path.dirname(_TESTS_DIR)  # oracle/oracle_engine
_ORACLE_ROOT = os.path.dirname(_ORACLE_ENGINE_ROOT)  # oracle/
_ORITA_ROOT = os.path.dirname(_ORACLE_ROOT)  # repo root
_TOOLS_DIR = os.path.join(_ORITA_ROOT, "tools")

sys.path.insert(0, os.path.join(_ORACLE_ENGINE_ROOT, "src"))

from oracle_engine import autograde, grading, prediction  # noqa: E402

_LOW_VELOCITY_LOG = """# Build Log

2026-07-13 11:12 UTC | off-by-one | 36 | cadence sealed
2026-07-13 12:00 UTC | ogun | 37 | one task shipped in the window
"""

_HIGH_VELOCITY_LOG = """# Build Log

2026-07-13 11:12 UTC | off-by-one | 36 | cadence sealed
2026-07-13 12:00 UTC | ogun | 37 | task a
2026-07-13 13:00 UTC | retrya | 38 | task b
2026-07-13 14:00 UTC | nisaba | 39 | task c
"""


def _fresh_ledger_module(tmp_path: str):
    mod = prediction.load_ledger_module(_TOOLS_DIR)
    mod.LEDGER = tmp_path
    return mod


def _write_buildlog(tmp_dir: str, text: str) -> str:
    path = os.path.join(tmp_dir, "_scratch_buildlog.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


class AutogradeTestBase(unittest.TestCase):
    def setUp(self):
        self.ledger_path = os.path.join(_TESTS_DIR, "_scratch_autograde_ledger.jsonl")
        if os.path.exists(self.ledger_path):
            os.remove(self.ledger_path)
        self.mod = _fresh_ledger_module(self.ledger_path)
        self.buildlog_path = os.path.join(_TESTS_DIR, "_scratch_autograde_buildlog.md")

    def tearDown(self):
        for p in (self.ledger_path, self.buildlog_path):
            if os.path.exists(p):
                os.remove(p)

    def _seal_cadence_call(self, sealed_at: str, target: str, threshold: int = 3, confidence: float = 0.7):
        claim = (
            f"By {target}, BUILDLOG.md will record at least {threshold} distinct "
            f"numbered ROADMAP task(s) newly shipped between now and then "
            f"(the 24h window just past logged 2)."
        )
        return prediction.seal_prediction(
            "off-by-one", claim, confidence, ts=sealed_at, ledger_module=self.mod
        )


class TestParseCadenceClaim(unittest.TestCase):
    def test_parses_target_and_threshold(self):
        claim = (
            "By 2026-07-14T11:12:14Z, BUILDLOG.md will record at least 3 distinct "
            "numbered ROADMAP task(s) newly shipped between now and then "
            "(the 24h window just past logged 32)."
        )
        target, threshold = autograde.parse_cadence_claim(claim)
        self.assertEqual(threshold, 3)
        self.assertEqual(
            target, datetime.datetime(2026, 7, 14, 11, 12, 14, tzinfo=datetime.timezone.utc)
        )

    def test_rejects_a_non_cadence_claim(self):
        with self.assertRaises(autograde.AutogradeError):
            autograde.parse_cadence_claim("a fork opens within 30 days")


class TestFindDueCalls(AutogradeTestBase):
    def test_a_call_whose_window_has_not_closed_is_not_due(self):
        self._seal_cadence_call(
            sealed_at="2026-07-13T11:12:14+00:00", target="2026-07-14T11:12:14Z"
        )
        now = datetime.datetime(2026, 7, 13, 12, 0, tzinfo=datetime.timezone.utc)
        due = autograde.find_due_calls(self.mod._entries(), now)
        self.assertEqual(due, [])

    def test_a_call_past_its_window_is_due(self):
        self._seal_cadence_call(
            sealed_at="2026-07-13T11:12:14+00:00", target="2026-07-14T11:12:14Z"
        )
        now = datetime.datetime(2026, 7, 15, 0, 0, tzinfo=datetime.timezone.utc)
        due = autograde.find_due_calls(self.mod._entries(), now)
        self.assertEqual(len(due), 1)

    def test_an_already_terminally_graded_call_is_not_due_again(self):
        call = self._seal_cadence_call(
            sealed_at="2026-07-13T11:12:14+00:00", target="2026-07-14T11:12:14Z"
        )
        grading.seal_grade(
            "ogun", call["seq"], "correct",
            ts="2026-07-14T12:00:00+00:00", ledger_module=self.mod,
        )
        now = datetime.datetime(2026, 7, 15, 0, 0, tzinfo=datetime.timezone.utc)
        due = autograde.find_due_calls(self.mod._entries(), now)
        self.assertEqual(due, [])

    def test_a_pending_graded_call_is_still_due(self):
        call = self._seal_cadence_call(
            sealed_at="2026-07-13T11:12:14+00:00", target="2026-07-14T11:12:14Z"
        )
        grading.seal_grade(
            "ogun", call["seq"], "pending",
            ts="2026-07-14T12:00:00+00:00", ledger_module=self.mod,
        )
        now = datetime.datetime(2026, 7, 15, 0, 0, tzinfo=datetime.timezone.utc)
        due = autograde.find_due_calls(self.mod._entries(), now)
        self.assertEqual(len(due), 1)

    def test_a_non_cadence_prediction_is_skipped_not_raised(self):
        prediction.seal_prediction(
            "nisaba", "a fork opens within 30 days", 0.5,
            ts="2026-07-13T00:00:00+00:00", ledger_module=self.mod,
        )
        now = datetime.datetime(2026, 7, 15, 0, 0, tzinfo=datetime.timezone.utc)
        due = autograde.find_due_calls(self.mod._entries(), now)
        self.assertEqual(due, [])

    def test_a_schema_mismatched_prior_grade_is_ignored_not_raised(self):
        # A tampered/malformed prior grade record (valid JSON, but not the
        # exact {"call_seq", "outcome"} shape grading.parse_grade_detail
        # enforces) must not crash find_due_calls -- it should be treated
        # like existing_grades already treats an unparseable one: ignored.
        import json as _json

        call = self._seal_cadence_call(
            sealed_at="2026-07-13T11:12:14+00:00", target="2026-07-14T11:12:14Z"
        )
        tampered_detail = _json.dumps(
            {"call_seq": call["seq"], "outcome": "pending", "note": "tampered"}, sort_keys=True
        )
        self.mod.append("ogun", grading.GRADE_ACT, tampered_detail, "2026-07-14T12:00:00+00:00")
        now = datetime.datetime(2026, 7, 15, 0, 0, tzinfo=datetime.timezone.utc)
        due = autograde.find_due_calls(self.mod._entries(), now)
        self.assertEqual(len(due), 1)


class TestScoreCall(AutogradeTestBase):
    def test_scores_correct_when_velocity_meets_threshold(self):
        call = self._seal_cadence_call(
            sealed_at="2026-07-13T11:12:00+00:00", target="2026-07-13T15:00:00Z", threshold=3
        )
        from oracle_engine.cadence import load_buildlog_entries

        path = _write_buildlog(_TESTS_DIR, _HIGH_VELOCITY_LOG)
        entries = load_buildlog_entries(path)
        outcome = autograde.score_call(call, entries)
        os.remove(path)
        self.assertEqual(outcome, "correct")

    def test_scores_incorrect_when_velocity_misses_threshold(self):
        call = self._seal_cadence_call(
            sealed_at="2026-07-13T11:12:00+00:00", target="2026-07-13T15:00:00Z", threshold=3
        )
        from oracle_engine.cadence import load_buildlog_entries

        path = _write_buildlog(_TESTS_DIR, _LOW_VELOCITY_LOG)
        entries = load_buildlog_entries(path)
        outcome = autograde.score_call(call, entries)
        os.remove(path)
        self.assertEqual(outcome, "incorrect")


class TestAutogradeDuePredictions(AutogradeTestBase):
    def test_a_quiet_run_seals_nothing(self):
        self._seal_cadence_call(
            sealed_at="2026-07-13T11:12:14+00:00", target="2026-07-14T11:12:14Z"
        )
        now = datetime.datetime(2026, 7, 13, 12, 0, tzinfo=datetime.timezone.utc)
        sealed = autograde.autograde_due_predictions(
            now=now, ts=now.isoformat(), buildlog_path=self.buildlog_path,
            ledger_module=self.mod,
        )
        self.assertEqual(sealed, [])
        self.assertEqual(self.mod._entries()[-1]["act"], "predict")

    def test_a_due_call_gets_exactly_one_terminal_grade_linked_by_seq(self):
        with open(self.buildlog_path, "w", encoding="utf-8") as f:
            f.write(_HIGH_VELOCITY_LOG)
        call = self._seal_cadence_call(
            sealed_at="2026-07-13T11:12:00+00:00", target="2026-07-13T15:00:00Z", threshold=3
        )
        now = datetime.datetime(2026, 7, 13, 16, 0, tzinfo=datetime.timezone.utc)
        sealed = autograde.autograde_due_predictions(
            now=now, ts=now.isoformat(), buildlog_path=self.buildlog_path,
            ledger_module=self.mod,
        )
        self.assertEqual(len(sealed), 1)
        payload = grading.parse_grade_detail(sealed[0]["detail"])
        self.assertEqual(payload["call_seq"], call["seq"])
        self.assertEqual(payload["outcome"], "correct")

    def test_running_twice_does_not_double_grade(self):
        with open(self.buildlog_path, "w", encoding="utf-8") as f:
            f.write(_HIGH_VELOCITY_LOG)
        self._seal_cadence_call(
            sealed_at="2026-07-13T11:12:00+00:00", target="2026-07-13T15:00:00Z", threshold=3
        )
        now = datetime.datetime(2026, 7, 13, 16, 0, tzinfo=datetime.timezone.utc)
        first = autograde.autograde_due_predictions(
            now=now, ts=now.isoformat(), buildlog_path=self.buildlog_path,
            ledger_module=self.mod,
        )
        second = autograde.autograde_due_predictions(
            now=now, ts=now.isoformat(), buildlog_path=self.buildlog_path,
            ledger_module=self.mod,
        )
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])

    def test_now_must_be_timezone_aware(self):
        with self.assertRaises(autograde.AutogradeError):
            autograde.autograde_due_predictions(
                now=datetime.datetime(2026, 7, 13, 16, 0),
                ts="2026-07-13T16:00:00+00:00",
                ledger_module=self.mod,
            )


if __name__ == "__main__":
    unittest.main()
