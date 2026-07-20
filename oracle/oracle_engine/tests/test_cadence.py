"""Task 36. The Oracle Desk's first real cadence: one self-referential,
checkable prediction read off `BUILDLOG.md`'s own honest record of the
town's shipping velocity, copylint-clean, sealed to a real (scratch, in
these tests) ledger before its outcome is knowable.
"""
from __future__ import annotations

import datetime
import os
import re
import sys
import tempfile
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORACLE_ENGINE_ROOT = os.path.dirname(_TESTS_DIR)  # oracle/oracle_engine
_ORACLE_ROOT = os.path.dirname(_ORACLE_ENGINE_ROOT)  # oracle/
_ORITA_ROOT = os.path.dirname(_ORACLE_ROOT)  # repo root
_TOOLS_DIR = os.path.join(_ORITA_ROOT, "tools")

sys.path.insert(0, os.path.join(_ORACLE_ENGINE_ROOT, "src"))

from oracle_engine import cadence, copylint, prediction  # noqa: E402

_SAMPLE_LOG = """# Build Log

2026-07-13 07:10 UTC | nisaba | 31 | Prediction schema shipped
2026-07-13 07:10 UTC | nisaba | 31 | Posted task 31 to @oritatown: https://x.com/i/web/status/1
2026-07-13 08:04 UTC | ogun | 32 | Self-scoring pass shipped
2026-07-13 09:10 UTC | retrya | 33 | Non-advice-shaped copy lint shipped
2026-07-13 10:20 UTC | kothar-wa-khasis | 34 | docs/oracle/ shipped
2026-07-13 10:24 UTC | kothar-wa-khasis | 34 | Posted task 34 to @oritatown: https://x.com/i/web/status/2
2026-07-13 11:02 UTC | esu-elegba | 35 | Shipped oracle/INTENT.md
2026-07-12 23:09 UTC | nisaba | roadmap | Extended ROADMAP.md
"""

_NOW = datetime.datetime(2026, 7, 13, 11, 30, tzinfo=datetime.timezone.utc)


def _fresh_ledger_module(tmp_path: str):
    mod = prediction.load_ledger_module(_TOOLS_DIR)
    mod.LEDGER = tmp_path
    return mod


class TestParseBuildlog(unittest.TestCase):
    def test_parses_only_well_formed_lines(self):
        entries = cadence.parse_buildlog(_SAMPLE_LOG)
        # 8 log lines match the pattern; the "roadmap" line's task token is
        # non-numeric so it is parsed but not counted as a numbered task.
        self.assertEqual(len(entries), 8)

    def test_task_field_captured_verbatim(self):
        entries = cadence.parse_buildlog(_SAMPLE_LOG)
        tasks = {e["task"].strip() for e in entries}
        self.assertIn("31", tasks)
        self.assertIn("roadmap", tasks)


class TestObscuredMinuteConvention(unittest.TestCase):
    """The real BUILDLOG.md obscures many lines' exact minute with a
    literal 'x' (e.g. "19:2x UTC", "03:0x UTC") -- a real, live convention
    used throughout the file (grep confirms it), never exercised by
    `_SAMPLE_LOG` above since that fixture predates the convention. Before
    the fix this task shipped, `_LOG_LINE_RE` required `\\d{2}:\\d{2}` and
    every such line was silently dropped by `parse_buildlog` -- more than
    a third of the real file's lines, undercounting
    `recent_task_velocity` (and therefore every cadence claim and
    autograde re-derivation built on it) without raising anything."""

    _OBSCURED_LOG = (
        "2026-07-13 07:10 UTC | nisaba | 31 | Prediction schema shipped\n"
        "2026-07-13 09:2x UTC | ogun | 32 | Self-scoring pass shipped\n"
        "2026-07-13 11:0x UTC | esu-elegba | 35 | Shipped oracle/INTENT.md\n"
    )

    def test_parses_lines_with_obscured_minute(self):
        entries = cadence.parse_buildlog(self._OBSCURED_LOG)
        self.assertEqual(len(entries), 3)
        tasks = {e["task"].strip() for e in entries}
        self.assertEqual(tasks, {"31", "32", "35"})

    def test_minute_floor_replaces_trailing_x_with_zero(self):
        self.assertEqual(cadence._minute_floor("19:2x"), "19:20")
        self.assertEqual(cadence._minute_floor("03:0x"), "03:00")
        self.assertEqual(cadence._minute_floor("11:16"), "11:16")

    def test_recent_task_velocity_counts_obscured_minute_lines(self):
        entries = cadence.parse_buildlog(self._OBSCURED_LOG)
        now = datetime.datetime(2026, 7, 13, 11, 30, tzinfo=datetime.timezone.utc)
        # All three tasks (31 at 07:10, 32 at 09:2x, 35 at 11:0x) fall
        # inside the 24h window -- the pre-fix code silently dropped the
        # two obscured-minute lines and returned 1, not 3.
        velocity = cadence.recent_task_velocity(entries, now, window_hours=24)
        self.assertEqual(velocity, 3)

    def test_real_buildlog_has_no_lines_the_parser_silently_drops(self):
        """A live, read-only check against the real BUILDLOG.md: every
        line shaped like a dated entry (`YYYY-MM-DD HH:` at the start)
        must be one `_LOG_LINE_RE` actually recognizes. This is the
        regression pin against the real file the bug was found in, not
        just the synthetic fixture above."""
        with open(cadence.DEFAULT_BUILDLOG_PATH, encoding="utf-8") as f:
            raw = f.read()
        shaped = [
            line
            for line in raw.splitlines()
            if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:", line)
        ]
        parsed = cadence.parse_buildlog(raw)
        self.assertEqual(
            len(parsed),
            len(shaped),
            "parse_buildlog silently dropped a real, dated BUILDLOG.md line",
        )


