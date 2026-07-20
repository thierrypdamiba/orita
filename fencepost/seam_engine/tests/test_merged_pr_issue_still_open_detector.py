"""Tests for RECIPES/merged-pr-issue-still-open/detector.py's own detection
logic (ROADMAP.md #183) -- no test file exercised `compute_gaps`/
`_closed_issue_numbers` directly before this one; test_recipes.py only
validates the recipe manifest schema, never the business logic beneath it.

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this test
exercises the exact module a live scan would import, not a copy.
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "merged-pr-issue-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_merged_pr_issue_still_open_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)


def _pull(body: str, merged_at: datetime = datetime(2026, 7, 15, 0, 0, 0, tzinfo=timezone.utc)) -> "detector.MergedPull":
    return detector.MergedPull(
        id="PR-1", title="Some fix", number=100, body=body, merged_at=merged_at,
        url="https://github.com/example/example-repo/pull/100",
    )


def _issue(number: int, state: str) -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestClosedIssueNumbers:
    def test_a_single_closing_keyword_returns_one_number(self):
        assert detector._closed_issue_numbers("Closes #55") == [55]

    def test_two_closing_keywords_return_both_numbers(self):
        assert detector._closed_issue_numbers("This closes #1 and fixes #2") == [1, 2]

    def test_no_closing_keyword_returns_an_empty_list(self):
        assert detector._closed_issue_numbers("No linked issue, docs only.") == []


class TestComputeGapsMultiIssuePr:
    def test_a_pr_naming_two_closing_keywords_still_flags_the_one_left_open(self):
        # Issue #1 is already closed; issue #2 is still open and stale
        # (well past _STALE_HOURS). Before the fix, `_closed_issue_number`'s
        # `.search()` only ever saw #1, so the PR was excluded as
        # "already closed" and #2's real, still-open gap was never surfaced
        # at all -- reproduced live against the pre-fix code before writing
        # this test.
        pr = _pull("This closes #1 and fixes #2", merged_at=datetime(2026, 7, 15, 0, 0, 0, tzinfo=timezone.utc))
        issues = [_issue(1, "closed"), _issue(2, "open")]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        surfaced_slugs = {g.slug for g in surfaced}
        excluded_slugs = {g.slug for g in excluded}
        assert "merged-pr-issue-still-open-100-2" in surfaced_slugs
        assert "issue-already-closed-100-1" in excluded_slugs
        assert not any("2" in s and "closed" in s for s in excluded_slugs)

    def test_both_issues_open_and_stale_surfaces_both_as_distinct_candidates(self):
        pr = _pull("Closes #1 and fixes #2", merged_at=datetime(2026, 7, 15, 0, 0, 0, tzinfo=timezone.utc))
        issues = [_issue(1, "open"), _issue(2, "open")]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert excluded == []
        surfaced_slugs = sorted(g.slug for g in surfaced)
        assert surfaced_slugs == ["merged-pr-issue-still-open-100-1", "merged-pr-issue-still-open-100-2"]

    def test_single_issue_pr_behavior_is_unchanged(self):
        pr = _pull("Closes #55", merged_at=datetime(2026, 7, 15, 0, 0, 0, tzinfo=timezone.utc))
        issues = [_issue(55, "open")]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "merged-pr-issue-still-open-100-55"
