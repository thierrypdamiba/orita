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

    def test_extracts_connected_users_target_from_synthetic_row(self):
        text = "| \"Connect your own\" OAuth completions across users | leading | 250 connected users in 60 days | kothar-wa-khasis |\n"
        self.assertEqual(stc.strategy_connected_users_target(text), 250)

    def test_missing_connected_users_row_raises(self):
        text = "| Some other row | leading | 100 connected users in 60 days | kothar-wa-khasis |\n"
        with self.assertRaises(stc.StrategyTargetError):
            stc.strategy_connected_users_target(text)

    def test_connected_users_row_present_but_malformed_target_raises(self):
        text = "| \"Connect your own\" OAuth completions across users | leading | a hundred users | kothar-wa-khasis |\n"
        with self.assertRaises(stc.StrategyTargetError):
            stc.strategy_connected_users_target(text)

    def test_extracts_toolkits_target_from_synthetic_row(self):
        text = "| Distinct read-only toolkits connected across users (Arcade breadth) | leading | >=9 toolkits in real use | nisaba |\n"
        self.assertEqual(stc.strategy_toolkits_target(text), 9)

    def test_missing_toolkits_row_raises(self):
        text = "| Some other row | leading | >=5 toolkits in real use | nisaba |\n"
        with self.assertRaises(stc.StrategyTargetError):
            stc.strategy_toolkits_target(text)

    def test_toolkits_row_present_but_malformed_target_raises(self):
        text = "| Distinct read-only toolkits connected across users (Arcade breadth) | leading | several toolkits | nisaba |\n"
        with self.assertRaises(stc.StrategyTargetError):
            stc.strategy_toolkits_target(text)


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

    def test_real_connected_users_target_is_a_hundred(self):
        self.assertEqual(stc.strategy_connected_users_target(self.text), 100)

    def test_real_toolkits_target_is_five(self):
        self.assertEqual(stc.strategy_toolkits_target(self.text), 5)


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
        self.assertTrue(result["connected_users"]["agree"])
        self.assertEqual(result["connected_users"]["strategy_target"], 100)
        self.assertEqual(result["connected_users"]["code_target"], 100)
        self.assertTrue(result["toolkits"]["agree"])
        self.assertEqual(result["toolkits"]["strategy_target"], 5)
        self.assertEqual(result["toolkits"]["code_target"], 5)

    def test_real_code_targets_are_live_loaded_not_hand_typed(self):
        # Cross-check against a SECOND, independent live import of the
        # real modules -- proves check_strategy_targets() is really reading
        # their real constants, not a copy pasted into this test file.
        rcc = _load("_t159_rcc_indep", os.path.join(ROOT, "tools", "report_cadence_check.py"))
        src = _load("_t159_src_indep", os.path.join(ROOT, "tools", "shared_reports_check.py"))
        ghs = _load("_t159_ghs_indep", os.path.join(ROOT, "tools", "github_stars_check.py"))
        cuc = _load("_t428_cuc_indep", os.path.join(ROOT, "tools", "connected_users_check.py"))
        tiu = _load("_t428_tiu_indep", os.path.join(ROOT, "tools", "toolkits_in_use_check.py"))
        result = stc.check_strategy_targets()
        self.assertEqual(result["report_streak"]["code_target"], rcc.TARGET_STREAK_DAYS)
        self.assertEqual(result["shared_reports"]["code_target"], src.TARGET_SHARES)
        self.assertEqual(result["github_stars"]["code_target"], ghs.TARGET_STARS)
        self.assertEqual(result["connected_users"]["code_target"], cuc.TARGET_CONNECTED_USERS)
        self.assertEqual(result["toolkits"]["code_target"], tiu.TARGET_TOOLKITS)

    def test_format_names_all_five_rows_and_agreement(self):
        result = stc.check_strategy_targets()
        formatted = stc.format_strategy_targets(result)
        self.assertIn("report cadence", formatted)
        self.assertIn("shared reports", formatted)
        self.assertIn("github stars", formatted)
        self.assertIn("connected users", formatted)
        self.assertIn("toolkits", formatted)
        self.assertIn("STRATEGY.md=30", formatted)
        self.assertIn("code=30", formatted)
        self.assertIn("STRATEGY.md=50", formatted)
        self.assertIn("code=50", formatted)
        self.assertIn("STRATEGY.md=1000", formatted)
        self.assertIn("code=1000", formatted)
        self.assertIn("STRATEGY.md=100", formatted)
        self.assertIn("code=100", formatted)
        self.assertIn("STRATEGY.md=5", formatted)
        self.assertIn("code=5", formatted)
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

    def test_mutation_a_drifted_connected_users_row_disagrees_with_the_real_code_constant(self):
        with open(stc.STRATEGY_MD, encoding="utf-8") as f:
            real_text = f.read()
        drifted_text = real_text.replace(
            "100 connected users in 60 days", "300 connected users in 60 days"
        )
        self.assertNotEqual(drifted_text, real_text, "fixture setup: the real row text must actually match first")

        cuc = _load("_t428_cuc_mut1", os.path.join(ROOT, "tools", "connected_users_check.py"))
        drifted_target = stc.strategy_connected_users_target(drifted_text)
        self.assertNotEqual(drifted_target, cuc.TARGET_CONNECTED_USERS)

    def test_mutation_a_drifted_code_constant_disagrees_with_the_real_connected_users_row(self):
        cuc = _load("_t428_cuc_mut2", os.path.join(ROOT, "tools", "connected_users_check.py"))
        cuc.TARGET_CONNECTED_USERS = cuc.TARGET_CONNECTED_USERS + 50  # mutate a loaded copy only
        with open(stc.STRATEGY_MD, encoding="utf-8") as f:
            real_text = f.read()
        real_strategy_target = stc.strategy_connected_users_target(real_text)
        self.assertNotEqual(real_strategy_target, cuc.TARGET_CONNECTED_USERS)

    def test_mutation_a_drifted_toolkits_row_disagrees_with_the_real_code_constant(self):
        with open(stc.STRATEGY_MD, encoding="utf-8") as f:
            real_text = f.read()
        drifted_text = real_text.replace(">=5 toolkits in real use", ">=8 toolkits in real use")
        self.assertNotEqual(drifted_text, real_text, "fixture setup: the real row text must actually match first")

        tiu = _load("_t428_tiu_mut1", os.path.join(ROOT, "tools", "toolkits_in_use_check.py"))
        drifted_target = stc.strategy_toolkits_target(drifted_text)
        self.assertNotEqual(drifted_target, tiu.TARGET_TOOLKITS)

    def test_mutation_a_drifted_code_constant_disagrees_with_the_real_toolkits_row(self):
        tiu = _load("_t428_tiu_mut2", os.path.join(ROOT, "tools", "toolkits_in_use_check.py"))
        tiu.TARGET_TOOLKITS = tiu.TARGET_TOOLKITS + 3  # mutate a loaded copy only, never the file on disk
        with open(stc.STRATEGY_MD, encoding="utf-8") as f:
            real_text = f.read()
        real_strategy_target = stc.strategy_toolkits_target(real_text)
        self.assertNotEqual(real_strategy_target, tiu.TARGET_TOOLKITS)


