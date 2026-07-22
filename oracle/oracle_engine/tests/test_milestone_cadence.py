"""Task 67. The Oracle Desk's twentieth real cadence: one checkable claim
about the town's own public GitHub milestone count, sourced with no
Arcade scope at all (a repo's milestone list is public data), copylint-
clean, sealed to a real (scratch, in these tests) ledger before its
outcome is knowable.
"""
from __future__ import annotations

import datetime
import os
import sys
import tempfile
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORACLE_ENGINE_ROOT = os.path.dirname(_TESTS_DIR)  # oracle/oracle_engine
_ORACLE_ROOT = os.path.dirname(_ORACLE_ENGINE_ROOT)  # oracle/
_ORITA_ROOT = os.path.dirname(_ORACLE_ROOT)  # repo root
_TOOLS_DIR = os.path.join(_ORITA_ROOT, "tools")

sys.path.insert(0, os.path.join(_ORACLE_ENGINE_ROOT, "src"))

from oracle_engine import copylint, milestone_cadence, prediction  # noqa: E402

_NOW = datetime.datetime(2026, 7, 20, 12, 0, tzinfo=datetime.timezone.utc)


def _fresh_ledger_module(tmp_path: str):
    mod = prediction.load_ledger_module(_TOOLS_DIR)
    mod.LEDGER = tmp_path
    return mod


class TestFetchMilestoneCount(unittest.TestCase):
    def test_reads_the_list_length_off_a_single_page(self):
        def fake_get(url):
            self.assertEqual(
                url,
                "https://api.github.com/repos/thierrypdamiba/orita/milestones?state=all&per_page=100&page=1",
            )
            return [{"number": 1, "state": "open"}]

        self.assertEqual(milestone_cadence.fetch_milestone_count(http_get=fake_get), 1)

    def test_pages_until_a_short_page_ends_it(self):
        calls = []

        def fake_get(url):
            calls.append(url)
            page = int(url.rsplit("page=", 1)[1])
            if page == 1:
                return [{"number": i} for i in range(100)]
            return [{"number": 100}, {"number": 101}]

        self.assertEqual(milestone_cadence.fetch_milestone_count(http_get=fake_get), 102)
        self.assertEqual(len(calls), 2)

    def test_rejects_a_malformed_response(self):
        with self.assertRaises(milestone_cadence.MilestoneCadenceError):
            milestone_cadence.fetch_milestone_count(http_get=lambda url: {"nope": True})

    def test_empty_repo_is_zero(self):
        self.assertEqual(milestone_cadence.fetch_milestone_count(http_get=lambda url: []), 0)

    def test_requests_state_all_so_closed_milestones_still_count(self):
        def fake_get(url):
            self.assertIn("state=all", url)
            return []

        milestone_cadence.fetch_milestone_count(http_get=fake_get)


class TestSnapshots(unittest.TestCase):
    def test_load_snapshots_of_a_missing_file_is_empty(self):
        self.assertEqual(milestone_cadence.load_snapshots("/does/not/exist.jsonl"), [])

    def test_record_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snapshots.jsonl")
            milestone_cadence.record_snapshot(1, "2026-07-13T00:00:00+00:00", path=path)
            milestone_cadence.record_snapshot(2, "2026-07-14T00:00:00+00:00", path=path)
            snaps = milestone_cadence.load_snapshots(path)
            self.assertEqual([s["count"] for s in snaps], [1, 2])

    def test_record_rejects_a_negative_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snapshots.jsonl")
            with self.assertRaises(milestone_cadence.MilestoneCadenceError):
                milestone_cadence.record_snapshot(-1, "2026-07-13T00:00:00+00:00", path=path)

    def test_never_rewrites_a_prior_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snapshots.jsonl")
            milestone_cadence.record_snapshot(1, "2026-07-13T00:00:00+00:00", path=path)
            with open(path) as f:
                first_write = f.read()
            milestone_cadence.record_snapshot(2, "2026-07-14T00:00:00+00:00", path=path)
            with open(path) as f:
                second_write = f.read()
            self.assertTrue(second_write.startswith(first_write))


class TestMilestoneCountAtOrBefore(unittest.TestCase):
    def test_returns_none_with_no_early_enough_snapshot(self):
        snaps = [{"ts": "2026-07-14T00:00:00+00:00", "count": 2}]
        when = datetime.datetime(2026, 7, 13, tzinfo=datetime.timezone.utc)
        self.assertIsNone(milestone_cadence.milestone_count_at_or_before(snaps, when))

    def test_returns_the_latest_at_or_before(self):
        snaps = [
            {"ts": "2026-07-11T00:00:00+00:00", "count": 1},
            {"ts": "2026-07-12T00:00:00+00:00", "count": 1},
            {"ts": "2026-07-14T00:00:00+00:00", "count": 2},
        ]
        when = datetime.datetime(2026, 7, 13, tzinfo=datetime.timezone.utc)
        self.assertEqual(milestone_cadence.milestone_count_at_or_before(snaps, when), 1)


