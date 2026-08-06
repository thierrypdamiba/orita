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
from unittest import mock

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORACLE_ENGINE_ROOT = os.path.dirname(_TESTS_DIR)  # oracle/oracle_engine
_ORACLE_ROOT = os.path.dirname(_ORACLE_ENGINE_ROOT)  # oracle/
_ORITA_ROOT = os.path.dirname(_ORACLE_ROOT)  # repo root
_TOOLS_DIR = os.path.join(_ORITA_ROOT, "tools")

sys.path.insert(0, os.path.join(_ORACLE_ENGINE_ROOT, "src"))

from oracle_engine import (  # noqa: E402
    autograde,
    branch_autograde,
    collaborator_autograde,
    comment_autograde,
    commit_autograde,
    commit_comment_autograde,
    contributor_autograde,
    deployment_autograde,
    follower_autograde,
    following_autograde,
    fork_autograde,
    grading,
    issue_autograde,
    issue_comment_autograde,
    label_autograde,
    listed_autograde,
    media_autograde,
    milestone_autograde,
    pr_autograde,
    prediction,
    release_autograde,
    run_autograde,
    star_autograde,
    subscriber_autograde,
    tag_autograde,
    topic_autograde,
    tweet_autograde,
    workflow_autograde,
)

AUTOGRADE_SIBLINGS = [
    autograde,
    branch_autograde,
    collaborator_autograde,
    comment_autograde,
    commit_autograde,
    commit_comment_autograde,
    contributor_autograde,
    deployment_autograde,
    follower_autograde,
    following_autograde,
    fork_autograde,
    issue_autograde,
    issue_comment_autograde,
    label_autograde,
    listed_autograde,
    media_autograde,
    milestone_autograde,
    pr_autograde,
    release_autograde,
    run_autograde,
    star_autograde,
    subscriber_autograde,
    tag_autograde,
    topic_autograde,
    tweet_autograde,
    workflow_autograde,
]


def _expected_autograde_error_cls(mod):
    """Derive `<Words>AutogradeError` from a sibling autograde module's own
    name (`star_autograde` -> `StarAutogradeError`; the base `autograde`
    module itself -> bare `AutogradeError`), the exact convention every one
    of the 25 siblings' real error class already follows -- checked against
    the live module, not assumed. Mirrors `test_time_utils.py`'s own
    `_expected_error_cls` for the `*_cadence.py` family."""
    mod_name = mod.__name__.rsplit(".", 1)[-1]
    stem = "" if mod_name == "autograde" else mod_name.replace("_autograde", "")
    name = "".join(word.capitalize() for word in stem.split("_")) + "AutogradeError" if stem else "AutogradeError"
    return getattr(mod, name)


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


