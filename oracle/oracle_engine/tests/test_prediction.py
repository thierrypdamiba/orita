"""Task 31. A prediction is sealed (actor, claim, confidence, timestamp)
the moment it's made, before the outcome exists to grade against — proven
chain-verifiable, proven immutable (a post-hoc edit breaks `ledger.py
verify`), and proven to have no edit path at all, by grepping the module's
own source for the absence of one.
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

from oracle_engine import prediction  # noqa: E402


def _fresh_ledger_module(tmp_ledger_path: str):
    mod = prediction.load_ledger_module(_TOOLS_DIR)
    mod.LEDGER = tmp_ledger_path
    return mod


class TestSchemaValidation(unittest.TestCase):
    def test_rejects_empty_claim(self):
        with self.assertRaises(prediction.PredictionError):
            prediction.validate_claim("   ")

    def test_rejects_non_string_claim(self):
        with self.assertRaises(prediction.PredictionError):
            prediction.validate_claim(None)  # type: ignore[arg-type]

    def test_rejects_confidence_out_of_range(self):
        with self.assertRaises(prediction.PredictionError):
            prediction.validate_confidence(0.0)
        with self.assertRaises(prediction.PredictionError):
            prediction.validate_confidence(1.5)
        with self.assertRaises(prediction.PredictionError):
            prediction.validate_confidence(-0.1)

    def test_rejects_non_numeric_or_bool_confidence(self):
        with self.assertRaises(prediction.PredictionError):
            prediction.validate_confidence("high")  # type: ignore[arg-type]
        with self.assertRaises(prediction.PredictionError):
            prediction.validate_confidence(True)

    def test_accepts_valid_confidence_boundary(self):
        prediction.validate_confidence(1.0)
        prediction.validate_confidence(0.01)

    def test_rejects_empty_actor(self):
        with self.assertRaises(prediction.PredictionError):
            prediction.validate_actor("")

    def test_requires_explicit_timestamp(self):
        with self.assertRaises(prediction.PredictionError):
            prediction.seal_prediction("kwaku-ananse", "a real claim", 0.7, ts=None)


class TestSealedShape(unittest.TestCase):
    def setUp(self):
        self.tmp_path = os.path.join(_TESTS_DIR, "_scratch_ledger.jsonl")
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)
        self.mod = _fresh_ledger_module(self.tmp_path)

    def tearDown(self):
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def test_seal_prediction_writes_exactly_the_schema_fields(self):
        entry = prediction.seal_prediction(
            "kwaku-ananse", "the town ships a real card trick by Monday", 0.62,
            ts="2026-07-13T07:00:00+00:00", ledger_module=self.mod,
        )
        self.assertEqual(entry["actor"], "kwaku-ananse")
        self.assertEqual(entry["act"], prediction.PREDICTION_ACT)
        payload = prediction.parse_prediction_detail(entry["detail"])
        self.assertEqual(payload["claim"], "the town ships a real card trick by Monday")
        self.assertAlmostEqual(payload["confidence"], 0.62)
        self.assertIn("hash", entry)
        self.assertIn("prev", entry)
        self.assertIn("seq", entry)
        self.assertIn("ts", entry)

    def test_two_predictions_chain_and_verify_clean(self):
        prediction.seal_prediction("nyx", "traffic dips on Sunday", 0.55,
                                    ts="2026-07-13T00:00:00+00:00", ledger_module=self.mod)
        prediction.seal_prediction("ogun", "a red badge within the week", 0.3,
                                    ts="2026-07-13T01:00:00+00:00", ledger_module=self.mod)
        self.assertTrue(self.mod.verify())

    def test_post_hoc_edit_of_a_sealed_prediction_breaks_verify(self):
        """The whole point (docs/oracle-desk.md): 'nobody edits a prediction
        after the fact.' Prove it by trying — directly, at the file level,
        since this module offers no function that would do it for you —
        and showing `ledger.py verify()` catches it."""
        prediction.seal_prediction("retrya", "the coin lands on the third try", 0.4,
                                    ts="2026-07-13T02:00:00+00:00", ledger_module=self.mod)
        self.assertTrue(self.mod.verify())

        with open(self.tmp_path) as f:
            lines = [line for line in f if line.strip()]
        entry = json.loads(lines[-1])
        payload = json.loads(entry["detail"])
        payload["confidence"] = 0.99  # a hindsight edit, made after sealing
        entry["detail"] = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        lines[-1] = json.dumps(entry, ensure_ascii=False) + "\n"
        with open(self.tmp_path, "w") as f:
            f.writelines(lines)

        self.assertFalse(self.mod.verify())

    def test_grade_entries_link_to_a_seq_rather_than_rewriting(self):
        """Task 32 (Ogun) is grading, not this task, but the schema must
        not preclude it: a grade is a *new* entry that names the original
        call's seq, never a mutation of the call itself."""
        call = prediction.seal_prediction("ogun", "a fork opens within 30 days", 0.5,
                                           ts="2026-07-13T03:00:00+00:00", ledger_module=self.mod)
        grade_detail = json.dumps({"call_seq": call["seq"], "outcome": "pending"}, sort_keys=True)
        grade = self.mod.append("ogun", "grade", grade_detail, "2026-07-20T00:00:00+00:00")
        self.assertEqual(json.loads(grade["detail"])["call_seq"], call["seq"])
        self.assertTrue(self.mod.verify())
        # the original call is untouched
        with open(self.tmp_path) as f:
            lines = [json.loads(line) for line in f if line.strip()]
        self.assertEqual(lines[call["seq"]]["detail"], call["detail"])


class TestNoEditPathExists(unittest.TestCase):
    """Doctrine test: this module must not define anything shaped like an
    edit/update/delete/rewrite of a sealed entry — not disabled, absent.
    Mirrors seam_engine/draftback.py's static-source-proof discipline."""

    def test_module_defines_no_edit_shaped_function(self):
        src_path = os.path.join(_ORACLE_ENGINE_ROOT, "src", "oracle_engine", "prediction.py")
        with open(src_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=src_path)

        forbidden_substrings = ("edit", "update", "rewrite", "amend", "mutate", "delete", "overwrite")
        func_names = [
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        self.assertTrue(func_names, "expected at least one function in prediction.py")
        for name in func_names:
            lowered = name.lower()
            for forbidden in forbidden_substrings:
                self.assertNotIn(
                    forbidden, lowered,
                    f"prediction.py defines {name!r}, which looks edit-shaped — "
                    "a sealed call must have no rewrite path, by omission",
                )

    def test_schema_is_exactly_three_conceptual_fields(self):
        payload = prediction.prediction_payload("x", 0.5)
        self.assertEqual(set(payload.keys()), {"claim", "confidence"})


if __name__ == "__main__":
    unittest.main()
