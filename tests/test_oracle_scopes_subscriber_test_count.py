"""ROADMAP #153. `oracle/SCOPES.md`'s subscriber-cadence `**BLOCKED**`
paragraph (task 89's correction) makes a concrete, checkable claim about a
sibling test surface -- one no prior audit task has ever cross-checked:

    `fetch_subscriber_count` is fully built and tested (34 tests, all
    green) and will seal the moment this wall lifts...

That "34 tests" number is never derived from anything -- it is Off-By-One's
own hand-typed arithmetic (task 50's own two test files: 20 in
`test_subscriber_cadence.py` + 14 in `test_subscriber_autograde.py`),
sealed into prose and never rechecked since. Task 131's own
`test_oracle_scopes_doc.py` generalizes the doc's `**PENDING:**` /
`**RESOLVED (corrected` paragraphs against the real snapshot files on disk,
but the subscriber-cadence paragraph uses a third marker entirely
(`**BLOCKED --`) that generalization deliberately never reaches, and none
of its four checks look at a test *count* claim in the first place -- this
is the exact "claims a number about itself, nothing ever checked it
against the live thing it describes" shape tasks 130/131/133/136/137/138/
141/142/143/145/148/149 already closed elsewhere, found here for the first
time in this doc's own BLOCKED paragraph.

This module extracts the claimed number structurally (regex over the
doc's live text, never a second hand-typed "34"), computes the REAL count
structurally too (`unittest.defaultTestLoader.loadTestsFromModule` against
the two real, live test files it names, never re-counted by hand), and
cross-checks them. Plus mutation-based hand-verification (the same
before/after discipline tasks 135-149 already hold their own checkers to):
a synthetic copy of the doc's real paragraph with the number changed is
proven to flip the checker from clean to broken, and a synthetic drop in
the real live test count (simulating a test quietly deleted from either
file without the doc being revisited) is proven to flip it too, in the
other direction -- before the real, unmutated doc and real, unmutated
test files are proven to pass clean today.
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DOC_PATH = os.path.join(REPO_ROOT, "oracle", "SCOPES.md")
ORACLE_ENGINE_TESTS_DIR = os.path.join(REPO_ROOT, "oracle", "oracle_engine", "tests")

CADENCE_TEST_FILE = os.path.join(ORACLE_ENGINE_TESTS_DIR, "test_subscriber_cadence.py")
AUTOGRADE_TEST_FILE = os.path.join(ORACLE_ENGINE_TESTS_DIR, "test_subscriber_autograde.py")

# The doc's own sentence, matched structurally -- never a second hand-typed
# "34". Anchored on the function name so a future reword of the surrounding
# prose (but not the number) still matches.
_CLAIM_RE = re.compile(
    r"`fetch_subscriber_count`\s+is fully built and tested \((\d+) tests, all green\)"
)


def _read_doc(path: str = DOC_PATH) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def claimed_subscriber_test_count(doc_text: str) -> int:
    """Live-extracts the number `oracle/SCOPES.md`'s subscriber-cadence
    BLOCKED paragraph claims for "fully built and tested". Raises if the
    sentence is missing or reworded past what the regex can still find --
    an honest failure, never a silent pass-through."""
    match = _CLAIM_RE.search(doc_text)
    if match is None:
        raise AssertionError(
            "could not find the 'fetch_subscriber_count ... fully built and "
            "tested (N tests, all green)' sentence in the supplied doc text"
        )
    return int(match.group(1))


def _load_module_from_path(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _live_test_count(path: str, module_name: str) -> int:
    mod = _load_module_from_path(module_name, path)
    suite = unittest.defaultTestLoader.loadTestsFromModule(mod)
    return suite.countTestCases()


def real_subscriber_test_count() -> int:
    """The REAL, live count of test methods across the two test files the
    doc's own claim is about -- structural (unittest's own loader walking
    real `TestCase` classes), never a second hand-typed sum."""
    cadence_count = _live_test_count(CADENCE_TEST_FILE, "_subscriber_cadence_count_check")
    autograde_count = _live_test_count(AUTOGRADE_TEST_FILE, "_subscriber_autograde_count_check")
    return cadence_count + autograde_count


def check_subscriber_test_count_claim(doc_text: str, real_count: int) -> dict:
    """The reusable checker both the real assertion and the mutation tests
    below run through -- so a mutation genuinely proves the SAME code path
    bites, not a lookalike copy of it."""
    claimed = claimed_subscriber_test_count(doc_text)
    return {"clean": claimed == real_count, "claimed": claimed, "real": real_count}


class RealClaimCrossCheckedAgainstLiveTestsCase(unittest.TestCase):
    def test_claimed_count_is_extracted_structurally_not_hardcoded(self):
        # Never re-typed as a literal "34" anywhere in this test file's own
        # assertions -- only ever compared to the live-computed total below.
        claimed = claimed_subscriber_test_count(_read_doc())
        self.assertIsInstance(claimed, int)
        self.assertGreater(claimed, 0)

    def test_real_test_count_is_computed_structurally_not_hardcoded(self):
        real = real_subscriber_test_count()
        self.assertIsInstance(real, int)
        self.assertGreater(real, 0)

    def test_docs_claimed_subscriber_test_count_matches_the_real_live_total(self):
        result = check_subscriber_test_count_claim(_read_doc(), real_subscriber_test_count())
        self.assertTrue(
            result["clean"],
            f"oracle/SCOPES.md claims {result['claimed']} subscriber-cadence "
            f"tests but the real live total across test_subscriber_cadence.py "
            f"+ test_subscriber_autograde.py is {result['real']}",
        )

    def test_regression_pin_todays_real_total_is_46(self):
        # Named so a future test added/removed from either file trips this
        # pin FIRST, distinct from (and in addition to) the doc cross-check
        # above -- exactly task 149's own "regression pin" discipline. Moved
        # 34 -> 36 by task 186's own two new test_subscriber_cadence.py
        # cases (test_rejects_zero_horizon_hours/test_rejects_negative_horizon_hours),
        # 36 -> 38 by task 231's own two new test_subscriber_cadence.py
        # cases (test_non_utc_aware_now_still_targets_the_true_utc_instant/
        # test_utc_now_unaffected_by_the_normalization), then 38 -> 42 by
        # task 270's own four new test_subscriber_cadence.py malformed-line
        # guard cases (test_load_snapshots_marks_a_malformed_line_instead_of_raising/
        # test_raises_tampered_error_on_a_malformed_line_instead_of_crashing x2/
        # test_a_valid_lookup_after_a_malformed_earlier_line_still_refuses), then
        # 42 -> 43 by task 296's own one new test_subscriber_autograde.py
        # schema-mismatched-prior-grade guard case
        # (test_a_schema_mismatched_prior_grade_is_ignored_not_raised), then
        # 43 -> 44 by task 325's own 26-file autograde-guard sweep's one new
        # test_subscriber_autograde.py case
        # (test_a_non_dict_predict_payload_is_skipped_not_raised) -- the doc's
        # own count claim went un-bumped past a live `dawn-run` failure
        # (#563/#564) until task 326 caught it, not a routine sweep. Then
        # 44 -> 46 by task 349's own two new test_subscriber_cadence.py
        # valid-JSON-non-dict guard cases
        # (test_load_snapshots_marks_a_valid_json_non_dict_line_as_malformed/
        # test_a_valid_json_non_dict_snapshot_line_refuses_not_crashes) -- the
        # doc's own count claim went un-bumped past a live `dawn-run` failure
        # (#598) until task 350 caught it, not a routine sweep.
        self.assertEqual(real_subscriber_test_count(), 46)


class MutationProvesTheCheckerBitesCase(unittest.TestCase):
    """Task 135-149's own before/after discipline: prove the checker
    actually flags a real drift in either direction, not just that it
    happens to pass today."""

    def test_checker_flags_a_doc_side_drift_wrong_number_in_the_sentence(self):
        real_doc = _read_doc()
        real_count = real_subscriber_test_count()

        # Sanity: the real, unmutated doc passes clean first.
        self.assertTrue(check_subscriber_test_count_claim(real_doc, real_count)["clean"])

        mutated_doc = _CLAIM_RE.sub(
            lambda m: m.group(0).replace(m.group(1), str(int(m.group(1)) + 1), 1),
            real_doc,
        )
        self.assertNotEqual(mutated_doc, real_doc)

        result = check_subscriber_test_count_claim(mutated_doc, real_count)
        self.assertFalse(result["clean"])
        self.assertEqual(result["claimed"], real_count + 1)
        self.assertEqual(result["real"], real_count)

    def test_checker_flags_a_code_side_drift_a_test_quietly_removed(self):
        # Simulates the other direction: a test method deleted from either
        # live file without oracle/SCOPES.md's prose ever being revisited.
        # Never mutates the real files on disk -- only the number handed to
        # the same checker function the real test above uses.
        real_doc = _read_doc()
        claimed = claimed_subscriber_test_count(real_doc)
        shrunk_real_count = real_subscriber_test_count() - 1

        result = check_subscriber_test_count_claim(real_doc, shrunk_real_count)
        self.assertFalse(result["clean"])
        self.assertEqual(result["claimed"], claimed)
        self.assertEqual(result["real"], shrunk_real_count)

    def test_checker_raises_on_a_missing_or_reworded_claim_sentence(self):
        mangled_doc = _read_doc().replace("fully built and tested", "fully built and tasted")
        with self.assertRaises(AssertionError):
            claimed_subscriber_test_count(mangled_doc)


if __name__ == "__main__":
    unittest.main()