class TestExistingGradesSkipsNonDictPayloads(unittest.TestCase):
    """ROADMAP.md task 302. `existing_grades()` is the one function every
    one of the 25 `oracle_engine/*_autograde.py` `find_due_calls()`
    implementations (tasks 276-301) calls directly and unguarded. Before
    this task, a `grade`-act entry whose `detail` was syntactically valid
    JSON but not a JSON object (a list, `null`, a bare number, a bool, a
    string) parsed cleanly -- so `except (KeyError, json.JSONDecodeError)`
    never fired -- and the very next line's `payload.get("call_seq")`
    raised an uncaught `AttributeError`, since none of those types define
    `.get`. That crashed every already-hardened autograde sibling from
    underneath, plus `assert_not_already_terminal()`/`seal_grade()`, the
    function the live `oracle-cadence` cron actually calls to seal a new
    grade."""

    def _entries_with_malformed_grade(self, malformed_detail: str) -> list[dict]:
        return [
            {"seq": 0, "act": prediction.PREDICTION_ACT, "detail": "{}"},
            {"seq": 1, "act": grading.GRADE_ACT, "detail": malformed_detail},
        ]

    def test_list_shaped_detail_is_skipped_not_raised(self):
        entries = self._entries_with_malformed_grade("[1, 2]")
        self.assertEqual(grading.existing_grades(0, entries), [])

    def test_null_shaped_detail_is_skipped_not_raised(self):
        entries = self._entries_with_malformed_grade("null")
        self.assertEqual(grading.existing_grades(0, entries), [])

    def test_bare_number_detail_is_skipped_not_raised(self):
        entries = self._entries_with_malformed_grade("5")
        self.assertEqual(grading.existing_grades(0, entries), [])

    def test_bare_bool_detail_is_skipped_not_raised(self):
        entries = self._entries_with_malformed_grade("true")
        self.assertEqual(grading.existing_grades(0, entries), [])

    def test_bare_string_detail_is_skipped_not_raised(self):
        entries = self._entries_with_malformed_grade('"oops"')
        self.assertEqual(grading.existing_grades(0, entries), [])

    def test_a_real_grade_still_found_alongside_a_malformed_one(self):
        entries = [
            {"seq": 0, "act": prediction.PREDICTION_ACT, "detail": "{}"},
            {"seq": 1, "act": grading.GRADE_ACT, "detail": "[1, 2]"},
            {
                "seq": 2,
                "act": grading.GRADE_ACT,
                "detail": json.dumps({"call_seq": 0, "outcome": "pending"}, sort_keys=True),
            },
        ]
        found = grading.existing_grades(0, entries)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["seq"], 2)

    def test_assert_not_already_terminal_unaffected_by_a_malformed_sibling_grade(self):
        """The regrade guard `seal_grade()` actually calls in production
        must keep working normally when a malformed grade entry sits on
        the chain alongside a real terminal one -- it should still refuse
        the regrade, not crash and not silently allow it."""
        tmp_path = os.path.join(_TESTS_DIR, "_scratch_grading_ledger4.jsonl")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        mod = _fresh_ledger_module(tmp_path)
        try:
            call = prediction.seal_prediction(
                "ogun", "a fork opens within 30 days", 0.5,
                ts="2026-07-13T03:00:00+00:00", ledger_module=mod,
            )
            grading.seal_grade("ogun", call["seq"], "incorrect",
                                ts="2026-07-20T00:00:00+00:00", ledger_module=mod)
            entries = mod._entries()
            entries.append({"seq": len(entries), "act": grading.GRADE_ACT, "detail": "[1, 2]"})
            # existing_grades must not crash on the appended malformed entry
            grades = grading.existing_grades(call["seq"], entries)
            self.assertEqual(len(grades), 1)
            with self.assertRaises(grading.GradingError):
                grading.assert_not_already_terminal(call["seq"], entries)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestParseGradeDetailRejectsNonDictPayloads(unittest.TestCase):
    """ROADMAP.md task 363. `parse_grade_detail()` is the function every
    one of the 25 `oracle_engine/*_autograde.py` modules calls to read a
    prior grade's outcome back out (`grading.parse_grade_detail(g["detail"])
    ["outcome"]`). Before this task it did a bare `json.loads(detail)` then
    `payload.keys()` with no shape check -- a valid-JSON-non-dict `detail`
    (list/null/number/bool/string) raised an uncaught `AttributeError`
    instead of the module's own named `GradingError`, unlike its sibling
    `existing_grades()` (task 302) which already guards the same shape."""

    def test_list_shaped_detail_raises_named_error_not_attributeerror(self):
        with self.assertRaises(grading.GradingError):
            grading.parse_grade_detail("[1, 2]")

    def test_null_shaped_detail_raises_named_error_not_attributeerror(self):
        with self.assertRaises(grading.GradingError):
            grading.parse_grade_detail("null")

    def test_bare_number_detail_raises_named_error_not_attributeerror(self):
        with self.assertRaises(grading.GradingError):
            grading.parse_grade_detail("5")

    def test_bare_bool_detail_raises_named_error_not_attributeerror(self):
        with self.assertRaises(grading.GradingError):
            grading.parse_grade_detail("true")

    def test_bare_string_detail_raises_named_error_not_attributeerror(self):
        with self.assertRaises(grading.GradingError):
            grading.parse_grade_detail('"oops"')

    def test_well_formed_detail_still_parses_normally(self):
        detail = json.dumps({"call_seq": 0, "outcome": "correct"}, sort_keys=True)
        self.assertEqual(
            grading.parse_grade_detail(detail),
            {"call_seq": 0, "outcome": "correct"},
        )


