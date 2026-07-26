"""Task 39's grading half: scoring a fork-cadence prediction the moment its
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

from oracle_engine import fork_autograde, fork_cadence, grading, prediction  # noqa: E402


def _fresh_ledger_module(tmp_path: str):
    mod = prediction.load_ledger_module(_TOOLS_DIR)
    mod.LEDGER = tmp_path
    return mod


class AutogradeTestBase(unittest.TestCase):
    def setUp(self):
        self.ledger_path = os.path.join(_TESTS_DIR, "_scratch_fork_autograde_ledger.jsonl")
        if os.path.exists(self.ledger_path):
            os.remove(self.ledger_path)
        self.mod = _fresh_ledger_module(self.ledger_path)
        self.snapshot_path = os.path.join(_TESTS_DIR, "_scratch_fork_snapshots.jsonl")

    def tearDown(self):
        for p in (self.ledger_path, self.snapshot_path):
            if os.path.exists(p):
                os.remove(p)

    def _seal_fork_call(self, sealed_at: str, target: str, threshold: int = 3, confidence: float = 0.55):
        claim = (
            f"By {target}, thierrypdamiba/orita's public GitHub fork count will be at "
            f"least {threshold} (currently {threshold - 1}, no earlier snapshot yet to compare against)."
        )
        return prediction.seal_prediction(
            "kothar-wa-khasis", claim, confidence, ts=sealed_at, ledger_module=self.mod
        )


class TestParseForkClaim(unittest.TestCase):
    def test_parses_target_and_threshold(self):
        claim = (
            "By 2026-08-03T12:00:00Z, thierrypdamiba/orita's public GitHub fork count "
            "will be at least 3 (currently 2, net change over the past 336h: +1)."
        )
        target, threshold = fork_autograde.parse_fork_claim(claim)
        self.assertEqual(threshold, 3)
        self.assertEqual(
            target, datetime.datetime(2026, 8, 3, 12, 0, tzinfo=datetime.timezone.utc)
        )

    def test_rejects_a_non_fork_claim(self):
        with self.assertRaises(fork_autograde.ForkAutogradeError):
            fork_autograde.parse_fork_claim("a star opens within 30 days")


class TestFindDueCalls(AutogradeTestBase):
    def test_a_call_whose_window_has_not_closed_is_not_due(self):
        self._seal_fork_call(sealed_at="2026-07-20T12:00:00+00:00", target="2026-08-03T12:00:00Z")
        now = datetime.datetime(2026, 7, 21, tzinfo=datetime.timezone.utc)
        due = fork_autograde.find_due_calls(self.mod._entries(), now)
        self.assertEqual(due, [])

    def test_a_call_past_its_window_is_due(self):
        self._seal_fork_call(sealed_at="2026-07-20T12:00:00+00:00", target="2026-08-03T12:00:00Z")
        now = datetime.datetime(2026, 8, 4, tzinfo=datetime.timezone.utc)
        due = fork_autograde.find_due_calls(self.mod._entries(), now)
        self.assertEqual(len(due), 1)

    def test_an_already_terminally_graded_call_is_not_due_again(self):
        call = self._seal_fork_call(sealed_at="2026-07-20T12:00:00+00:00", target="2026-08-03T12:00:00Z")
        grading.seal_grade(
            "ogun", call["seq"], "correct", ts="2026-08-03T13:00:00+00:00", ledger_module=self.mod,
        )
        now = datetime.datetime(2026, 8, 4, tzinfo=datetime.timezone.utc)
        due = fork_autograde.find_due_calls(self.mod._entries(), now)
        self.assertEqual(due, [])

    def test_a_schema_mismatched_prior_grade_is_ignored_not_raised(self):
        # A tampered/malformed prior grade record (valid JSON, but not the
        # exact {"call_seq", "outcome"} shape grading.parse_grade_detail
        # enforces) must not crash find_due_calls -- it should be treated
        # like existing_grades already treats an unparseable one: ignored.
        import json as _json

        call = self._seal_fork_call(sealed_at="2026-07-20T12:00:00+00:00", target="2026-08-03T12:00:00Z")
        tampered_detail = _json.dumps(
            {"call_seq": call["seq"], "outcome": "pending", "note": "tampered"}, sort_keys=True
        )
        self.mod.append("ogun", grading.GRADE_ACT, tampered_detail, "2026-07-21T00:00:00+00:00")
        now = datetime.datetime(2026, 8, 4, tzinfo=datetime.timezone.utc)
        due = fork_autograde.find_due_calls(self.mod._entries(), now)
        self.assertEqual(len(due), 1)

    def test_a_star_cadence_shaped_prediction_is_skipped_not_raised(self):
        prediction.seal_prediction(
            "off-by-one",
            "By 2026-07-27T12:00:00Z, thierrypdamiba/orita's public GitHub stargazer count "
            "will be at least 5 (currently 4, no earlier snapshot yet to compare against).",
            0.6,
            ts="2026-07-20T12:00:00+00:00",
            ledger_module=self.mod,
        )
        now = datetime.datetime(2026, 8, 4, tzinfo=datetime.timezone.utc)
        due = fork_autograde.find_due_calls(self.mod._entries(), now)
        self.assertEqual(due, [])

    def test_a_non_dict_predict_payload_is_skipped_not_raised(self):
        # A tampered/malformed `predict` entry (valid JSON, but not a JSON
        # object -- e.g. a bare string) must not crash find_due_calls with
        # an uncaught TypeError -- skipped like any other malformed entry.
        import json as _json

        self.mod.append(
            "off-by-one", prediction.PREDICTION_ACT, _json.dumps("not-a-dict"),
            "2026-07-20T12:00:00+00:00",
        )
        now = datetime.datetime(2026, 8, 4, tzinfo=datetime.timezone.utc)
        due = fork_autograde.find_due_calls(self.mod._entries(), now)
        self.assertEqual(due, [])


class TestScoreCall(AutogradeTestBase):
    def test_scores_correct_when_the_recorded_snapshot_meets_threshold(self):
        call = self._seal_fork_call(
            sealed_at="2026-07-20T12:00:00+00:00", target="2026-08-03T12:00:00Z", threshold=3
        )
        fork_cadence.record_snapshot(4, "2026-08-03T13:00:00+00:00", path=self.snapshot_path)
        snapshots = fork_cadence.load_snapshots(self.snapshot_path)
        self.assertEqual(fork_autograde.score_call(call, snapshots), "correct")

    def test_scores_incorrect_when_the_recorded_snapshot_misses_threshold(self):
        call = self._seal_fork_call(
            sealed_at="2026-07-20T12:00:00+00:00", target="2026-08-03T12:00:00Z", threshold=3
        )
        fork_cadence.record_snapshot(2, "2026-08-03T13:00:00+00:00", path=self.snapshot_path)
        snapshots = fork_cadence.load_snapshots(self.snapshot_path)
        self.assertEqual(fork_autograde.score_call(call, snapshots), "incorrect")

    def test_raises_when_no_snapshot_exists_at_or_after_the_target(self):
        call = self._seal_fork_call(
            sealed_at="2026-07-20T12:00:00+00:00", target="2026-08-03T12:00:00Z", threshold=3
        )
        with self.assertRaises(fork_autograde.ForkAutogradeError):
            fork_autograde.score_call(call, [])


class TestAutogradeDuePredictions(AutogradeTestBase):
    def test_a_quiet_run_seals_nothing(self):
        self._seal_fork_call(sealed_at="2026-07-20T12:00:00+00:00", target="2026-08-03T12:00:00Z")
        now = datetime.datetime(2026, 7, 21, tzinfo=datetime.timezone.utc)
        sealed = fork_autograde.autograde_due_predictions(
            now=now, ts=now.isoformat(), snapshot_path=self.snapshot_path, ledger_module=self.mod,
        )
        self.assertEqual(sealed, [])

    def test_a_due_but_unscoreable_call_stays_ungraded(self):
        self._seal_fork_call(sealed_at="2026-07-20T12:00:00+00:00", target="2026-08-03T12:00:00Z")
        now = datetime.datetime(2026, 8, 4, tzinfo=datetime.timezone.utc)
        sealed = fork_autograde.autograde_due_predictions(
            now=now, ts=now.isoformat(), snapshot_path=self.snapshot_path, ledger_module=self.mod,
        )
        self.assertEqual(sealed, [])
        self.assertEqual(self.mod._entries()[-1]["act"], "predict")

    def test_a_due_scoreable_call_gets_exactly_one_terminal_grade_linked_by_seq(self):
        call = self._seal_fork_call(
            sealed_at="2026-07-20T12:00:00+00:00", target="2026-08-03T12:00:00Z", threshold=3
        )
        fork_cadence.record_snapshot(4, "2026-08-03T13:00:00+00:00", path=self.snapshot_path)
        now = datetime.datetime(2026, 8, 4, tzinfo=datetime.timezone.utc)
        sealed = fork_autograde.autograde_due_predictions(
            now=now, ts=now.isoformat(), snapshot_path=self.snapshot_path, ledger_module=self.mod,
        )
        self.assertEqual(len(sealed), 1)
        payload = grading.parse_grade_detail(sealed[0]["detail"])
        self.assertEqual(payload["call_seq"], call["seq"])
        self.assertEqual(payload["outcome"], "correct")

    def test_running_twice_does_not_double_grade(self):
        self._seal_fork_call(
            sealed_at="2026-07-20T12:00:00+00:00", target="2026-08-03T12:00:00Z", threshold=3
        )
        fork_cadence.record_snapshot(4, "2026-08-03T13:00:00+00:00", path=self.snapshot_path)
        now = datetime.datetime(2026, 8, 4, tzinfo=datetime.timezone.utc)
        first = fork_autograde.autograde_due_predictions(
            now=now, ts=now.isoformat(), snapshot_path=self.snapshot_path, ledger_module=self.mod,
        )
        second = fork_autograde.autograde_due_predictions(
            now=now, ts=now.isoformat(), snapshot_path=self.snapshot_path, ledger_module=self.mod,
        )
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])

    def test_now_must_be_timezone_aware(self):
        with self.assertRaises(fork_autograde.ForkAutogradeError):
            fork_autograde.autograde_due_predictions(
                now=datetime.datetime(2026, 8, 4, 0, 0),
                ts="2026-08-04T00:00:00+00:00",
                ledger_module=self.mod,
            )


if __name__ == "__main__":
    unittest.main()
