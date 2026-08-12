"""Task 145. Proves tools/consent_grant_log.py is the durable, gate-verified
memory of real human consent grants: it never records anything the gate
itself would refuse, it is append-only, and its distinct-toolkit count is
computed structurally off real recorded entries -- never a second
hand-typed number.
"""
import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "fencepost", "seam_engine", "src"))
from seam_engine.consent import REQUIRED_SCOPES, ConsentRequiredError  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


cgl = _load("consent_grant_log", os.path.join(ROOT, "tools", "consent_grant_log.py"))

_REAL_ISSUE = "https://github.com/thierrypdamiba/orita/issues/9"


class GateEnforcementCase(unittest.TestCase):
    """record_grant re-runs the real gate itself -- a caller cannot durably
    claim a consent the gate would refuse."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)
        self.log_path = os.path.join(self.tmp, "log.jsonl")

    def test_a_real_valid_grant_is_recorded(self):
        entry = cgl.record_grant(
            "thierrypdamiba",
            "github",
            _REAL_ISSUE,
            REQUIRED_SCOPES["github"],
            "2026-07-19T04:30:00Z",
            path=self.log_path,
        )
        self.assertEqual(entry["toolkit"], "github")
        self.assertTrue(os.path.exists(self.log_path))
        self.assertEqual(cgl.real_distinct_toolkit_count(self.log_path), 1)

    def test_an_under_confirmed_scope_set_is_refused_and_writes_nothing(self):
        partial = frozenset(list(REQUIRED_SCOPES["github"])[:2])
        with self.assertRaises(ConsentRequiredError):
            cgl.record_grant(
                "thierrypdamiba", "github", _REAL_ISSUE, partial, "2026-07-19T04:30:00Z", path=self.log_path
            )
        self.assertFalse(os.path.exists(self.log_path))

    def test_a_non_public_issue_url_is_refused_and_writes_nothing(self):
        with self.assertRaises(ConsentRequiredError):
            cgl.record_grant(
                "thierrypdamiba",
                "github",
                "not-a-real-url",
                REQUIRED_SCOPES["github"],
                "2026-07-19T04:30:00Z",
                path=self.log_path,
            )
        self.assertFalse(os.path.exists(self.log_path))

    def test_a_blank_human_is_refused_and_writes_nothing(self):
        # ROADMAP: enforce_consent_gate now refuses a blank/whitespace human
        # identity -- record_grant re-runs that same gate, so a caller can
        # never durably count an anonymous grant toward
        # real_distinct_human_count(), STRATEGY.md's own connected-users
        # metric.
        with self.assertRaises(ConsentRequiredError):
            cgl.record_grant(
                "", "github", _REAL_ISSUE, REQUIRED_SCOPES["github"], "2026-07-19T04:30:00Z", path=self.log_path
            )
        self.assertFalse(os.path.exists(self.log_path))

    def test_an_unknown_toolkit_is_refused_and_writes_nothing(self):
        with self.assertRaises(ConsentRequiredError):
            cgl.record_grant(
                "thierrypdamiba",
                "slack",
                _REAL_ISSUE,
                frozenset({"ListChannels"}),
                "2026-07-19T04:30:00Z",
                path=self.log_path,
            )
        self.assertFalse(os.path.exists(self.log_path))


class AppendOnlyAndCountingCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)
        self.log_path = os.path.join(self.tmp, "log.jsonl")

    def test_never_checked_log_counts_zero_not_error(self):
        never_written = os.path.join(self.tmp, "does-not-exist.jsonl")
        self.assertEqual(cgl.real_distinct_toolkit_count(never_written), 0)

    def test_two_grants_same_toolkit_count_as_one_distinct_toolkit(self):
        cgl.record_grant(
            "alice", "github", _REAL_ISSUE, REQUIRED_SCOPES["github"], "2026-07-19T01:00:00Z", path=self.log_path
        )
        cgl.record_grant(
            "bob", "github", _REAL_ISSUE, REQUIRED_SCOPES["github"], "2026-07-19T02:00:00Z", path=self.log_path
        )
        self.assertEqual(cgl.real_distinct_toolkit_count(self.log_path), 1)

    def test_two_grants_different_toolkits_count_as_two(self):
        cgl.record_grant(
            "alice", "github", _REAL_ISSUE, REQUIRED_SCOPES["github"], "2026-07-19T01:00:00Z", path=self.log_path
        )
        cgl.record_grant(
            "alice", "x", _REAL_ISSUE, REQUIRED_SCOPES["x"], "2026-07-19T02:00:00Z", path=self.log_path
        )
        self.assertEqual(cgl.real_distinct_toolkit_count(self.log_path), 2)

    def test_appending_never_truncates_a_prior_line(self):
        cgl.record_grant(
            "alice", "github", _REAL_ISSUE, REQUIRED_SCOPES["github"], "2026-07-19T01:00:00Z", path=self.log_path
        )
        with open(self.log_path, encoding="utf-8") as f:
            first_pass_lines = f.readlines()
        cgl.record_grant(
            "alice", "x", _REAL_ISSUE, REQUIRED_SCOPES["x"], "2026-07-19T02:00:00Z", path=self.log_path
        )
        with open(self.log_path, encoding="utf-8") as f:
            second_pass_lines = f.readlines()
        self.assertEqual(second_pass_lines[: len(first_pass_lines)], first_pass_lines)
        self.assertEqual(len(second_pass_lines), len(first_pass_lines) + 1)


class TamperedLogCase(unittest.TestCase):
    """A line that is not even valid JSON any more must not crash the
    reader, but the toolkit count must still refuse rather than guess
    past it (tasks 238-241's sibling convention)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)
        self.log_path = os.path.join(self.tmp, "log.jsonl")

    def test_a_malformed_line_does_not_crash_entries(self):
        cgl.record_grant(
            "alice", "github", _REAL_ISSUE, REQUIRED_SCOPES["github"], "2026-07-19T01:00:00Z", path=self.log_path
        )
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write("not valid json at all\n")
        entries = cgl._entries(self.log_path)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[1]["_malformed"])

    def test_a_malformed_line_makes_the_toolkit_count_refuse(self):
        cgl.record_grant(
            "alice", "github", _REAL_ISSUE, REQUIRED_SCOPES["github"], "2026-07-19T01:00:00Z", path=self.log_path
        )
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write("not valid json at all\n")
        with self.assertRaises(cgl.ConsentLogTamperedError):
            cgl.real_distinct_toolkit_count(self.log_path)

    def test_a_clean_log_is_unaffected_by_the_new_guard(self):
        cgl.record_grant(
            "alice", "github", _REAL_ISSUE, REQUIRED_SCOPES["github"], "2026-07-19T01:00:00Z", path=self.log_path
        )
        cgl.record_grant(
            "alice", "x", _REAL_ISSUE, REQUIRED_SCOPES["x"], "2026-07-19T02:00:00Z", path=self.log_path
        )
        self.assertEqual(cgl.real_distinct_toolkit_count(self.log_path), 2)

    def test_a_non_dict_json_line_does_not_crash_entries(self):
        """Task 313: a line that parses cleanly to a non-dict JSON value
        (bare number, null, list, string) used to slip past the
        _malformed guard entirely and crash distinct_toolkits()'s
        e.get("_malformed") with an uncaught AttributeError -- the same
        boundary case tasks 309-312 already fixed in their four
        siblings."""
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write("5\n")
        entries = cgl._entries(self.log_path)
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0]["_malformed"])

    def test_a_non_dict_json_line_makes_the_toolkit_count_refuse(self):
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write("5\n")
        with self.assertRaises(cgl.ConsentLogTamperedError):
            cgl.real_distinct_toolkit_count(self.log_path)


