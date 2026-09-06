"""Task 1294. Proves tools/ranking_replay_check.py's replay actually bites
on a synthetic sealed-snapshot/law mismatch, stays clean when a snapshot's
recorded label/rank/lead genuinely matches what `ranking.rank()` produces
from its own recorded candidates, and confirms the live, current checkout's
54 real sealed `fencepost/candidates/*.json` snapshots hold zero mismatches
today.
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


rrc = _load("ranking_replay_check", os.path.join(ROOT, "tools", "ranking_replay_check.py"))


def _write_snapshot(path, primary_gap, tail, confidence_bar=0.70, separation_margin=0.15):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "confidence_bar": confidence_bar,
                "separation_margin": separation_margin,
                "primary_gap": primary_gap,
                "tail": tail,
            },
            f,
        )


def _gap(slug, confidence, label, rank, lead):
    return {
        "slug": slug,
        "headline": f"headline for {slug}",
        "detail": f"detail for {slug}",
        "confidence": confidence,
        "evidence": [],
        "label": label,
        "rank": rank,
        "lead": lead,
    }


class FixtureCase(unittest.TestCase):
    def setUp(self):
        self.candidates_dir = tempfile.mkdtemp()
        self.addCleanup(self._rm)

    def _rm(self):
        import shutil
        shutil.rmtree(self.candidates_dir, ignore_errors=True)

    def _path(self, name):
        return os.path.join(self.candidates_dir, name)

    def test_agreeing_snapshot_is_clean(self):
        # The last-ranked entry's own `lead` is its confidence minus 0.0
        # (nothing ranks below it) -- 0.55, not 0.0.
        primary = _gap("milestone-unannounced", 0.85, "primary", 1, 0.3)
        tail = [_gap("coincidence-automatic", 0.55, "coincidence", 2, 0.55)]
        _write_snapshot(self._path("2026-09-06.json"), primary, tail)
        result = rrc.find_mismatches(candidates_dir=self.candidates_dir)
        self.assertEqual(result, [])

    def test_wrong_recorded_label_is_a_mismatch(self):
        # Confidence 0.85 vs 0.55 clears both the bar (0.70) and the margin
        # (0.15) -- the real law elects this PRIMARY. Recording it as a
        # CONTENDER is exactly the drift this check exists to catch.
        primary = _gap("milestone-unannounced", 0.85, "contender", 1, 0.3)
        tail = [_gap("coincidence-automatic", 0.55, "coincidence", 2, 0.55)]
        _write_snapshot(self._path("2026-09-07.json"), primary, tail)
        result = rrc.find_mismatches(candidates_dir=self.candidates_dir)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["slug"], "milestone-unannounced")
        self.assertEqual(result[0]["recorded"]["label"], "contender")
        self.assertEqual(result[0]["replayed"]["label"], "primary")

    def test_wrong_recorded_lead_is_a_mismatch(self):
        primary = _gap("milestone-unannounced", 0.85, "primary", 1, 0.99)
        tail = [_gap("coincidence-automatic", 0.55, "coincidence", 2, 0.55)]
        _write_snapshot(self._path("2026-09-08.json"), primary, tail)
        result = rrc.find_mismatches(candidates_dir=self.candidates_dir)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["recorded"]["lead"], 0.99)
        self.assertEqual(result[0]["replayed"]["lead"], 0.3)

    def test_no_primary_gap_day_replays_clean(self):
        # A real historical shape (2026-07-15/16/17): nothing cleared the
        # law that day, so `primary_gap` is null and only the tail exists.
        # The last-ranked entry's `lead` is its own confidence minus 0.0.
        tail = [
            _gap("coincidence-a", 0.6, "coincidence", 1, 0.05),
            _gap("coincidence-b", 0.55, "coincidence", 2, 0.55),
        ]
        _write_snapshot(self._path("2026-07-15.json"), None, tail)
        result = rrc.find_mismatches(candidates_dir=self.candidates_dir)
        self.assertEqual(result, [])

    def test_github_events_cache_file_is_skipped(self):
        # Not a scan result -- github_events_cache.py's own incremental
        # cache, a bare list of events, would crash the replay if read as
        # a snapshot. Confirm it is never even opened.
        path = self._path("github-events-cache.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("[]")
        result = rrc.find_mismatches(candidates_dir=self.candidates_dir)
        self.assertEqual(result, [])

    def test_format_mismatches_clean(self):
        self.assertIn("clean", rrc.format_mismatches([], count=3))

    def test_format_mismatches_dirty(self):
        primary = _gap("x", 0.9, "contender", 1, 0.5)
        _write_snapshot(self._path("2026-09-09.json"), primary, [])
        result = rrc.find_mismatches(candidates_dir=self.candidates_dir)
        out = rrc.format_mismatches(result)
        self.assertIn("MISMATCH", out)
        self.assertIn("2026-09-09.json", out)


class LiveCheckoutCase(unittest.TestCase):
    def test_live_checkout_candidates_replay_clean(self):
        result = rrc.find_mismatches()
        self.assertEqual(result, [], f"live ranking replay mismatches: {result}")


if __name__ == "__main__":
    unittest.main()