class TestRecentTaskVelocity(unittest.TestCase):
    def test_counts_distinct_numbered_tasks_in_window(self):
        entries = cadence.parse_buildlog(_SAMPLE_LOG)
        # Within the 24h before _NOW: tasks 31, 32, 33, 34, 35 = 5 distinct
        # numbered tasks (task 31 and 34 each appear twice, counted once).
        velocity = cadence.recent_task_velocity(entries, _NOW, window_hours=24)
        self.assertEqual(velocity, 5)

    def test_a_tighter_window_counts_fewer(self):
        entries = cadence.parse_buildlog(_SAMPLE_LOG)
        velocity = cadence.recent_task_velocity(entries, _NOW, window_hours=1)
        self.assertEqual(velocity, 1)  # only task 35 at 11:02

    def test_rejects_naive_datetime(self):
        entries = cadence.parse_buildlog(_SAMPLE_LOG)
        with self.assertRaises(cadence.CadenceError):
            cadence.recent_task_velocity(entries, datetime.datetime(2026, 7, 13, 11, 30))


class TestBuildPrediction(unittest.TestCase):
    def test_claim_names_the_threshold_and_horizon(self):
        entries = cadence.parse_buildlog(_SAMPLE_LOG)
        payload = cadence.build_prediction(_NOW, entries, threshold=3, horizon_hours=24)
        self.assertIn("3", payload["claim"])
        self.assertIn("2026-07-14T11:30:00Z", payload["claim"])
        self.assertEqual(payload["confidence"], cadence.DEFAULT_CONFIDENCE)

    def test_claim_clears_copylint(self):
        entries = cadence.parse_buildlog(_SAMPLE_LOG)
        payload = cadence.build_prediction(_NOW, entries)
        result = copylint.enforce_copy(payload["claim"], payload["confidence"])
        self.assertTrue(result.ok)

    def test_rejects_threshold_below_one(self):
        entries = cadence.parse_buildlog(_SAMPLE_LOG)
        with self.assertRaises(cadence.CadenceError):
            cadence.build_prediction(_NOW, entries, threshold=0)


class TestSealCadencePrediction(unittest.TestCase):
    def test_seals_a_real_predict_entry_to_a_scratch_ledger(self):
        entries = cadence.parse_buildlog(_SAMPLE_LOG)
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = os.path.join(tmp, "ledger.jsonl")
            mod = _fresh_ledger_module(ledger_path)
            entry = cadence.seal_cadence_prediction(
                now=_NOW,
                ts=_NOW.isoformat(timespec="seconds"),
                entries=entries,
                ledger_module=mod,
            )
            self.assertEqual(entry["act"], prediction.PREDICTION_ACT)
            self.assertEqual(entry["actor"], "off-by-one")
            self.assertTrue(mod.verify())

    def test_a_tampered_sealed_cadence_prediction_breaks_verify(self):
        entries = cadence.parse_buildlog(_SAMPLE_LOG)
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = os.path.join(tmp, "ledger.jsonl")
            mod = _fresh_ledger_module(ledger_path)
            cadence.seal_cadence_prediction(
                now=_NOW,
                ts=_NOW.isoformat(timespec="seconds"),
                entries=entries,
                ledger_module=mod,
            )
            with open(ledger_path) as f:
                lines = f.readlines()
            import json as _json

            tampered = _json.loads(lines[0])
            tampered["detail"] = tampered["detail"].replace("3", "999")
            with open(ledger_path, "w") as f:
                f.write(_json.dumps(tampered) + "\n")
            self.assertFalse(mod.verify())


if __name__ == "__main__":
    unittest.main()
