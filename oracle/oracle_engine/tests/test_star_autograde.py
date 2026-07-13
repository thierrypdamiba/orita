"""Task 38's grading half: scoring a star-cadence prediction the moment its
target passes, off the real recorded snapshot log, exactly once, never
early, never on a guess.
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

from oracle_engine import grading, prediction, star_autograde, star_cadence  # noqa: E402


def _fresh_ledger_module(tmp_path: str):
    mod = prediction.load_ledger_module(_TOOLS_DIR)
    mod.LEDGER = tmp_path
    return mod


class AutogradeTestBase(unittest.TestCase):
    def setUp(self):
        self.ledger_path = os.path.join(_TESTS_DIR, "_scratch_star_autograde_ledger.jsonl")
        if os.path.exists(self.ledger_path):
            os.remove(self.ledger_path)
        self.mod = _fresh_ledger_module(self.ledger_path)
        self.snapshot_path = os.path.join(_TESTS_DIR, "_scratch_star_snapshots.jsonl")

    def tearDown(self):
        for p in (self.ledger_path, self.snapshot_path):
            if os.path.exists(p):
                os.remove(p)

    def _seal_star_call(self, sealed_at: str, target: str, threshold: int = 5, confidence: float = 0.6):
        claim = (
            f"By {target}, thierrypdamiba/orita's public GitHub stargazer count will be at "
            f"least {threshold} (currently {threshold - 1}, no earlier snapshot yet to compare against)."
        )
        return prediction.seal_prediction(
            "off-by-one", claim, confidence, ts=sealed_at, ledger_module=self.mod
        )


class TestParseStarClaim(unittest.TestCase):
    def test_parses_target_and_threshold(self):
        claim = (
            "By 2026-07-27T12:00:00Z, thierrypdamiba/orita's public GitHub stargazer count "
            "will be at least 5 (currently 4, net change over the past 168h: +2)."
        )
        target, threshold = star_autograde.parse_star_claim(claim)
        self.assertEqual(threshold, 5)
        self.assertEqual(
            target, datetime.datetime(2026, 7, 27, 12, 0, tzinfo=datetime.timezone.utc)
        )

    def test_rejects_a_non_star_claim(self):
        with self.assertRaises(star_autograde.StarAutogradeError):
            star_autograde.parse_star_claim("a fork opens within 30 days")


class TestFindDueCalls(AutogradeTestBase):
    def test_a_call_whose_window_has_not_closed_is_not_due(self):
        self._seal_star_call(sealed_at="2026-07-20T12:00:00+00:00", target="2026-07-27T12:00:00Z")
        now = datetime.datetime(2026, 7, 21, tzinfo=datetime.timezone.utc)
        due = star_autograde.find_due_calls(self.mod._entries(), now)
        self.assertEqual(due, [])

    def test_a_call_past_its_window_is_due(self):
        self._seal_star_call(sealed_at="2026-07-20T12:00:00+00:00", target="2026-07-27T12:00:00Z")
        now = datetime.datetime(2026, 7, 28, tzinfo=datetime.timezone.utc)
        due = star_autograde.find_due_calls(self.mod._entries(), now)
        self.assertEqual(len(due), 1)

    def test_an_already_terminally_graded_call_is_not_due_again(self):
        call = self._seal_star_call(sealed_at="2026-07-20T12:00:00+00:00", target="2026-07-27T12:00:00Z")
        grading.seal_grade(
            "ogun", call["seq"], "correct", ts="2026-07-27T13:00:00+00:00", ledger_module=self.mod,
        )
        now = datetime.datetime(2026, 7, 28, tzinfo=datetime.timezone.utc)
        due = star_autograde.find_due_calls(self.mod._entries(), now)
        self.assertEqual(due, [])

    def test_a_cadence_shaped_prediction_is_skipped_not_raised(self):
        prediction.seal_prediction(
            "off-by-one",
            "By 2026-07-14T11:12:14Z, BUILDLOG.md will record at least 3 distinct numbered "
            "ROADMAP task(s) newly shipped between now and then (the 24h window just past logged 5).",
            0.7,
            ts="2026-07-13T11:12:14+00:00",
            ledger_module=self.mod,
        )
        now = datetime.datetime(2026, 7, 28, tzinfo=datetime.timezone.utc)
        due = star_autograde.find_due_calls(self.mod._entries(), now)
        self.assertEqual(due, [])


class TestScoreCall(AutogradeTestBase):
    def test_scores_correct_when_the_recorded_snapshot_meets_threshold(self):
        call = self._seal_star_call(
            sealed_at="2026-07-20T12:00:00+00:00", target="2026-07-27T12:00:00Z", threshold=5
        )
        star_cadence.record_snapshot(6, "2026-07-27T13:00:00+00:00", path=self.snapshot_path)
        snapshots = star_cadence.load_snapshots(self.snapshot_path)
        self.assertEqual(star_autograde.score_call(call, snapshots), "correct")

    def test_scores_incorrect_when_the_recorded_snapshot_misses_threshold(self):
        call = self._seal_star_call(
            sealed_at="2026-07-20T12:00:00+00:00", target="2026-07-27T12:00:00Z", threshold=5
        )
        star_cadence.record_snapshot(4, "2026-07-27T13:00:00+00:00", path=self.snapshot_path)
        snapshots = star_cadence.load_snapshots(self.snapshot_path)
        self.assertEqual(star_autograde.score_call(call, snapshots), "incorrect")

    def test_raises_when_no_snapshot_exists_at_or_before_the_target(self):
        call = self._seal_star_call(
            sealed_at="2026-07-20T12:00:00+00:00", target="2026-07-27T12:00:00Z", threshold=5
        )
        with self.assertRaises(star_autograde.StarAutogradeError):
            star_autograde.score_call(call, [])


class TestAutogradeDuePredictions(AutogradeTestBase):
    def test_a_quiet_run_seals_nothing(self):
        self._seal_star_call(sealed_at="2026-07-20T12:00:00+00:00", target="2026-07-27T12:00:00Z")
        now = datetime.datetime(2026, 7, 21, tzinfo=datetime.timezone.utc)
        sealed = star_autograde.autograde_due_predictions(
            now=now, ts=now.isoformat(), snapshot_path=self.snapshot_path, ledger_module=self.mod,
        )
        self.assertEqual(sealed, [])

    def test_a_due_but_unscoreable_call_stays_ungraded(self):
        self._seal_star_call(sealed_at="2026-07-20T12:00:00+00:00", target="2026-07-27T12:00:00Z")
        now = datetime.datetime(2026, 7, 28, tzinfo=datetime.timezone.utc)
        sealed = star_autograde.autograde_due_predictions(
            now=now, ts=now.isoformat(), snapshot_path=self.snapshot_path, ledger_module=self.mod,
        )
        self.assertEqual(sealed, [])
        self.assertEqual(self.mod._entries()[-1]["act"], "predict")

    def test_a_due_scoreable_call_gets_exactly_one_terminal_grade_linked_by_seq(self):
        call = self._seal_star_call(
            sealed_at="2026-07-20T12:00:00+00:00", target="2026-07-27T12:00:00Z", threshold=5
        )
        star_cadence.record_snapshot(6, "2026-07-27T13:00:00+00:00", path=self.snapshot_path)
        now = datetime.datetime(2026, 7, 28, tzinfo=datetime.timezone.utc)
        sealed = star_autograde.autograde_due_predictions(
            now=now, ts=now.isoformat(), snapshot_path=self.snapshot_path, ledger_module=self.mod,
        )
        self.assertEqual(len(sealed), 1)
        payload = grading.parse_grade_detail(sealed[0]["detail"])
        self.assertEqual(payload["call_seq"], call["seq"])
        self.assertEqual(payload["outcome"], "correct")

    def test_running_twice_does_not_double_grade(self):
        self._seal_star_call(
            sealed_at="2026-07-20T12:00:00+00:00", target="2026-07-27T12:00:00Z", threshold=5
        )
        star_cadence.record_snapshot(6, "2026-07-27T13:00:00+00:00", path=self.snapshot_path)
        now = datetime.datetime(2026, 7, 28, tzinfo=datetime.timezone.utc)
        first = star_autograde.autograde_due_predictions(
            now=now, ts=now.isoformat(), snapshot_path=self.snapshot_path, ledger_module=self.mod,
        )
        second = star_autograde.autograde_due_predictions(
            now=now, ts=now.isoformat(), snapshot_path=self.snapshot_path, ledger_module=self.mod,
        )
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])

    def test_now_must_be_timezone_aware(self):
        with self.assertRaises(star_autograde.StarAutogradeError):
            star_autograde.autograde_due_predictions(
                now=datetime.datetime(2026, 7, 28, 0, 0),
                ts="2026-07-28T00:00:00+00:00",
                ledger_module=self.mod,
            )


if __name__ == "__main__":
    unittest.main()
