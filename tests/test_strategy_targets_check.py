#!/usr/bin/env python3
"""Task 159. Proves tools/strategy_targets_check.py really reads STRATEGY.md's
own live text (never a hand-typed copy of the number), really cross-checks it
against the two real modules that claim to mirror it, and really would have
caught either side drifting.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


stc = _load("strategy_targets_check", os.path.join(ROOT, "tools", "strategy_targets_check.py"))


class SyntheticExtractionCase(unittest.TestCase):
    """Structural extraction, proven on synthetic fixture text so the real
    file's real numbers can't be coincidentally passing this by accident --
    the same discipline `test_cadence_target_mirror_doctrine.py`'s printed-
    line tests already hold against a fixture rather than the live file."""

    def test_extracts_report_streak_target_from_synthetic_row(self):
        text = "| Daily Fencepost Report shipped (town dogfood) | leading | 1/day, 45 of 45 days | off-by-one |\n"
        self.assertEqual(stc.strategy_report_streak_target(text), 45)

    def test_extracts_shared_reports_target_from_synthetic_row(self):
        text = "| Shared Fencepost Reports in the wild | lagging | 77 organic links/screenshots | kwaku-ananse |\n"
        self.assertEqual(stc.strategy_shared_reports_target(text), 77)

    def test_missing_report_streak_row_raises(self):
        text = "| Some other row | leading | 1/day, 30 of 30 days | off-by-one |\n"
        with self.assertRaises(stc.StrategyTargetError):
            stc.strategy_report_streak_target(text)

    def test_missing_shared_reports_row_raises(self):
        text = "| Some other row | lagging | 50 organic links/screenshots | kwaku-ananse |\n"
        with self.assertRaises(stc.StrategyTargetError):
            stc.strategy_shared_reports_target(text)

    def test_report_streak_row_present_but_malformed_target_raises(self):
        text = "| Daily Fencepost Report shipped (town dogfood) | leading | thirty of thirty days | off-by-one |\n"
        with self.assertRaises(stc.StrategyTargetError):
            stc.strategy_report_streak_target(text)

    def test_shared_reports_row_present_but_malformed_target_raises(self):
        text = "| Shared Fencepost Reports in the wild | lagging | a lot of screenshots | kwaku-ananse |\n"
        with self.assertRaises(stc.StrategyTargetError):
            stc.strategy_shared_reports_target(text)

    def test_extracts_github_stars_target_from_synthetic_row(self):
        text = "| GitHub stars | lagging | 2,500 (Star Covenant, unbegged) | off-by-one |\n"
        self.assertEqual(stc.strategy_github_stars_target(text), 2500)

    def test_extracts_github_stars_target_without_comma(self):
        text = "| GitHub stars | lagging | 999 (Star Covenant, unbegged) | off-by-one |\n"
        self.assertEqual(stc.strategy_github_stars_target(text), 999)

    def test_missing_github_stars_row_raises(self):
        text = "| Some other row | lagging | 1,000 (Star Covenant, unbegged) | off-by-one |\n"
        with self.assertRaises(stc.StrategyTargetError):
            stc.strategy_github_stars_target(text)

    def test_github_stars_row_present_but_malformed_target_raises(self):
        text = "| GitHub stars | lagging | a thousand, unbegged | off-by-one |\n"
        with self.assertRaises(stc.StrategyTargetError):
            stc.strategy_github_stars_target(text)


class RealStrategyMdCase(unittest.TestCase):
    """The real point: STRATEGY.md's own live text, read from disk, not a
    fixture standing in for it."""

    def setUp(self):
        with open(stc.STRATEGY_MD, encoding="utf-8") as f:
            self.text = f.read()

    def test_real_report_streak_target_is_thirty(self):
        # Regression pin: today's real STRATEGY.md target. If a future
        # decree revises this row, this pin breaks loudly and gets updated
        # deliberately -- never silently, same as every other pin this
        # town's own audits carry.
        self.assertEqual(stc.strategy_report_streak_target(self.text), 30)

    def test_real_shared_reports_target_is_fifty(self):
        self.assertEqual(stc.strategy_shared_reports_target(self.text), 50)

    def test_real_github_stars_target_is_a_thousand(self):
        self.assertEqual(stc.strategy_github_stars_target(self.text), 1000)


class RealCrossCheckCase(unittest.TestCase):
    """`check_strategy_targets()` against the real repo: today, both real
    modules' real constants agree with STRATEGY.md's real text."""

    def test_real_check_reports_agreement_on_both_rows(self):
        result = stc.check_strategy_targets()
        self.assertTrue(result["report_streak"]["agree"])
        self.assertEqual(result["report_streak"]["strategy_target"], 30)
        self.assertEqual(result["report_streak"]["code_target"], 30)
        self.assertTrue(result["shared_reports"]["agree"])
        self.assertEqual(result["shared_reports"]["strategy_target"], 50)
        self.assertEqual(result["shared_reports"]["code_target"], 50)
        self.assertTrue(result["github_stars"]["agree"])
        self.assertEqual(result["github_stars"]["strategy_target"], 1000)
        self.assertEqual(result["github_stars"]["code_target"], 1000)

    def test_real_code_targets_are_live_loaded_not_hand_typed(self):
        # Cross-check against a SECOND, independent live import of the
        # real modules -- proves check_strategy_targets() is really reading
        # their real constants, not a copy pasted into this test file.
        rcc = _load("_t159_rcc_indep", os.path.join(ROOT, "tools", "report_cadence_check.py"))
        src = _load("_t159_src_indep", os.path.join(ROOT, "tools", "shared_reports_check.py"))
        ghs = _load("_t159_ghs_indep", os.path.join(ROOT, "tools", "github_stars_check.py"))
        result = stc.check_strategy_targets()
        self.assertEqual(result["report_streak"]["code_target"], rcc.TARGET_STREAK_DAYS)
        self.assertEqual(result["shared_reports"]["code_target"], src.TARGET_SHARES)
        self.assertEqual(result["github_stars"]["code_target"], ghs.TARGET_STARS)

    def test_format_names_all_three_rows_and_agreement(self):
        result = stc.check_strategy_targets()
        formatted = stc.format_strategy_targets(result)
        self.assertIn("report cadence", formatted)
        self.assertIn("shared reports", formatted)
        self.assertIn("github stars", formatted)
        self.assertIn("STRATEGY.md=30", formatted)
        self.assertIn("code=30", formatted)
        self.assertIn("STRATEGY.md=50", formatted)
        self.assertIn("code=50", formatted)
        self.assertIn("STRATEGY.md=1000", formatted)
        self.assertIn("code=1000", formatted)
        self.assertNotIn("DRIFT", formatted)


class MutationCase(unittest.TestCase):
    """Reconstructs the exact failure mode neither existing test file could
    catch: STRATEGY.md's target moves, or the code constant moves, and the
    other side doesn't follow. Proves this check would have caught each."""

    def test_mutation_a_drifted_strategy_row_disagrees_with_the_real_code_constant(self):
        with open(stc.STRATEGY_MD, encoding="utf-8") as f:
            real_text = f.read()
        # A real STRATEGY.md row, mutated to a plausible future decree
        # (60 of 60 days instead of 30 of 30) -- the exact shape a future
        # metrics revision could ship without anyone updating the code side.
        drifted_text = real_text.replace("1/day, 30 of 30 days", "1/day, 60 of 60 days")
        self.assertNotEqual(drifted_text, real_text, "fixture setup: the real row text must actually match first")

        rcc = _load("_t159_rcc_mut1", os.path.join(ROOT, "tools", "report_cadence_check.py"))
        drifted_target = stc.strategy_report_streak_target(drifted_text)
        self.assertNotEqual(drifted_target, rcc.TARGET_STREAK_DAYS)

    def test_mutation_a_drifted_code_constant_disagrees_with_the_real_strategy_row(self):
        rcc = _load("_t159_rcc_mut2", os.path.join(ROOT, "tools", "report_cadence_check.py"))
        rcc.TARGET_STREAK_DAYS = rcc.TARGET_STREAK_DAYS + 15  # mutate a loaded copy only, never the file on disk
        with open(stc.STRATEGY_MD, encoding="utf-8") as f:
            real_text = f.read()
        real_strategy_target = stc.strategy_report_streak_target(real_text)
        self.assertNotEqual(real_strategy_target, rcc.TARGET_STREAK_DAYS)

    def test_mutation_a_drifted_shared_reports_row_disagrees_with_the_real_code_constant(self):
        with open(stc.STRATEGY_MD, encoding="utf-8") as f:
            real_text = f.read()
        drifted_text = real_text.replace("50 organic links/screenshots", "100 organic links/screenshots")
        self.assertNotEqual(drifted_text, real_text, "fixture setup: the real row text must actually match first")

        src = _load("_t159_src_mut1", os.path.join(ROOT, "tools", "shared_reports_check.py"))
        drifted_target = stc.strategy_shared_reports_target(drifted_text)
        self.assertNotEqual(drifted_target, src.TARGET_SHARES)

    def test_mutation_a_drifted_github_stars_row_disagrees_with_the_real_code_constant(self):
        with open(stc.STRATEGY_MD, encoding="utf-8") as f:
            real_text = f.read()
        drifted_text = real_text.replace(
            "1,000 (Star Covenant, unbegged)", "5,000 (Star Covenant, unbegged)"
        )
        self.assertNotEqual(drifted_text, real_text, "fixture setup: the real row text must actually match first")

        ghs = _load("_t421_ghs_mut1", os.path.join(ROOT, "tools", "github_stars_check.py"))
        drifted_target = stc.strategy_github_stars_target(drifted_text)
        self.assertNotEqual(drifted_target, ghs.TARGET_STARS)

    def test_mutation_a_drifted_code_constant_disagrees_with_the_real_github_stars_row(self):
        ghs = _load("_t421_ghs_mut2", os.path.join(ROOT, "tools", "github_stars_check.py"))
        ghs.TARGET_STARS = ghs.TARGET_STARS + 500  # mutate a loaded copy only, never the file on disk
        with open(stc.STRATEGY_MD, encoding="utf-8") as f:
            real_text = f.read()
        real_strategy_target = stc.strategy_github_stars_target(real_text)
        self.assertNotEqual(real_strategy_target, ghs.TARGET_STARS)


if __name__ == "__main__":
    unittest.main()