class RealLiveStateCase(unittest.TestCase):
    """The real point: as of this task, zero real human consents have
    ever been recorded anywhere in this town -- the actual town log
    (HAND/consent-grants-log.jsonl) has never been written, so the real,
    honest ground truth this hour is 0, not the 2 metrics.jsonl has been
    claiming."""

    def test_the_real_town_log_has_never_been_written(self):
        self.assertFalse(os.path.exists(cgl.LOG))

    def test_the_real_ground_truth_is_honestly_zero(self):
        self.assertEqual(cgl.real_distinct_toolkit_count(), 0)

    def test_the_real_connected_user_ground_truth_is_also_honestly_zero(self):
        self.assertEqual(cgl.real_distinct_human_count(), 0)


class DistinctHumanCountCase(unittest.TestCase):
    """Task 412: `distinct_humans`/`real_distinct_human_count` are
    STRATEGY.md's "'Connect your own' OAuth completions across users"
    row's actual ground truth -- distinct from `distinct_toolkits`
    because one human confirming two toolkits is one connected USER, not
    two toolkits' worth of users."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)
        self.log_path = os.path.join(self.tmp, "log.jsonl")

    def test_never_checked_log_counts_zero_humans_not_error(self):
        never_written = os.path.join(self.tmp, "does-not-exist.jsonl")
        self.assertEqual(cgl.real_distinct_human_count(never_written), 0)

    def test_one_human_two_toolkits_counts_as_one_connected_user(self):
        cgl.record_grant(
            "alice", "github", _REAL_ISSUE, REQUIRED_SCOPES["github"], "2026-07-19T01:00:00Z", path=self.log_path
        )
        cgl.record_grant(
            "alice", "x", _REAL_ISSUE, REQUIRED_SCOPES["x"], "2026-07-19T02:00:00Z", path=self.log_path
        )
        self.assertEqual(cgl.real_distinct_human_count(self.log_path), 1)
        # The sibling toolkit count, over the identical log, disagrees on purpose.
        self.assertEqual(cgl.real_distinct_toolkit_count(self.log_path), 2)

    def test_two_humans_same_toolkit_counts_as_two_connected_users(self):
        cgl.record_grant(
            "alice", "github", _REAL_ISSUE, REQUIRED_SCOPES["github"], "2026-07-19T01:00:00Z", path=self.log_path
        )
        cgl.record_grant(
            "bob", "github", _REAL_ISSUE, REQUIRED_SCOPES["github"], "2026-07-19T02:00:00Z", path=self.log_path
        )
        self.assertEqual(cgl.real_distinct_human_count(self.log_path), 2)
        self.assertEqual(cgl.real_distinct_toolkit_count(self.log_path), 1)

    def test_a_malformed_line_makes_the_human_count_refuse(self):
        cgl.record_grant(
            "alice", "github", _REAL_ISSUE, REQUIRED_SCOPES["github"], "2026-07-19T01:00:00Z", path=self.log_path
        )
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write("not valid json at all\n")
        with self.assertRaises(cgl.ConsentLogTamperedError):
            cgl.real_distinct_human_count(self.log_path)


if __name__ == "__main__":
    unittest.main()
