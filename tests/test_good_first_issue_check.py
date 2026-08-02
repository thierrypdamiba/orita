"""Proves tools/good_first_issue_check.py correctly reads whether the
`good first issue` label is currently attached to any open issue: clean
when stocked, empty when not, tolerant of case/whitespace, never fooled by
a near-miss label name, and `None`-safe when no live read was held.
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


gfic = _load("good_first_issue_check", os.path.join(ROOT, "tools", "good_first_issue_check.py"))


class TestComputeGoodFirstIssueState(unittest.TestCase):
    def test_empty_list_is_zero(self):
        state = gfic.compute_good_first_issue_state([])
        self.assertEqual(state, {"count": 0, "issue_numbers": []})

    def test_no_matching_labels_is_zero(self):
        issues = [{"number": 1, "labels": ["bug"]}, {"number": 2, "labels": ["question"]}]
        state = gfic.compute_good_first_issue_state(issues)
        self.assertEqual(state["count"], 0)

    def test_one_matching_label_is_found(self):
        issues = [{"number": 1, "labels": ["bug"]}, {"number": 7, "labels": ["good first issue"]}]
        state = gfic.compute_good_first_issue_state(issues)
        self.assertEqual(state, {"count": 1, "issue_numbers": [7]})

    def test_multiple_matches_are_all_found_and_sorted(self):
        issues = [
            {"number": 9, "labels": ["good first issue"]},
            {"number": 3, "labels": ["good first issue", "documentation"]},
        ]
        state = gfic.compute_good_first_issue_state(issues)
        self.assertEqual(state, {"count": 2, "issue_numbers": [3, 9]})

    def test_matching_is_case_insensitive(self):
        issues = [{"number": 1, "labels": ["Good First Issue"]}]
        state = gfic.compute_good_first_issue_state(issues)
        self.assertEqual(state["count"], 1)

    def test_matching_tolerates_surrounding_whitespace(self):
        issues = [{"number": 1, "labels": [" good first issue "]}]
        state = gfic.compute_good_first_issue_state(issues)
        self.assertEqual(state["count"], 1)

    def test_near_miss_label_does_not_falsely_match(self):
        """A label that merely contains the phrase, or negates it, must
        never count -- exact match only, the same discipline
        rider_check.py's siblings hold for their own cue words."""
        issues = [
            {"number": 1, "labels": ["not a good first issue"]},
            {"number": 2, "labels": ["good first issue candidate"]},
        ]
        state = gfic.compute_good_first_issue_state(issues)
        self.assertEqual(state["count"], 0)

    def test_missing_labels_key_does_not_crash(self):
        state = gfic.compute_good_first_issue_state([{"number": 1}])
        self.assertEqual(state["count"], 0)


class TestCheckGoodFirstIssues(unittest.TestCase):
    def test_none_input_returns_none(self):
        self.assertIsNone(gfic.check_good_first_issues(None))

    def test_empty_shelf_is_not_clean(self):
        result = gfic.check_good_first_issues([{"number": 1, "labels": ["bug"]}])
        self.assertFalse(result["clean"])
        self.assertEqual(result["count"], 0)

    def test_stocked_shelf_is_clean(self):
        result = gfic.check_good_first_issues([{"number": 5, "labels": ["good first issue"]}])
        self.assertTrue(result["clean"])
        self.assertEqual(result["issue_numbers"], [5])


class TestFormatGoodFirstIssues(unittest.TestCase):
    def test_format_none(self):
        text = gfic.format_good_first_issues(None)
        self.assertIn("not read this hour", text)

    def test_format_clean(self):
        text = gfic.format_good_first_issues({"clean": True, "count": 1, "issue_numbers": [5]})
        self.assertIn("stocked", text)
        self.assertIn("[5]", text)

    def test_format_empty_names_the_charter_clause(self):
        text = gfic.format_good_first_issues({"clean": False, "count": 0, "issue_numbers": []})
        self.assertIn("EMPTY", text)
        self.assertIn("good-first-issues stocked", text)


class TestCli(unittest.TestCase):
    def test_check_command_exits_zero_when_stocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "issues.json")
            with open(path, "w") as f:
                json.dump([{"number": 1, "labels": ["good first issue"]}], f)
            rc = gfic.main(["good_first_issue_check.py", "check", path])
        self.assertEqual(rc, 0)

    def test_check_command_exits_nonzero_when_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "issues.json")
            with open(path, "w") as f:
                json.dump([{"number": 1, "labels": ["bug"]}], f)
            rc = gfic.main(["good_first_issue_check.py", "check", path])
        self.assertEqual(rc, 1)

    def test_non_list_json_raises_arg_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "issues.json")
            with open(path, "w") as f:
                json.dump({"not": "a list"}, f)
            with self.assertRaises(gfic.GoodFirstIssueArgError):
                gfic.main(["good_first_issue_check.py", "check", path])


if __name__ == "__main__":
    unittest.main()
