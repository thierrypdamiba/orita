"""Task 38. The Oracle Desk's second real cadence: one checkable claim
about the town's own public GitHub stargazer count, sourced with no
Arcade scope at all (a repo's star count is public data), copylint-clean,
sealed to a real (scratch, in these tests) ledger before its outcome is
knowable.
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

from oracle_engine import copylint, prediction, star_cadence  # noqa: E402

_NOW = datetime.datetime(2026, 7, 20, 12, 0, tzinfo=datetime.timezone.utc)


def _fresh_ledger_module(tmp_path: str):
    mod = prediction.load_ledger_module(_TOOLS_DIR)
    mod.LEDGER = tmp_path
    return mod


class TestFetchStarCount(unittest.TestCase):
    def test_reads_stargazers_count_off_the_injected_getter(self):
        def fake_get(url):
            self.assertEqual(url, "https://api.github.com/repos/thierrypdamiba/orita")
            return {"stargazers_count": 7}

        self.assertEqual(star_cadence.fetch_star_count(http_get=fake_get), 7)

    def test_rejects_a_malformed_response(self):
        with self.assertRaises(star_cadence.StarCadenceError):
            star_cadence.fetch_star_count(http_get=lambda url: {"nope": True})


class TestSnapshots(unittest.TestCase):
    def test_load_snapshots_of_a_missing_file_is_empty(self):
        self.assertEqual(star_cadence.load_snapshots("/does/not/exist.jsonl"), [])

    def test_record_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snapshots.jsonl")
            star_cadence.record_snapshot(3, "2026-07-13T00:00:00+00:00", path=path)
            star_cadence.record_snapshot(5, "2026-07-14T00:00:00+00:00", path=path)
            snaps = star_cadence.load_snapshots(path)
            self.assertEqual([s["count"] for s in snaps], [3, 5])

    def test_record_rejects_a_negative_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snapshots.jsonl")
            with self.assertRaises(star_cadence.StarCadenceError):
                star_cadence.record_snapshot(-1, "2026-07-13T00:00:00+00:00", path=path)

    def test_never_rewrites_a_prior_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snapshots.jsonl")
            star_cadence.record_snapshot(1, "2026-07-13T00:00:00+00:00", path=path)
            with open(path) as f:
                first_write = f.read()
            star_cadence.record_snapshot(2, "2026-07-14T00:00:00+00:00", path=path)
            with open(path) as f:
                second_write = f.read()
            self.assertTrue(second_write.startswith(first_write))

    def test_load_snapshots_marks_a_malformed_line_instead_of_raising(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snapshots.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                f.write('{"ts": "2026-07-13T00:00:00+00:00", "count": 4}\n')
                f.write("not valid json at all\n")
            snaps = star_cadence.load_snapshots(path)
            self.assertEqual(len(snaps), 2)
            self.assertEqual(snaps[0]["count"], 4)
            self.assertTrue(snaps[1]["_malformed"])
            self.assertIn("_error", snaps[1])

    def test_load_snapshots_marks_a_valid_json_non_dict_line_as_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snapshots.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                f.write('{"ts": "2026-07-13T00:00:00+00:00", "count": 4}\n')
                f.write("5\n")
            snaps = star_cadence.load_snapshots(path)
            self.assertEqual(len(snaps), 2)
            self.assertEqual(snaps[0]["count"], 4)
            self.assertTrue(snaps[1]["_malformed"])
            self.assertEqual(snaps[1]["_error"], "not a JSON object")

    def test_a_valid_json_non_dict_snapshot_line_refuses_not_crashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snapshots.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                f.write('{"ts": "2026-07-13T00:00:00+00:00", "count": 4}\n')
                f.write("5\n")
            snaps = star_cadence.load_snapshots(path)
            when = datetime.datetime(2026, 7, 14, tzinfo=datetime.timezone.utc)
            with self.assertRaises(star_cadence.StarCadenceTamperedError):
                star_cadence.star_count_at_or_before(snaps, when)


class TestStarCountAtOrBefore(unittest.TestCase):
    def test_returns_none_with_no_early_enough_snapshot(self):
        snaps = [{"ts": "2026-07-14T00:00:00+00:00", "count": 5}]
        when = datetime.datetime(2026, 7, 13, tzinfo=datetime.timezone.utc)
        self.assertIsNone(star_cadence.star_count_at_or_before(snaps, when))

    def test_returns_the_latest_at_or_before(self):
        snaps = [
            {"ts": "2026-07-11T00:00:00+00:00", "count": 1},
            {"ts": "2026-07-12T00:00:00+00:00", "count": 3},
            {"ts": "2026-07-14T00:00:00+00:00", "count": 9},
        ]
        when = datetime.datetime(2026, 7, 13, tzinfo=datetime.timezone.utc)
        self.assertEqual(star_cadence.star_count_at_or_before(snaps, when), 3)

    def test_raises_tampered_error_on_a_malformed_line_instead_of_crashing(self):
        snaps = [
            {"ts": "2026-07-11T00:00:00+00:00", "count": 1},
            {"_malformed": True, "_error": "Expecting value: line 1 column 1 (char 0)"},
        ]
        when = datetime.datetime(2026, 7, 13, tzinfo=datetime.timezone.utc)
        with self.assertRaises(star_cadence.StarCadenceTamperedError):
            star_cadence.star_count_at_or_before(snaps, when)


class TestStarCountAtOrAfter(unittest.TestCase):
    def test_returns_none_with_no_late_enough_snapshot(self):
        snaps = [{"ts": "2026-07-11T00:00:00+00:00", "count": 1}]
        when = datetime.datetime(2026, 7, 13, tzinfo=datetime.timezone.utc)
        self.assertIsNone(star_cadence.star_count_at_or_after(snaps, when))

    def test_raises_tampered_error_on_a_malformed_line_instead_of_crashing(self):
        snaps = [
            {"ts": "2026-07-11T00:00:00+00:00", "count": 1},
            {"_malformed": True, "_error": "Expecting value: line 1 column 1 (char 0)"},
        ]
        when = datetime.datetime(2026, 7, 13, tzinfo=datetime.timezone.utc)
        with self.assertRaises(star_cadence.StarCadenceTamperedError):
            star_cadence.star_count_at_or_after(snaps, when)

    def test_a_valid_lookup_after_a_malformed_earlier_line_still_refuses(self):
        # Even when the malformed line would not have been the winning
        # match, the guard refuses rather than silently trusting the rest
        # of the log -- a malformed line anywhere could be masking the
        # real closest snapshot for a different `when`.
        snaps = [
            {"_malformed": True, "_error": "boom"},
            {"ts": "2026-07-14T00:00:00+00:00", "count": 2},
        ]
        when = datetime.datetime(2026, 7, 13, tzinfo=datetime.timezone.utc)
        with self.assertRaises(star_cadence.StarCadenceTamperedError):
            star_cadence.star_count_at_or_after(snaps, when)

    def test_returns_the_earliest_at_or_after(self):
        snaps = [
            {"ts": "2026-07-11T00:00:00+00:00", "count": 1},
            {"ts": "2026-07-14T00:00:00+00:00", "count": 9},
            {"ts": "2026-07-16T00:00:00+00:00", "count": 12},
        ]
        when = datetime.datetime(2026, 7, 13, tzinfo=datetime.timezone.utc)
        self.assertEqual(star_cadence.star_count_at_or_after(snaps, when), 9)


class TestBuildPrediction(unittest.TestCase):
    def test_claim_names_the_threshold_and_target(self):
        payload = star_cadence.build_prediction(_NOW, [], current_count=4, horizon_hours=168)
        self.assertIn("5", payload["claim"])
        self.assertIn("2026-07-27T12:00:00Z", payload["claim"])
        self.assertEqual(payload["confidence"], star_cadence.DEFAULT_CONFIDENCE)

    def test_no_baseline_snapshot_says_so_honestly(self):
        payload = star_cadence.build_prediction(_NOW, [], current_count=4, horizon_hours=168)
        self.assertIn("no earlier snapshot yet", payload["claim"])

    def test_a_baseline_snapshot_names_the_real_delta(self):
        baseline_when = _NOW - datetime.timedelta(hours=168)
        snaps = [{"ts": baseline_when.isoformat(), "count": 2}]
        payload = star_cadence.build_prediction(_NOW, snaps, current_count=4, horizon_hours=168)
        self.assertIn("+2", payload["claim"])

    def test_claim_clears_copylint(self):
        payload = star_cadence.build_prediction(_NOW, [], current_count=4)
        result = copylint.enforce_copy(payload["claim"], payload["confidence"])
        self.assertTrue(result.ok)

    def test_rejects_naive_datetime(self):
        with self.assertRaises(star_cadence.StarCadenceError):
            star_cadence.build_prediction(
                datetime.datetime(2026, 7, 20, 12, 0), [], current_count=4
            )

    def test_rejects_a_negative_count(self):
        with self.assertRaises(star_cadence.StarCadenceError):
            star_cadence.build_prediction(_NOW, [], current_count=-1)

    def test_rejects_zero_horizon_hours(self):
        # A zero horizon puts the claim's own target at the exact sealing
        # moment -- no "then" at all, already knowable the instant it would
        # be sealed.
        with self.assertRaises(star_cadence.StarCadenceError):
            star_cadence.build_prediction(_NOW, [], current_count=1, horizon_hours=0)

    def test_rejects_negative_horizon_hours(self):
        # A negative horizon puts the claim's own target BEFORE the sealing
        # moment -- hindsight wearing a prediction's clothes.
        with self.assertRaises(star_cadence.StarCadenceError):
            star_cadence.build_prediction(_NOW, [], current_count=1, horizon_hours=-24)

    def test_non_utc_aware_now_still_targets_the_true_utc_instant(self):
        # `now.tzinfo is None` rejects naive datetimes, but any *other*
        # aware timezone was passing straight through into a claim string
        # that hardcodes a literal "Z" (UTC) suffix -- mislabeling the
        # target by exactly the caller's UTC offset. A non-UTC caller (a
        # server in another timezone, a manual/ad-hoc seal) must still
        # produce the same real-world target instant as the equivalent UTC
        # call, not a claim that lies about which instant it names.
        eastern = datetime.timezone(datetime.timedelta(hours=-5))
        now_eastern = _NOW.astimezone(eastern)
        payload = star_cadence.build_prediction(now_eastern, [], current_count=4, horizon_hours=168)
        self.assertIn("2026-07-27T12:00:00Z", payload["claim"])

    def test_utc_now_unaffected_by_the_normalization(self):
        # The fix must be a no-op for every already-passing UTC call site.
        payload = star_cadence.build_prediction(_NOW, [], current_count=4, horizon_hours=168)
        self.assertIn("2026-07-27T12:00:00Z", payload["claim"])


class TestSealStarPrediction(unittest.TestCase):
    def test_seals_a_real_predict_entry_to_a_scratch_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = os.path.join(tmp, "ledger.jsonl")
            mod = _fresh_ledger_module(ledger_path)
            entry = star_cadence.seal_star_prediction(
                now=_NOW,
                ts=_NOW.isoformat(timespec="seconds"),
                current_count=4,
                snapshots=[],
                ledger_module=mod,
            )
            self.assertEqual(entry["act"], prediction.PREDICTION_ACT)
            self.assertEqual(entry["actor"], "off-by-one")
            self.assertTrue(mod.verify())

    def test_a_tampered_sealed_star_prediction_breaks_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = os.path.join(tmp, "ledger.jsonl")
            mod = _fresh_ledger_module(ledger_path)
            star_cadence.seal_star_prediction(
                now=_NOW,
                ts=_NOW.isoformat(timespec="seconds"),
                current_count=4,
                snapshots=[],
                ledger_module=mod,
            )
            with open(ledger_path) as f:
                lines = f.readlines()
            import json as _json

            tampered = _json.loads(lines[0])
            tampered["detail"] = tampered["detail"].replace("5", "999")
            with open(ledger_path, "w") as f:
                f.write(_json.dumps(tampered) + "\n")
            self.assertFalse(mod.verify())


if __name__ == "__main__":
    unittest.main()
