"""Task 1057. Proves tools/consent_template_scope_check.py actually catches
drift between consent.py's REQUIRED_SCOPES and the issue template's
scope-confirm table -- not just asserts "clean" against today's files,
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


ctsc = _load(
    "consent_template_scope_check",
    os.path.join(ROOT, "tools", "consent_template_scope_check.py"),
)

REAL_TEMPLATE = os.path.join(ROOT, ".github", "ISSUE_TEMPLATE", "point-fencepost.md")

GOOD_TABLE = """
| toolkit | paste this back, verbatim, to confirm it |
|--|--|
| GitHub | `GetRepository, ListIssues` |
| X | `GetUserTweets, WhoAmI` |
| Google Calendar | `ListEvents, GetEvent` |
| Slack (proposed) | `SearchChannelMessages` |
"""

GOOD_REQUIRED = {
    "github": frozenset({"GetRepository", "ListIssues"}),
    "x": frozenset({"GetUserTweets", "WhoAmI"}),
    "google_calendar": frozenset({"ListEvents", "GetEvent"}),
    "slack": frozenset({"SearchChannelMessages"}),
}


class NormalizeDisplayNameCase(unittest.TestCase):
    def test_plain_name_lowercases(self):
        self.assertEqual(ctsc.normalize_display_name("GitHub"), "github")

    def test_multiword_name_gets_underscored(self):
        self.assertEqual(ctsc.normalize_display_name("Google Calendar"), "google_calendar")

    def test_proposed_suffix_is_stripped(self):
        self.assertEqual(ctsc.normalize_display_name("Slack (proposed)"), "slack")
        self.assertEqual(ctsc.normalize_display_name("Linear (Proposed)"), "linear")

    def test_a_future_toolkit_normalizes_with_no_code_change(self):
        # The whole point: a brand new toolkit row needs no matching edit
        # to this module to normalize correctly.
        self.assertEqual(ctsc.normalize_display_name("Notion (proposed)"), "notion")


class ParseTemplateScopesCase(unittest.TestCase):
    def test_parses_every_row_in_file_order(self):
        rows = ctsc.parse_template_scopes(GOOD_TABLE)
        self.assertEqual([r.toolkit_key for r in rows], ["github", "x", "google_calendar", "slack"])

    def test_scopes_split_and_stripped(self):
        rows = ctsc.parse_template_scopes(GOOD_TABLE)
        github = next(r for r in rows if r.toolkit_key == "github")
        self.assertEqual(github.scopes, frozenset({"GetRepository", "ListIssues"}))

    def test_header_and_separator_rows_are_not_parsed_as_data(self):
        rows = ctsc.parse_template_scopes(GOOD_TABLE)
        self.assertNotIn("toolkit", [r.toolkit_key for r in rows])


class FindDriftCase(unittest.TestCase):
    def test_matching_table_and_dict_have_no_drift(self):
        rows = ctsc.parse_template_scopes(GOOD_TABLE)
        self.assertEqual(ctsc.find_drift(rows, GOOD_REQUIRED), [])

    def test_a_missing_scope_name_in_the_template_is_flagged(self):
        rows = ctsc.parse_template_scopes(GOOD_TABLE)
        required = dict(GOOD_REQUIRED)
        required["github"] = frozenset({"GetRepository", "ListIssues", "GetIssue"})
        problems = ctsc.find_drift(rows, required)
        self.assertEqual(len(problems), 1)
        self.assertIn("github", problems[0])
        self.assertIn("GetIssue", problems[0])

    def test_an_extra_scope_name_in_the_template_is_flagged(self):
        rows = ctsc.parse_template_scopes(GOOD_TABLE)
        required = dict(GOOD_REQUIRED)
        required["github"] = frozenset({"GetRepository"})
        problems = ctsc.find_drift(rows, required)
        self.assertEqual(len(problems), 1)
        self.assertIn("ListIssues", problems[0])

    def test_a_required_toolkit_missing_from_the_template_entirely_is_flagged(self):
        rows = ctsc.parse_template_scopes(GOOD_TABLE)
        required = dict(GOOD_REQUIRED)
        required["gmail"] = frozenset({"ListEmails"})
        problems = ctsc.find_drift(rows, required)
        self.assertTrue(any("gmail" in p for p in problems))

    def test_a_template_row_for_an_unrequired_toolkit_is_flagged(self):
        rows = ctsc.parse_template_scopes(GOOD_TABLE)
        rows = list(rows) + [
            ctsc.TemplateRow("Notion (proposed)", "notion", frozenset({"SearchPages"}))
        ]
        problems = ctsc.find_drift(rows, GOOD_REQUIRED)
        self.assertTrue(any("notion" in p for p in problems))

    def test_a_duplicate_toolkit_row_is_flagged(self):
        rows = ctsc.parse_template_scopes(GOOD_TABLE)
        rows = list(rows) + [rows[0]]
        problems = ctsc.find_drift(rows, GOOD_REQUIRED)
        self.assertTrue(any("more than one template row" in p for p in problems))


class RealLiveStateCase(unittest.TestCase):
    """The actual point: today's real template really does match today's
    real consent.py, checked structurally, not by re-asserting the claim."""

    def test_the_real_template_matches_the_real_required_scopes(self):
        ok, msg = ctsc.check(REAL_TEMPLATE)
        self.assertTrue(ok, msg)

    def test_every_required_toolkit_has_exactly_one_real_template_row(self):
        with open(REAL_TEMPLATE, encoding="utf-8") as f:
            rows = ctsc.parse_template_scopes(f.read())
        keys = [r.toolkit_key for r in rows]
        self.assertEqual(set(keys), set(REQUIRED_SCOPES))
        self.assertEqual(len(keys), len(set(keys)))


class CliCase(unittest.TestCase):
    def test_check_on_the_real_template_exits_zero(self):
        self.assertEqual(ctsc.main(["check", REAL_TEMPLATE]), 0)

    def test_missing_file_exits_nonzero(self):
        self.assertEqual(ctsc.main(["check", "/nonexistent/path.md"]), 1)

    def test_no_args_exits_with_usage(self):
        self.assertEqual(ctsc.main([]), 2)


if __name__ == "__main__":
    unittest.main()