class LoadHelperCase(unittest.TestCase):
    """Task 624. strategy_targets_check.py's own `_load()` -- the loader
    `check_strategy_targets()` uses to live-load the two real modules it
    cross-checks STRATEGY.md against -- called
    `importlib.util.module_from_spec(spec)` / `spec.loader.exec_module(...)`
    unconditionally, the same shape task 621 already fixed in
    ritual_check.py's own `_load()`. `spec_from_file_location` returns
    `None` (not a `ModuleSpec`) whenever the target path's extension has no
    registered loader, and every current call site here hands `_load()` a
    real `.py` relpath so the gap never fires today -- but it is a real,
    reachable path for a future caller passing a typo'd or non-`.py`
    relpath, not a hypothetical."""

    def test_load_raises_named_error_for_unloadable_path(self):
        with self.assertRaises(ImportError) as ctx:
            stc._load("_test_load_helper_bogus", "README.md")
        self.assertIn("_test_load_helper_bogus", str(ctx.exception))
        self.assertIn("README.md", str(ctx.exception))

    def test_load_still_loads_a_real_module(self):
        mod = stc._load("_test_load_helper_real", "tools/word_watch.py")
        self.assertTrue(hasattr(mod, "LOG"))


if __name__ == "__main__":
    unittest.main()
