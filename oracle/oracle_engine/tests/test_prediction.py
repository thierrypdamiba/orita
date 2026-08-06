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

from oracle_engine import copylint, prediction  # noqa: E402


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


class TestSealGenericPrediction(unittest.TestCase):
    """Task 573: `seal_generic_prediction` is the shared glue an AST-hash
    sweep found byte-identical across all 25 `*_cadence.py` siblings' own
    `seal_<topic>_prediction`. Exercised directly here (not through any
    real cadence module) with a fake `build_prediction_fn`/
    `load_snapshots_fn` pair, the same "prove the shared function itself
    works" discipline the sibling-delegation proof in test_time_utils.py
    complements rather than duplicates."""

    def setUp(self):
        self.tmp_path = os.path.join(_TESTS_DIR, "_scratch_generic_ledger.jsonl")
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)
        self.mod = _fresh_ledger_module(self.tmp_path)

    def tearDown(self):
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def _build(self, now, snapshots, current_count, **kwargs):
        return {
            "claim": f"there will be at least {current_count} things (built with {kwargs})",
            "confidence": 0.5,
        }

    def test_seals_using_the_supplied_build_and_load_functions(self):
        calls = {"load": 0}

        def fake_load_snapshots():
            calls["load"] += 1
            return []

        entry = prediction.seal_generic_prediction(
            self._build,
            fake_load_snapshots,
            now="2026-08-06T14:00:00+00:00",
            ts="2026-08-06T14:00:00+00:00",
            current_count=3,
            actor="esu-elegba",
            ledger_module=self.mod,
        )
        self.assertEqual(calls["load"], 1, "snapshots=None must call the supplied loader")
        self.assertEqual(entry["actor"], "esu-elegba")
        payload = prediction.parse_prediction_detail(entry["detail"])
        self.assertIn("at least 3 things", payload["claim"])
        self.assertTrue(self.mod.verify())

    def test_an_explicit_snapshots_list_skips_the_loader(self):
        def fake_load_snapshots():
            raise AssertionError("loader must not be called when snapshots is given")

        prediction.seal_generic_prediction(
            self._build,
            fake_load_snapshots,
            now="2026-08-06T14:00:00+00:00",
            ts="2026-08-06T14:00:00+00:00",
            current_count=1,
            actor="esu-elegba",
            snapshots=[{"ts": "2026-08-05T00:00:00Z", "count": 1}],
            ledger_module=self.mod,
        )
        self.assertTrue(self.mod.verify())

    def test_build_kwargs_pass_through_to_the_build_function(self):
        entry = prediction.seal_generic_prediction(
            self._build,
            lambda: [],
            now="2026-08-06T14:00:00+00:00",
            ts="2026-08-06T14:00:00+00:00",
            current_count=7,
            actor="esu-elegba",
            ledger_module=self.mod,
            horizon_hours=336,
        )
        payload = prediction.parse_prediction_detail(entry["detail"])
        self.assertIn("horizon_hours", payload["claim"])

    def test_a_copylint_rejected_claim_never_reaches_the_ledger(self):
        def build_bad(now, snapshots, current_count, **kwargs):
            return {"claim": "it will definitely happen no matter what", "confidence": 0.9}

        with self.assertRaises(copylint.CopyRejected):
            prediction.seal_generic_prediction(
                build_bad,
                lambda: [],
                now="2026-08-06T14:00:00+00:00",
                ts="2026-08-06T14:00:00+00:00",
                current_count=1,
                actor="esu-elegba",
                ledger_module=self.mod,
            )
        self.assertFalse(os.path.exists(self.tmp_path) and open(self.tmp_path).read().strip())


class TestParsePredictionDetailRejectsNonDictPayloads(unittest.TestCase):
    """ROADMAP.md task 363. `parse_prediction_detail()` did a bare
    `json.loads(detail)` then `payload.keys()` with no shape check -- a
    valid-JSON-non-dict `detail` (list/null/number/bool/string) raised an
    uncaught `AttributeError` instead of the module's own named
    `PredictionError`, mirroring the identical gap `grading.py`'s
    `parse_grade_detail()` had (task 363's other half)."""

    def test_list_shaped_detail_raises_named_error_not_attributeerror(self):
        with self.assertRaises(prediction.PredictionError):
            prediction.parse_prediction_detail("[1, 2]")

    def test_null_shaped_detail_raises_named_error_not_attributeerror(self):
        with self.assertRaises(prediction.PredictionError):
            prediction.parse_prediction_detail("null")

    def test_bare_number_detail_raises_named_error_not_attributeerror(self):
        with self.assertRaises(prediction.PredictionError):
            prediction.parse_prediction_detail("5")

    def test_bare_bool_detail_raises_named_error_not_attributeerror(self):
        with self.assertRaises(prediction.PredictionError):
            prediction.parse_prediction_detail("true")

    def test_bare_string_detail_raises_named_error_not_attributeerror(self):
        with self.assertRaises(prediction.PredictionError):
            prediction.parse_prediction_detail('"oops"')

    def test_well_formed_detail_still_parses_normally(self):
        detail = json.dumps({"claim": "x", "confidence": 0.5}, sort_keys=True)
        self.assertEqual(
            prediction.parse_prediction_detail(detail),
            {"claim": "x", "confidence": 0.5},
        )


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
