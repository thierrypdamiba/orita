"""Task 1311. Proves tools/scopes_md_consent_sync_check.py actually
catches drift between SCOPES.md's own table and consent.py's
REQUIRED_SCOPES -- not just asserts "clean" against today's real file,
which would pass even if the parser silently matched nothing.
"""
import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "fencepost", "seam_engine", "src"))
from seam_engine.consent import REQUIRED_SCOPES  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


smcs = _load(
    "scopes_md_consent_sync_check",
    os.path.join(ROOT, "tools", "scopes_md_consent_sync_check.py"),
)

REAL_SCOPES_PATH = os.path.join(ROOT, "fencepost", "SCOPES.md")

GOOD_TABLE = """
| toolkit | Fencepost uses | Fencepost may NEVER use |
|--|--|--|
| GitHub | GetRepository, ListIssues | CreateFile, MergePullRequest |
| X | GetUserTweets, WhoAmI | PostTweet, ReplyToTweet |
| Gmail (v0.2) | ListEmails, GetEmail | SendEmail, Trash* |
| Slack (proposed) | SearchChannelMessages | PostMessage |
"""

GOOD_REQUIRED = {
    "github": frozenset({"GetRepository", "ListIssues"}),
    "x": frozenset({"GetUserTweets", "WhoAmI"}),
    "gmail": frozenset({"ListEmails", "GetEmail"}),
    "slack": frozenset({"SearchChannelMessages"}),
}


class ParseScopesTableCase(unittest.TestCase):
    def test_parses_every_row_in_file_order(self):
        rows = smcs.parse_scopes_table(GOOD_TABLE)
        self.assertEqual(
            [r.toolkit_key for r in rows], ["github", "x", "gmail", "slack"]
        )

    def test_v02_suffix_is_stripped(self):
        rows = smcs.parse_scopes_table(GOOD_TABLE)
        gmail = next(r for r in rows if r.toolkit_key == "gmail")
        self.assertEqual(gmail.display, "Gmail (v0.2)")

    def test_uses_and_never_use_split_and_stripped(self):
        rows = smcs.parse_scopes_table(GOOD_TABLE)
        github = next(r for r in rows if r.toolkit_key == "github")
        self.assertEqual(github.uses, frozenset({"GetRepository", "ListIssues"}))
        self.assertEqual(
            github.never_use, frozenset({"CreateFile", "MergePullRequest"})
        )

    def test_header_and_separator_rows_are_not_parsed_as_data(self):
        rows = smcs.parse_scopes_table(GOOD_TABLE)
        self.assertNotIn("toolkit", [r.toolkit_key for r in rows])


class FindDriftCase(unittest.TestCase):
    def test_matching_table_and_dict_have_no_drift(self):
        rows = smcs.parse_scopes_table(GOOD_TABLE)
        self.assertEqual(smcs.find_drift(rows, GOOD_REQUIRED), [])

    def test_a_missing_scope_in_scopes_md_is_flagged(self):
        rows = smcs.parse_scopes_table(GOOD_TABLE)
        required = dict(GOOD_REQUIRED)
        required["github"] = frozenset({"GetRepository", "ListIssues", "GetIssue"})
        problems = smcs.find_drift(rows, required)
        self.assertTrue(any("github" in p and "GetIssue" in p for p in problems))

    def test_an_extra_scope_in_scopes_md_is_flagged(self):
        rows = smcs.parse_scopes_table(GOOD_TABLE)
        required = dict(GOOD_REQUIRED)
        required["github"] = frozenset({"GetRepository"})
        problems = smcs.find_drift(rows, required)
        self.assertTrue(any("ListIssues" in p for p in problems))

    def test_a_required_toolkit_missing_from_scopes_md_entirely_is_flagged(self):
        rows = smcs.parse_scopes_table(GOOD_TABLE)
        required = dict(GOOD_REQUIRED)
        required["linear"] = frozenset({"SearchIssueComments"})
        problems = smcs.find_drift(rows, required)
        self.assertTrue(any("linear" in p for p in problems))

    def test_a_row_for_an_unrequired_toolkit_is_flagged(self):
        rows = smcs.parse_scopes_table(GOOD_TABLE)
        rows = list(rows) + [
            smcs.ScopesRow(
                "Notion (proposed)",
                "notion",
                frozenset({"SearchPages"}),
                frozenset({"CreatePage"}),
            )
        ]
        problems = smcs.find_drift(rows, GOOD_REQUIRED)
        self.assertTrue(any("notion" in p for p in problems))

    def test_a_duplicate_toolkit_row_is_flagged(self):
        rows = smcs.parse_scopes_table(GOOD_TABLE)
        rows = list(rows) + [rows[0]]
        problems = smcs.find_drift(rows, GOOD_REQUIRED)
        self.assertTrue(any("more than one SCOPES.md table row" in p for p in problems))

    def test_a_name_in_both_uses_and_never_use_on_one_row_is_flagged(self):
        rows = [
            smcs.ScopesRow(
                "GitHub",
                "github",
                frozenset({"GetRepository", "CreateFile"}),
                frozenset({"CreateFile"}),
            )
        ]
        required = {"github": frozenset({"GetRepository", "CreateFile"})}
        problems = smcs.find_drift(rows, required)
        self.assertTrue(
            any("BOTH" in p and "CreateFile" in p for p in problems)
        )

    def test_required_scope_listed_as_never_use_is_flagged(self):
        rows = [
            smcs.ScopesRow(
                "GitHub", "github", frozenset({"GetRepository"}), frozenset({"GetRepository"})
            )
        ]
        required = {"github": frozenset({"GetRepository"})}
        problems = smcs.find_drift(rows, required)
        self.assertTrue(
            any("REQUIRED_SCOPES requires" in p for p in problems)
        )


class RealLiveStateCase(unittest.TestCase):
    """The actual point: today's real SCOPES.md table really does match
    today's real consent.py, checked structurally, not by re-asserting
    the claim a sixth time by eye."""

    def test_the_real_scopes_doc_matches_the_real_required_scopes(self):
        ok, msg = smcs.check(REAL_SCOPES_PATH)
        self.assertTrue(ok, msg)

    def test_every_required_toolkit_has_exactly_one_real_scopes_row(self):
        with open(REAL_SCOPES_PATH, encoding="utf-8") as f:
            rows = smcs.parse_scopes_table(f.read())
        keys = [r.toolkit_key for r in rows]
        self.assertEqual(set(keys), set(REQUIRED_SCOPES))
        self.assertEqual(len(keys), len(set(keys)))


class CliCase(unittest.TestCase):
    def test_check_on_the_real_scopes_doc_exits_zero(self):
        self.assertEqual(smcs.main(["check", REAL_SCOPES_PATH]), 0)

    def test_missing_file_exits_nonzero(self):
        self.assertEqual(smcs.main(["check", "/nonexistent/path.md"]), 1)

    def test_no_args_exits_with_usage(self):
        self.assertEqual(smcs.main([]), 2)


if __name__ == "__main__":
    unittest.main()
