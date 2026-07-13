"""Task 32. Once an outcome is knowable, the grade is sealed as its own
chained ledger entry linked to the original call's seq -- proven present
and linked, proven a grade cannot reference a non-existent call seq, and
proven a terminal grade can never be quietly replaced (Ogun's law: no
"didn't count" pile).
"""
from __future__ import annotations

import ast
import json
import os
import sys
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORACLE_ENGINE_ROOT = os.path.dirname(_TESTS_DIR)  # oracle/oracle_engine
_ORACLE_ROOT = os.path.dirname(_ORACLE_ENGINE_ROOT)  # oracle/
_ORITA_ROOT = os.path.dirname(_ORACLE_ROOT)  # repo root
_TOOLS_DIR = os.path.join(_ORITA_ROOT, "tools")

sys.path.insert(0, os.path.join(_ORACLE_ENGINE_ROOT, "src"))

from oracle_engine import grading, prediction  # noqa: E402


def _fresh_ledger_module(tmp_ledger_path: str):
    mod = prediction.load_ledger_module(_TOOLS_DIR)
    mod.LEDGER = tmp_ledger_path
    return mod


class TestGradeRequiresRealCall(unittest.TestCase):
    def setUp(self):
        self.tmp_path = os.path.join(_TESTS_DIR, "_scratch_grading_ledger.jsonl")
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)
        self.mod = _fresh_ledger_module(self.tmp_path)

    def tearDown(self):
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def test_grade_cannot_reference_a_non_existent_call_seq(self):
        with self.assertRaises(grading.GradingError):
            grading.seal_grade("ogun", 999, "correct",
                                ts="2026-07-20T00:00:00+00:00", ledger_module=self.mod)
        # nothing was written
        self.assertEqual(self.mod._entries(), [])

    def test_grade_cannot_reference_a_grade_entry_as_its_call(self):
        call = prediction.seal_prediction("nisaba", "a fork opens within 30 days", 0.5,
                                           ts="2026-07-13T03:00:00+00:00", ledger_module=self.mod)
        grade = grading.seal_grade("ogun", call["seq"], "pending",
                                    ts="2026-07-14T00:00:00+00:00", ledger_module=self.mod)
        with self.assertRaises(grading.GradingError):
            grading.seal_grade("ogun", grade["seq"], "correct",
                                ts="2026-07-15T00:00:00+00:00", ledger_module=self.mod)

    def test_call_seq_must_be_a_non_negative_int(self):
        with self.assertRaises(grading.GradingError):
            grading.find_call(-1, [])
        with self.assertRaises(grading.GradingError):
            grading.find_call(1.5, [])
        with self.assertRaises(grading.GradingError):
            grading.find_call(True, [])

    def test_requires_explicit_timestamp(self):
        call = prediction.seal_prediction("retrya", "the coin lands on the third try", 0.4,
                                           ts="2026-07-13T02:00:00+00:00", ledger_module=self.mod)
        with self.assertRaises(grading.GradingError):
            grading.seal_grade("ogun", call["seq"], "correct", ts=None, ledger_module=self.mod)

    def test_rejects_empty_actor(self):
        with self.assertRaises(grading.GradingError):
            grading.validate_actor("")

    def test_rejects_unknown_outcome(self):
        with self.assertRaises(grading.GradingError):
            grading.validate_outcome("didnt-count")
        with self.assertRaises(grading.GradingError):
            grading.validate_outcome("void")


