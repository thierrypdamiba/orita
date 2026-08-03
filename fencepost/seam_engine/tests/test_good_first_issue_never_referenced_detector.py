"""Tests for RECIPES/good-first-issue-never-referenced/detector.py's own
detection logic (ROADMAP.md #499) -- the thirty-eighth real recipe: an
issue labeled 'good first issue' that no pull request has ever named
through a real GitHub closing keyword.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "good-first-issue-never-referenced" / "detector.py"

_spec = importlib.util.spec_from_file_location(
    "seam_engine._recipe_good_first_issue_never_referenced_test", DETECTOR_PATH
)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 3, 6, 0, 0, tzinfo=timezone.utc)


def _issue(
    number: int,
    title: str,
    created_at: datetime,
    *,
    state: str = "open",
    labels: list[str] | None = None,
) -> "detector.Issue":
    return detector.Issue(
        number=number, title=title, state=state,
        labels=labels if labels is not None else ["good first issue"],
        created_at=created_at,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


def _pull(number: int, body: str, *, state: str = "open") -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, body=body,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestComputeGaps:
    def test_an_old_labeled_issue_never_referenced_is_surfaced_at_high_confidence(self):
        issue = _issue(601, "Old invitation", datetime(2026, 7, 20, 9, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([issue], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "good-first-issue-never-referenced-601"
        assert surfaced[0].confidence == 0.85
        assert surfaced[0].evidence == [issue.url]

    def test_a_recently_labeled_issue_never_referenced_is_surfaced_at_low_confidence(self):
        issue = _issue(602, "Fresh invitation", datetime(2026, 8, 2, 18, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([issue], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_an_issue_referenced_by_an_open_pr_closing_keyword_is_excluded(self):
        issue = _issue(603, "Claimed invitation", datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc))
        pr = _pull(701, "Working on it. fixes #603")

        surfaced, excluded = detector.compute_gaps([issue], [pr], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "already-referenced-603"

    def test_an_issue_referenced_by_a_closed_never_merged_pr_is_still_excluded(self):
        # An abandoned attempt still counts as someone having noticed --
        # this recipe asks whether the shelf item was ever picked up, not
        # whether picking it up succeeded.
        issue = _issue(603, "Claimed then abandoned", datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc))
        pr = _pull(701, "closes #603", state="closed")

        surfaced, excluded = detector.compute_gaps([issue], [pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "already-referenced-603"

    def test_an_already_closed_labeled_issue_is_excluded_not_surfaced(self):
        issue = _issue(604, "Already done", datetime(2026, 7, 10, 8, 0, 0, tzinfo=timezone.utc), state="closed")

        surfaced, excluded = detector.compute_gaps([issue], [], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "not-open-604"

    def test_an_issue_without_the_label_is_skipped_entirely_not_even_excluded(self):
        issue = _issue(605, "Not an invitation", datetime(2026, 7, 1, 8, 0, 0, tzinfo=timezone.utc), labels=["house:nisaba"])

        surfaced, excluded = detector.compute_gaps([issue], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_label_match_is_case_insensitive_and_whitespace_tolerant(self):
        issue = _issue(606, "Weird casing", datetime(2026, 7, 1, 8, 0, 0, tzinfo=timezone.utc), labels=[" Good First Issue "])

        surfaced, excluded = detector.compute_gaps([issue], [], now=_NOW)

        assert len(surfaced) == 1

    def test_a_pr_body_referencing_a_different_issue_does_not_exclude_this_one(self):
        issue = _issue(601, "Still open", datetime(2026, 7, 20, 9, 0, 0, tzinfo=timezone.utc))
        pr = _pull(702, "fixes #999 -- unrelated issue")

        surfaced, excluded = detector.compute_gaps([issue], [pr], now=_NOW)

        assert len(surfaced) == 1
        assert excluded == []

    def test_multiple_surfaced_issues_are_ranked_highest_confidence_first(self):
        old = _issue(601, "Old", datetime(2026, 7, 20, 9, 0, 0, tzinfo=timezone.utc))
        recent = _issue(602, "Recent", datetime(2026, 8, 2, 18, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([old, recent], [], now=_NOW)

        assert excluded == []
        assert [g.slug for g in surfaced] == [
            "good-first-issue-never-referenced-601",
            "good-first-issue-never-referenced-602",
        ]


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "good-first-issue-never-referenced-601"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recent_issue_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "good-first-issue-never-referenced-602" in tail_slugs

    def test_the_shipped_fixture_excludes_referenced_and_closed(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "already-referenced-603" in excluded_slugs
        assert "not-open-604" in excluded_slugs

    def test_the_shipped_fixture_never_names_the_unlabeled_issue_anywhere(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = (
            {g["slug"] for g in result["tail"]}
            | {g["slug"] for g in result["excluded"]}
            | ({result["primary_gap"]["slug"]} if result["primary_gap"] else set())
        )
        assert not any("605" in slug for slug in all_slugs)


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
