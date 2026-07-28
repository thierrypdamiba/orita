"""Tests for RECIPES/issue-closed-pr-still-open/detector.py's own detection
logic (ROADMAP.md #373) -- the sixth real recipe, the mirror image of
merged-pr-issue-still-open (task 108/183): a still-OPEN PR names a closing
keyword for an issue that closed anyway, through some other route.

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this test
exercises the exact module a live scan would import, not a copy.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "issue-closed-pr-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_issue_closed_pr_still_open_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 25, 12, 0, 0, tzinfo=timezone.utc)


def _pull(
    body: str,
    state: str = "open",
    opened_at: datetime = datetime(2026, 7, 19, 0, 0, 0, tzinfo=timezone.utc),
) -> "detector.OpenPull":
    return detector.OpenPull(
        id="PR-1", title="Some fix", number=100, body=body, state=state,
        opened_at=opened_at, url="https://github.com/example/example-repo/pull/100",
    )


def _issue(number: int, state: str, closed_at: datetime | None = None) -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state, closed_at=closed_at,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestNamedIssueNumbers:
    def test_a_single_closing_keyword_returns_one_number(self):
        assert detector._named_issue_numbers("Closes #55") == [55]

    def test_two_closing_keywords_return_both_numbers(self):
        assert detector._named_issue_numbers("This closes #1 and fixes #2") == [1, 2]

    def test_no_closing_keyword_returns_an_empty_list(self):
        assert detector._named_issue_numbers("No linked issue, docs only.") == []


class TestComputeGaps:
    def test_a_stale_closed_issue_is_surfaced_at_high_confidence(self):
        pr = _pull("Closes #1")
        issues = [_issue(1, "closed", closed_at=datetime(2026, 7, 19, 0, 0, 0, tzinfo=timezone.utc))]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-closed-pr-still-open-100-1"
        assert surfaced[0].confidence == 0.85

    def test_a_recently_closed_issue_is_surfaced_at_low_confidence(self):
        pr = _pull("Fixes #1")
        issues = [_issue(1, "closed", closed_at=_NOW - timedelta(hours=4))]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_still_open_named_issue_is_excluded_not_surfaced(self):
        pr = _pull("Resolves #1")
        issues = [_issue(1, "open")]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "issue-still-open-100-1"

    def test_a_pr_with_no_closing_keyword_produces_no_candidate_at_all(self):
        pr = _pull("Cosmetic only, no linked issue.")
        issues = [_issue(1, "closed", closed_at=datetime(2026, 7, 19, 0, 0, 0, tzinfo=timezone.utc))]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-closing-keyword-100"

    def test_a_merged_pr_is_never_considered_at_all(self):
        # This recipe's seam is specifically a PR that never merged (so
        # GitHub's auto-close never had a trigger). A merged PR is
        # merged-pr-issue-still-open's seam, not this one's.
        pr = _pull("Closes #1", state="merged")
        issues = [_issue(1, "closed", closed_at=datetime(2026, 7, 19, 0, 0, 0, tzinfo=timezone.utc))]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_pr_naming_two_closing_keywords_judges_each_issue_independently(self):
        pr = _pull("This closes #1 and fixes #2")
        issues = [
            _issue(1, "closed", closed_at=datetime(2026, 7, 19, 0, 0, 0, tzinfo=timezone.utc)),
            _issue(2, "open"),
        ]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        surfaced_slugs = {g.slug for g in surfaced}
        excluded_slugs = {g.slug for g in excluded}
        assert "issue-closed-pr-still-open-100-1" in surfaced_slugs
        assert "issue-still-open-100-2" in excluded_slugs

    def test_an_unrecognized_issue_number_is_excluded_not_surfaced(self):
        pr = _pull("Closes #999")
        issues = [_issue(1, "closed", closed_at=datetime(2026, 7, 19, 0, 0, 0, tzinfo=timezone.utc))]

        surfaced, excluded = detector.compute_gaps([pr], issues, now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "issue-still-open-100-999"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "issue-closed-pr-still-open-601-501"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recently_closed_issue_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "issue-closed-pr-still-open-602-502" in tail_slugs

    def test_the_shipped_fixture_excludes_the_still_open_named_issue(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "issue-still-open-603-503" in excluded_slugs
        assert "no-closing-keyword-604" in excluded_slugs


class TestLoaders:
    """load_pulls/load_issues -- mirrors merged-pr-issue-still-open's own
    _load_rows guard against syntactically valid but non-list JSON (task
    358's closed campaign), applied here fresh since this is a new loader,
    not a shared one."""

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.OpenPull) for p in pulls)

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pulls_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pulls(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_issues_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issues(bad_file)