class TestGradedCallLinkedInChain(unittest.TestCase):
    def setUp(self):
        self.tmp_path = os.path.join(_TESTS_DIR, "_scratch_grading_ledger2.jsonl")
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)
        self.mod = _fresh_ledger_module(self.tmp_path)

    def tearDown(self):
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def test_graded_call_and_original_prediction_both_present_and_linked(self):
        call = prediction.seal_prediction("kwaku-ananse", "the town ships a real card trick by Monday", 0.62,
                                           ts="2026-07-13T07:00:00+00:00", ledger_module=self.mod)
        grade = grading.seal_grade("ogun", call["seq"], "correct",
                                    ts="2026-07-20T09:00:00+00:00", ledger_module=self.mod)

        self.assertEqual(grade["actor"], "ogun")
        self.assertEqual(grade["act"], grading.GRADE_ACT)
        payload = grading.parse_grade_detail(grade["detail"])
        self.assertEqual(payload["call_seq"], call["seq"])
        self.assertEqual(payload["outcome"], "correct")

        # the original prediction is untouched
        entries = self.mod._entries()
        self.assertEqual(entries[call["seq"]]["detail"], call["detail"])
        self.assertEqual(entries[call["seq"]]["act"], prediction.PREDICTION_ACT)
        self.assertTrue(self.mod.verify())

    def test_two_calls_each_graded_chain_and_verify_clean(self):
        call_a = prediction.seal_prediction("nyx", "traffic dips on Sunday", 0.55,
                                             ts="2026-07-13T00:00:00+00:00", ledger_module=self.mod)
        call_b = prediction.seal_prediction("ogun", "a red badge within the week", 0.3,
                                             ts="2026-07-13T01:00:00+00:00", ledger_module=self.mod)
        grading.seal_grade("ogun", call_a["seq"], "incorrect",
                            ts="2026-07-14T00:00:00+00:00", ledger_module=self.mod)
        grading.seal_grade("ogun", call_b["seq"], "correct",
                            ts="2026-07-21T00:00:00+00:00", ledger_module=self.mod)
        self.assertTrue(self.mod.verify())

    def test_pending_then_one_terminal_grade_is_allowed(self):
        call = prediction.seal_prediction("off-by-one", "the streak reaches day 7", 0.8,
                                           ts="2026-07-13T05:00:00+00:00", ledger_module=self.mod)
        grading.seal_grade("ogun", call["seq"], "pending",
                            ts="2026-07-14T00:00:00+00:00", ledger_module=self.mod)
        final = grading.seal_grade("ogun", call["seq"], "correct",
                                    ts="2026-07-19T12:00:00+00:00", ledger_module=self.mod)
        self.assertEqual(grading.parse_grade_detail(final["detail"])["outcome"], "correct")
        self.assertTrue(self.mod.verify())

    def test_post_hoc_edit_of_a_sealed_grade_breaks_verify(self):
        call = prediction.seal_prediction("esu-elegba", "a first-timer crosses within a day", 0.7,
                                           ts="2026-07-13T06:00:00+00:00", ledger_module=self.mod)
        grading.seal_grade("ogun", call["seq"], "incorrect",
                            ts="2026-07-14T00:00:00+00:00", ledger_module=self.mod)
        self.assertTrue(self.mod.verify())

        with open(self.tmp_path) as f:
            lines = [line for line in f if line.strip()]
        entry = json.loads(lines[-1])
        payload = json.loads(entry["detail"])
        payload["outcome"] = "correct"  # a hindsight edit, made after sealing
        entry["detail"] = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        lines[-1] = json.dumps(entry, ensure_ascii=False) + "\n"
        with open(self.tmp_path, "w") as f:
            f.writelines(lines)

        self.assertFalse(self.mod.verify())


class TestNoQuietlyMovingALossIntoADidntCountPile(unittest.TestCase):
    """Ogun's law, ROADMAP.md task 32: once a call has a terminal grade,
    no second grade for the same call_seq is permitted -- a loss cannot be
    regraded away, and a win cannot be quietly voided either."""

    def setUp(self):
        self.tmp_path = os.path.join(_TESTS_DIR, "_scratch_grading_ledger3.jsonl")
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)
        self.mod = _fresh_ledger_module(self.tmp_path)

    def tearDown(self):
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def test_cannot_regrade_a_loss_into_something_else(self):
        call = prediction.seal_prediction("ogun", "a fork opens within 30 days", 0.5,
                                           ts="2026-07-13T03:00:00+00:00", ledger_module=self.mod)
        grading.seal_grade("ogun", call["seq"], "incorrect",
                            ts="2026-07-20T00:00:00+00:00", ledger_module=self.mod)
        with self.assertRaises(grading.GradingError):
            grading.seal_grade("ogun", call["seq"], "pending",
                                ts="2026-07-21T00:00:00+00:00", ledger_module=self.mod)
        with self.assertRaises(grading.GradingError):
            grading.seal_grade("ogun", call["seq"], "correct",
                                ts="2026-07-22T00:00:00+00:00", ledger_module=self.mod)
        # only the one terminal grade is on the chain
        grades = grading.existing_grades(call["seq"], self.mod._entries())
        self.assertEqual(len(grades), 1)

    def test_cannot_regrade_a_win_either(self):
        call = prediction.seal_prediction("ogun", "the badge stays green", 0.9,
                                           ts="2026-07-13T03:00:00+00:00", ledger_module=self.mod)
        grading.seal_grade("ogun", call["seq"], "correct",
                            ts="2026-07-20T00:00:00+00:00", ledger_module=self.mod)
        with self.assertRaises(grading.GradingError):
            grading.seal_grade("ogun", call["seq"], "incorrect",
                                ts="2026-07-21T00:00:00+00:00", ledger_module=self.mod)


class TestNoEditPathExists(unittest.TestCase):
    """Doctrine test: this module must not define anything shaped like an
    edit/update/delete/rewrite of a sealed entry -- not disabled, absent.
    Mirrors prediction.py's own doctrine test (task 31)."""

    def test_module_defines_no_edit_shaped_function(self):
        src_path = os.path.join(_ORACLE_ENGINE_ROOT, "src", "oracle_engine", "grading.py")
        with open(src_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=src_path)

        forbidden_substrings = ("edit", "update", "rewrite", "amend", "mutate", "delete", "overwrite")
        func_names = [
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        self.assertTrue(func_names, "expected at least one function in grading.py")
        for name in func_names:
            lowered = name.lower()
            for forbidden in forbidden_substrings:
                self.assertNotIn(
                    forbidden, lowered,
                    f"grading.py defines {name!r}, which looks edit-shaped — "
                    "a sealed entry must have no rewrite path, by omission",
                )

    def test_schema_is_exactly_two_conceptual_fields(self):
        payload = grading.grade_payload(0, "pending")
        self.assertEqual(set(payload.keys()), {"call_seq", "outcome"})


if __name__ == "__main__":
    unittest.main()
