"""Task 43. The Oracle Desk's seventh real cadence: one checkable claim
about the town's own public X (`@oritatown`) tweet count, sourced through
the-hand's already-cleared `X_WhoAmI` read (no new Arcade scope,
`oracle/SCOPES.md`'s `WhoAmI` allow-list already exercised for follower
count in task 42, now for tweet count too), copylint-clean, sealed to a
real (scratch, in these tests) ledger before its outcome is knowable.
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

from oracle_engine import copylint, prediction, tweet_cadence  # noqa: E402

_NOW = datetime.datetime(2026, 7, 20, 12, 0, tzinfo=datetime.timezone.utc)


def _fresh_ledger_module(tmp_path: str):
    mod = prediction.load_ledger_module(_TOOLS_DIR)
    mod.LEDGER = tmp_path
    return mod


class TestFetchTweetCount(unittest.TestCase):
    def test_reads_tweet_count_off_the_injected_getter(self):
        def fake_get():
            return {"public_metrics": {"tweet_count": 21}}

        self.assertEqual(tweet_cadence.fetch_tweet_count(x_whoami_get=fake_get), 21)

    def test_rejects_a_malformed_response(self):
        with self.assertRaises(tweet_cadence.TweetCadenceError):
            tweet_cadence.fetch_tweet_count(x_whoami_get=lambda: {"nope": True})

    def test_rejects_a_response_missing_tweet_count(self):
        with self.assertRaises(tweet_cadence.TweetCadenceError):
            tweet_cadence.fetch_tweet_count(
                x_whoami_get=lambda: {"public_metrics": {"followers_count": 0}}
            )

    def test_the_default_getter_raises_rather_than_guessing(self):
        with self.assertRaises(NotImplementedError):
            tweet_cadence.fetch_tweet_count()


class TestSnapshots(unittest.TestCase):
    def test_load_snapshots_of_a_missing_file_is_empty(self):
        self.assertEqual(tweet_cadence.load_snapshots("/does/not/exist.jsonl"), [])

    def test_record_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snapshots.jsonl")
            tweet_cadence.record_snapshot(21, "2026-07-13T00:00:00+00:00", path=path)
            tweet_cadence.record_snapshot(23, "2026-07-14T00:00:00+00:00", path=path)
            snaps = tweet_cadence.load_snapshots(path)
            self.assertEqual([s["count"] for s in snaps], [21, 23])

    def test_record_rejects_a_negative_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snapshots.jsonl")
            with self.assertRaises(tweet_cadence.TweetCadenceError):
                tweet_cadence.record_snapshot(-1, "2026-07-13T00:00:00+00:00", path=path)

    def test_never_rewrites_a_prior_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snapshots.jsonl")
            tweet_cadence.record_snapshot(1, "2026-07-13T00:00:00+00:00", path=path)
            with open(path) as f:
                first_write = f.read()
            tweet_cadence.record_snapshot(2, "2026-07-14T00:00:00+00:00", path=path)
            with open(path) as f:
                second_write = f.read()
            self.assertTrue(second_write.startswith(first_write))


class TestTweetCountAtOrBefore(unittest.TestCase):
    def test_returns_none_with_no_early_enough_snapshot(self):
        snaps = [{"ts": "2026-07-14T00:00:00+00:00", "count": 5}]
        when = datetime.datetime(2026, 7, 13, tzinfo=datetime.timezone.utc)
        self.assertIsNone(tweet_cadence.tweet_count_at_or_before(snaps, when))

    def test_returns_the_latest_at_or_before(self):
        snaps = [
            {"ts": "2026-07-11T00:00:00+00:00", "count": 18},
            {"ts": "2026-07-12T00:00:00+00:00", "count": 20},
            {"ts": "2026-07-14T00:00:00+00:00", "count": 25},
        ]
        when = datetime.datetime(2026, 7, 13, tzinfo=datetime.timezone.utc)
        self.assertEqual(tweet_cadence.tweet_count_at_or_before(snaps, when), 20)


class TestTweetCountAtOrAfter(unittest.TestCase):
    def test_returns_none_with_no_late_enough_snapshot(self):
        snaps = [{"ts": "2026-07-11T00:00:00+00:00", "count": 18}]
        when = datetime.datetime(2026, 7, 13, tzinfo=datetime.timezone.utc)
        self.assertIsNone(tweet_cadence.tweet_count_at_or_after(snaps, when))

    def test_returns_the_earliest_at_or_after(self):
        snaps = [
            {"ts": "2026-07-11T00:00:00+00:00", "count": 18},
            {"ts": "2026-07-14T00:00:00+00:00", "count": 25},
            {"ts": "2026-07-16T00:00:00+00:00", "count": 27},
        ]
        when = datetime.datetime(2026, 7, 13, tzinfo=datetime.timezone.utc)
        self.assertEqual(tweet_cadence.tweet_count_at_or_after(snaps, when), 25)


class TestBuildPrediction(unittest.TestCase):
    def test_claim_names_the_threshold_and_target(self):
        payload = tweet_cadence.build_prediction(_NOW, [], current_count=21, horizon_hours=168)
        self.assertIn("22", payload["claim"])
        self.assertIn("2026-07-27T12:00:00Z", payload["claim"])
        self.assertEqual(payload["confidence"], tweet_cadence.DEFAULT_CONFIDENCE)

    def test_no_baseline_snapshot_says_so_honestly(self):
        payload = tweet_cadence.build_prediction(_NOW, [], current_count=21, horizon_hours=168)
        self.assertIn("no earlier snapshot yet", payload["claim"])

    def test_a_baseline_snapshot_names_the_real_delta(self):
        baseline_when = _NOW - datetime.timedelta(hours=168)
        snaps = [{"ts": baseline_when.isoformat(), "count": 19}]
        payload = tweet_cadence.build_prediction(_NOW, snaps, current_count=21, horizon_hours=168)
        self.assertIn("+2", payload["claim"])

    def test_claim_clears_copylint(self):
        payload = tweet_cadence.build_prediction(_NOW, [], current_count=21)
        result = copylint.enforce_copy(payload["claim"], payload["confidence"])
        self.assertTrue(result.ok)

    def test_rejects_naive_datetime(self):
        with self.assertRaises(tweet_cadence.TweetCadenceError):
            tweet_cadence.build_prediction(
                datetime.datetime(2026, 7, 20, 12, 0), [], current_count=21
            )

    def test_rejects_a_negative_count(self):
        with self.assertRaises(tweet_cadence.TweetCadenceError):
            tweet_cadence.build_prediction(_NOW, [], current_count=-1)

    def test_rejects_zero_horizon_hours(self):
        # A zero horizon puts the claim's own target at the exact sealing
        # moment -- no "then" at all, already knowable the instant it would
        # be sealed.
        with self.assertRaises(tweet_cadence.TweetCadenceError):
            tweet_cadence.build_prediction(_NOW, [], current_count=1, horizon_hours=0)

    def test_rejects_negative_horizon_hours(self):
        # A negative horizon puts the claim's own target BEFORE the sealing
        # moment -- hindsight wearing a prediction's clothes.
        with self.assertRaises(tweet_cadence.TweetCadenceError):
            tweet_cadence.build_prediction(_NOW, [], current_count=1, horizon_hours=-24)

    def test_non_utc_aware_now_still_targets_the_true_utc_instant(self):
        non_utc_now = _NOW.astimezone(datetime.timezone(datetime.timedelta(hours=-5)))
        payload = tweet_cadence.build_prediction(non_utc_now, [], current_count=21, horizon_hours=168)
        self.assertIn("2026-07-27T12:00:00Z", payload["claim"])

    def test_utc_now_unaffected_by_the_normalization(self):
        payload = tweet_cadence.build_prediction(_NOW, [], current_count=21, horizon_hours=168)
        self.assertIn("2026-07-27T12:00:00Z", payload["claim"])


class TestSealTweetPrediction(unittest.TestCase):
    def test_seals_a_real_predict_entry_to_a_scratch_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = os.path.join(tmp, "ledger.jsonl")
            mod = _fresh_ledger_module(ledger_path)
            entry = tweet_cadence.seal_tweet_prediction(
                now=_NOW,
                ts=_NOW.isoformat(timespec="seconds"),
                current_count=21,
                snapshots=[],
                ledger_module=mod,
            )
            self.assertEqual(entry["act"], prediction.PREDICTION_ACT)
            self.assertEqual(entry["actor"], "kwaku-ananse")
            self.assertTrue(mod.verify())

    def test_a_tampered_sealed_tweet_prediction_breaks_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = os.path.join(tmp, "ledger.jsonl")
            mod = _fresh_ledger_module(ledger_path)
            tweet_cadence.seal_tweet_prediction(
                now=_NOW,
                ts=_NOW.isoformat(timespec="seconds"),
                current_count=21,
                snapshots=[],
                ledger_module=mod,
            )
            with open(ledger_path) as f:
                lines = f.readlines()
            import json as _json

            tampered = _json.loads(lines[0])
            tampered["detail"] = tampered["detail"].replace("22", "999")
            with open(ledger_path, "w") as f:
                f.write(_json.dumps(tampered) + "\n")
            self.assertFalse(mod.verify())


if __name__ == "__main__":
    unittest.main()