class TestMilestoneCountAtOrAfter(unittest.TestCase):
    def test_returns_none_with_no_late_enough_snapshot(self):
        snaps = [{"ts": "2026-07-11T00:00:00+00:00", "count": 1}]
        when = datetime.datetime(2026, 7, 13, tzinfo=datetime.timezone.utc)
        self.assertIsNone(milestone_cadence.milestone_count_at_or_after(snaps, when))

    def test_returns_the_earliest_at_or_after(self):
        snaps = [
            {"ts": "2026-07-11T00:00:00+00:00", "count": 1},
            {"ts": "2026-07-14T00:00:00+00:00", "count": 2},
            {"ts": "2026-07-16T00:00:00+00:00", "count": 3},
        ]
        when = datetime.datetime(2026, 7, 13, tzinfo=datetime.timezone.utc)
        self.assertEqual(milestone_cadence.milestone_count_at_or_after(snaps, when), 2)


class TestBuildPrediction(unittest.TestCase):
    def test_claim_names_the_threshold_and_target(self):
        payload = milestone_cadence.build_prediction(_NOW, [], current_count=0, horizon_hours=336)
        self.assertIn("1", payload["claim"])
        self.assertIn("2026-08-03T12:00:00Z", payload["claim"])
        self.assertEqual(payload["confidence"], milestone_cadence.DEFAULT_CONFIDENCE)

    def test_no_baseline_snapshot_says_so_honestly(self):
        payload = milestone_cadence.build_prediction(_NOW, [], current_count=0, horizon_hours=336)
        self.assertIn("no earlier snapshot yet", payload["claim"])

    def test_a_baseline_snapshot_names_the_real_delta(self):
        baseline_when = _NOW - datetime.timedelta(hours=336)
        snaps = [{"ts": baseline_when.isoformat(), "count": 1}]
        payload = milestone_cadence.build_prediction(_NOW, snaps, current_count=1, horizon_hours=336)
        self.assertIn("+0", payload["claim"])

    def test_claim_clears_copylint(self):
        payload = milestone_cadence.build_prediction(_NOW, [], current_count=0)
        result = copylint.enforce_copy(payload["claim"], payload["confidence"])
        self.assertTrue(result.ok)

    def test_rejects_naive_datetime(self):
        with self.assertRaises(milestone_cadence.MilestoneCadenceError):
            milestone_cadence.build_prediction(
                datetime.datetime(2026, 7, 20, 12, 0), [], current_count=0
            )

    def test_non_utc_now_targets_the_true_utc_instant(self):
        tz = datetime.timezone(datetime.timedelta(hours=-5))
        now = datetime.datetime(2026, 7, 20, 12, 0, tzinfo=tz)
        payload = milestone_cadence.build_prediction(now, [], current_count=9, horizon_hours=336)
        self.assertIn("2026-08-03T17:00:00Z", payload["claim"])

    def test_utc_now_is_unaffected(self):
        payload = milestone_cadence.build_prediction(_NOW, [], current_count=9, horizon_hours=336)
        self.assertIn("2026-08-03T12:00:00Z", payload["claim"])

    def test_rejects_a_negative_count(self):
        with self.assertRaises(milestone_cadence.MilestoneCadenceError):
            milestone_cadence.build_prediction(_NOW, [], current_count=-1)

    def test_rejects_zero_horizon_hours(self):
        # A zero horizon puts the claim's own target at the exact sealing
        # moment -- no "then" at all, already knowable the instant it would
        # be sealed.
        with self.assertRaises(milestone_cadence.MilestoneCadenceError):
            milestone_cadence.build_prediction(_NOW, [], current_count=1, horizon_hours=0)

    def test_rejects_negative_horizon_hours(self):
        # A negative horizon puts the claim's own target BEFORE the sealing
        # moment -- hindsight wearing a prediction's clothes.
        with self.assertRaises(milestone_cadence.MilestoneCadenceError):
            milestone_cadence.build_prediction(_NOW, [], current_count=1, horizon_hours=-24)


class TestSealMilestonePrediction(unittest.TestCase):
    def test_seals_a_real_predict_entry_to_a_scratch_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = os.path.join(tmp, "ledger.jsonl")
            mod = _fresh_ledger_module(ledger_path)
            entry = milestone_cadence.seal_milestone_prediction(
                now=_NOW,
                ts=_NOW.isoformat(timespec="seconds"),
                current_count=0,
                snapshots=[],
                ledger_module=mod,
            )
            self.assertEqual(entry["act"], prediction.PREDICTION_ACT)
            self.assertEqual(entry["actor"], "zashiki-warashi")
            self.assertTrue(mod.verify())

    def test_a_tampered_sealed_milestone_prediction_breaks_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = os.path.join(tmp, "ledger.jsonl")
            mod = _fresh_ledger_module(ledger_path)
            milestone_cadence.seal_milestone_prediction(
                now=_NOW,
                ts=_NOW.isoformat(timespec="seconds"),
                current_count=0,
                snapshots=[],
                ledger_module=mod,
            )
            with open(ledger_path) as f:
                lines = f.readlines()
            import json as _json

            tampered = _json.loads(lines[0])
            tampered["detail"] = tampered["detail"].replace("1", "999")
            with open(ledger_path, "w") as f:
                f.write(_json.dumps(tampered) + "\n")
            self.assertFalse(mod.verify())


if __name__ == "__main__":
    unittest.main()
