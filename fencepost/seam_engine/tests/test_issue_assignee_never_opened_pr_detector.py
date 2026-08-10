"""Tests for RECIPES/issue-assignee-never-opened-pr/detector.py's own
detection logic (ROADMAP.md #652) -- the seventy-seventh real recipe: an
issue's own assignee who never opened a pull request that closes the
issue they were assigned.

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this
test exercises the exact module a live scan would import, not a copy.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "issue-assignee-never-opened-pr" / "detector.py"

_spec = importlib.util.spec_from_file_location(
    "seam_engine._recipe_issue_assignee_never_opened_pr_test", DETECTOR_PATH
)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 10, 14, 0, 0, tzinfo=timezone.utc)


def _issue(
    number: int,
    title: str,
    created_at: datetime,
    *,
    state: str = "open",
    assignees: list[str] | None = None,
) -> "detector.Issue":
    return detector.Issue(
        number=number, title=title, state=state,
        assignees=assignees if assignees is not None else ["mortal-a"],
        created_at=created_at,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


def _pull(number: int, author: str, body: str, *, state: str = "open") -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, author=author, body=body,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestComputeGaps:
    def test_an_old_assigned_issue_never_answered_is_surfaced_at_high_confidence(self):
        issue = _issue(801, "Old assignment", datetime(2026, 8, 5, 9, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([issue], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-assignee-never-opened-pr-801"
        assert surfaced[0].confidence == 0.85
        assert surfaced[0].evidence == [issue.url]

    def test_a_recently_assigned_issue_never_answered_is_surfaced_at_low_confidence(self):
        issue = _issue(802, "Fresh assignment", datetime(2026, 8, 10, 10, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([issue], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_an_issue_answered_by_its_own_assignee_is_excluded(self):
        issue = _issue(803, "Answered", datetime(2026, 7, 20, 8, 0, 0, tzinfo=timezone.utc), assignees=["mortal-c"])
        pr = _pull(901, "mortal-c", "Root cause found. Fixes #803")

        surfaced, excluded = detector.compute_gaps([issue], [pr], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "answered-by-assignee-803"

    def test_an_issue_answered_by_a_closed_never_merged_pr_is_still_excluded(self):
        # An abandoned attempt still counts as a real swing taken -- this
        # recipe asks whether the assignee ever opened the channel, not
        # whether opening it succeeded.
        issue = _issue(803, "Answered then abandoned", datetime(2026, 7, 20, 8, 0, 0, tzinfo=timezone.utc), assignees=["mortal-c"])
        pr = _pull(901, "mortal-c", "closes #803", state="closed")

        surfaced, excluded = detector.compute_gaps([issue], [pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "answered-by-assignee-803"

    def test_a_bystanders_pr_closing_the_issue_does_not_exclude_it(self):
        # The whole point of this recipe over good-first-issue-never-
        # referenced: identity matters. Someone else's PR closing the
        # issue is real activity, but it is not the assignee's own answer.
        issue = _issue(806, "Bystander attempt", datetime(2026, 8, 10, 9, 0, 0, tzinfo=timezone.utc), assignees=["mortal-e", "mortal-f"])
        pr = _pull(903, "some-other-mortal", "Took a swing at this. closes #806")

        surfaced, excluded = detector.compute_gaps([issue], [pr], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-assignee-never-opened-pr-806"

    def test_an_assignees_pr_closing_a_different_issue_does_not_exclude_this_one(self):
        issue = _issue(806, "Wrong target", datetime(2026, 8, 10, 9, 0, 0, tzinfo=timezone.utc), assignees=["mortal-f"])
        pr = _pull(902, "mortal-f", "Unrelated: tidies up the README's own footer typo.")

        surfaced, excluded = detector.compute_gaps([issue], [pr], now=_NOW)

        assert len(surfaced) == 1
        assert excluded == []

    def test_an_already_closed_assigned_issue_is_excluded_not_surfaced(self):
        issue = _issue(804, "Already done", datetime(2026, 7, 1, 8, 0, 0, tzinfo=timezone.utc), state="closed", assignees=["mortal-d"])

        surfaced, excluded = detector.compute_gaps([issue], [], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "not-open-804"

    def test_an_issue_with_no_assignees_is_skipped_entirely_not_even_excluded(self):
        issue = _issue(805, "Unassigned", datetime(2026, 7, 15, 8, 0, 0, tzinfo=timezone.utc), assignees=[])

        surfaced, excluded = detector.compute_gaps([issue], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_multiple_surfaced_issues_are_ranked_highest_confidence_first(self):
        old = _issue(801, "Old", datetime(2026, 8, 5, 9, 0, 0, tzinfo=timezone.utc))
        recent = _issue(802, "Recent", datetime(2026, 8, 10, 10, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([old, recent], [], now=_NOW)

        assert excluded == []
        assert [g.slug for g in surfaced] == [
            "issue-assignee-never-opened-pr-801",
            "issue-assignee-never-opened-pr-802",
        ]


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "issue-assignee-never-opened-pr-801"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recent_issues_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "issue-assignee-never-opened-pr-802" in tail_slugs
        assert "issue-assignee-never-opened-pr-806" in tail_slugs

    def test_the_shipped_fixture_excludes_answered_and_closed(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "answered-by-assignee-803" in excluded_slugs
        assert "not-open-804" in excluded_slugs

    def test_the_shipped_fixture_never_names_the_unassigned_issue_anywhere(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = (
            {g["slug"] for g in result["tail"]}
            | {g["slug"] for g in result["excluded"]}
            | ({result["primary_gap"]["slug"]} if result["primary_gap"] else set())
        )
        assert not any("805" in slug for slug in all_slugs)


class TestLoaders:
    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pulls)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_issues_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issues(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pulls_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pulls(bad_file)
