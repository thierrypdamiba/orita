"""Task 33. A render/lint pass rejects any published call phrased as an
instruction ("buy," "sell," "you should") or claiming unlabeled certainty,
before a single character of it renders -- proven for each failure class,
proven a clean call still passes, and proven the reject happens strictly
before render (no partial/truncated output ever escapes).
"""
from __future__ import annotations

import os
import sys
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORACLE_ENGINE_ROOT = os.path.dirname(_TESTS_DIR)  # oracle/oracle_engine

sys.path.insert(0, os.path.join(_ORACLE_ENGINE_ROOT, "src"))

from oracle_engine import copylint  # noqa: E402


class TestInstructionPhrasedRejected(unittest.TestCase):
    def test_buy_rejected(self):
        with self.assertRaises(copylint.CopyRejected):
            copylint.enforce_copy("Now might be a good time to buy the dip.", 0.6)

    def test_sell_rejected(self):
        with self.assertRaises(copylint.CopyRejected):
            copylint.enforce_copy("Time to sell before the close.", 0.6)

    def test_you_should_rejected(self):
        with self.assertRaises(copylint.CopyRejected):
            copylint.enforce_copy("You should rotate out of this position.", 0.6)

    def test_invest_in_rejected(self):
        with self.assertRaises(copylint.CopyRejected):
            copylint.enforce_copy("Invest in this before the announcement.", 0.6)

    def test_seller_is_not_a_false_positive(self):
        # "seller" contains "sell" but isn't the instruction verb -- word
        # boundaries must not flag ordinary vocabulary.
        result = copylint.lint_claim("The seller-side volume ticked up this week.", 0.6)
        self.assertTrue(result.ok, result.reason)


class TestUnlabeledCertaintyRejected(unittest.TestCase):
    def test_guaranteed_rejected(self):
        with self.assertRaises(copylint.CopyRejected):
            copylint.enforce_copy("This is a guaranteed move by Friday.", 0.6)

    def test_certain_rejected(self):
        with self.assertRaises(copylint.CopyRejected):
            copylint.enforce_copy("It is certain to happen by Friday.", 0.6)

    def test_cant_lose_rejected(self):
        with self.assertRaises(copylint.CopyRejected):
            copylint.enforce_copy("This can't lose over the next quarter.", 0.6)

    def test_uncertain_is_not_a_false_positive(self):
        # "uncertain" contains "certain" but asserts the opposite claim.
        result = copylint.lint_claim("The outcome is genuinely uncertain here.", 0.4)
        self.assertTrue(result.ok, result.reason)

    def test_missing_confidence_rejected(self):
        with self.assertRaises(copylint.CopyRejected):
            copylint.enforce_copy("A quiet week for this metric.", None)


class TestCleanCallPasses(unittest.TestCase):
    def test_clean_forecast_passes(self):
        result = copylint.lint_claim(
            "This metric is likely to move up modestly this week.", 0.65
        )
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(len(result.checks), 3)
        self.assertTrue(all(passed for _, passed in result.checks))

    def test_enforce_copy_returns_result_when_clean(self):
        result = copylint.enforce_copy("A modest move is more likely than not.", 0.55)
        self.assertIsInstance(result, copylint.LintResult)
        self.assertTrue(result.ok)


class TestRejectedBeforeRender(unittest.TestCase):
    def test_render_call_raises_and_produces_no_text(self):
        with self.assertRaises(copylint.CopyRejected):
            copylint.render_call("retrya", "Buy now, guaranteed.", 0.9, "2026-07-13T09:00:00Z")

    def test_render_call_renders_when_clean(self):
        text = copylint.render_call(
            "retrya", "This metric leans up this week.", 0.6, "2026-07-13T09:00:00Z"
        )
        self.assertIn("retrya", text)
        self.assertIn("0.60", text)

    def test_empty_claim_rejected(self):
        with self.assertRaises(copylint.CopyRejected):
            copylint.enforce_copy("   ", 0.5)

    def test_reason_names_every_failed_check(self):
        try:
            copylint.enforce_copy("You should buy, guaranteed.", None)
            self.fail("expected CopyRejected")
        except copylint.CopyRejected as exc:
            reason = str(exc)
            self.assertIn("FAIL", reason)
            # all three checks should fail on this claim
            self.assertEqual(reason.count("FAIL"), 3)


if __name__ == "__main__":
    unittest.main()