class TestLoadClaimPayload(unittest.TestCase):
    """`grading.load_claim_payload` -- the shared implementation every one
    of the 25 `oracle_engine/*_autograde.py` modules' own private
    `_load_claim_payload` used to carry a byte-identical copy of, differing
    only in which module-local `*AutogradeError` it raised."""

    def test_well_formed_dict_payload_passes_through(self):
        detail = json.dumps({"claim": "By 2026-08-06T00:00:00Z, ..."}, sort_keys=True)
        self.assertEqual(
            grading.load_claim_payload(detail, grading.GradingError),
            {"claim": "By 2026-08-06T00:00:00Z, ..."},
        )

    def test_list_shaped_detail_raises_the_given_error_cls(self):
        with self.assertRaises(grading.GradingError):
            grading.load_claim_payload("[1, 2]", grading.GradingError)

    def test_null_shaped_detail_raises_the_given_error_cls(self):
        with self.assertRaises(grading.GradingError):
            grading.load_claim_payload("null", grading.GradingError)

    def test_bare_number_detail_raises_the_given_error_cls(self):
        with self.assertRaises(grading.GradingError):
            grading.load_claim_payload("5", grading.GradingError)

    def test_a_different_error_cls_is_the_one_actually_raised(self):
        """Not `GradingError` itself -- proves `error_cls` is genuinely
        used, not hardcoded, the same guarantee `record_snapshot`/
        `reject_malformed`'s own `error_cls` parameter already proves for
        the `*_cadence.py` family."""

        class ProbeError(ValueError):
            pass

        with self.assertRaises(ProbeError):
            grading.load_claim_payload("[1, 2]", ProbeError)

    def test_malformed_json_still_raises_jsondecodeerror_not_the_error_cls(self):
        """Unchanged from every sibling's own pre-consolidation behavior:
        a `json.loads` failure is not caught here -- the caller's own
        `except (..., json.JSONDecodeError)` handles that, same as
        before."""
        with self.assertRaises(json.JSONDecodeError):
            grading.load_claim_payload("{not valid json", grading.GradingError)


class LoadClaimPayloadDelegatesCase(unittest.TestCase):
    """Every sibling autograde module's own `_load_claim_payload(detail)`
    must genuinely call through to `grading.load_claim_payload` with its
    own `*AutogradeError` subclass as `error_cls` -- not carry a reinlined
    copy of the parse-and-validate logic. Mirrors `test_time_utils.py`'s
    `RecordSnapshotDelegatesCase`/`RejectMalformedDelegatesCase` exactly,
    one directory over, for the autograde family instead of the cadence
    one."""

    def test_every_sibling_wrapper_delegates_to_the_shared_function(self):
        self.assertEqual(
            len(AUTOGRADE_SIBLINGS), 26, "sibling list drifted from the live sweep"
        )
        for mod in AUTOGRADE_SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                sentinel = object()
                calls = []

                def fake_load_claim_payload(detail, error_cls, _calls=calls, _sentinel=sentinel):
                    _calls.append((detail, error_cls))
                    return _sentinel

                with mock.patch.object(grading, "load_claim_payload", fake_load_claim_payload):
                    result = mod._load_claim_payload("some probe detail")
                self.assertIs(
                    result,
                    sentinel,
                    f"{mod.__name__}._load_claim_payload did not return the shared "
                    "function's result -- it may hold a reinlined copy again",
                )
                self.assertEqual(
                    calls,
                    [("some probe detail", _expected_autograde_error_cls(mod))],
                    f"{mod.__name__}._load_claim_payload did not pass its argument "
                    "and own error class through to grading.load_claim_payload unchanged",
                )

    def test_every_sibling_still_raises_its_own_error_class_on_a_non_dict_payload(self):
        """Not mocked: proves the real, live delegation still surfaces the
        right exception type end to end, not just that the mock saw the
        right kwarg."""
        for mod in AUTOGRADE_SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                with self.assertRaises(_expected_autograde_error_cls(mod)):
                    mod._load_claim_payload("[1, 2]")

    def test_a_well_formed_payload_still_parses_normally_through_every_sibling(self):
        for mod in AUTOGRADE_SIBLINGS:
            with self.subTest(sibling=mod.__name__):
                detail = json.dumps({"claim": "probe"}, sort_keys=True)
                self.assertEqual(mod._load_claim_payload(detail), {"claim": "probe"})


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
