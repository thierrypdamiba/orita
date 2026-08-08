"""Tests for RECIPES/merged-pr-requested-reviewer-never-reviewed/detector.py's
own detection logic -- the sixty-third real recipe: a pull request merged
without a single comment from a reviewer it explicitly requested.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "merged-pr-requested-reviewer-never-reviewed" / "detector.py"

_spec = importlib.util.spec_from_file_location(
    "seam_engine._recipe_merged_pr_requested_reviewer_never_reviewed_test", DETECTOR_PATH
)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 8, 12, 0, 0, tzinfo=timezone.utc)


def _pr(
    number: int,
    requested_reviewers: list[str],
    state: str = "merged",
    merged_at: datetime | None = None,
) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, merged_at=merged_at,
        requested_reviewers=requested_reviewers,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


def _comment(pr_number: int, author: str, comment_id: int = 1) -> "detector.ReviewComment":
    return detector.ReviewComment(
        id=comment_id, pull_request_number=pr_number, author=author, body="A review comment.",
        url=f"https://github.com/example/example-repo/pull/{pr_number}#discussion_r{comment_id}",
    )


class TestDedupPreserveOrder:
    def test_removes_duplicates_keeping_first_seen_order(self):
        assert detector._dedup_preserve_order(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]

    def test_empty_list_returns_empty_list(self):
        assert detector._dedup_preserve_order([]) == []

    def test_no_duplicates_returns_same_order(self):
        assert detector._dedup_preserve_order(["x", "y", "z"]) == ["x", "y", "z"]


class TestComputeGaps:
    def test_a_stale_unreviewed_request_is_surfaced_at_high_confidence(self):
        pr = _pr(950, ["reviewer-a"], merged_at=datetime(2026, 7, 30, 9, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([pr], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "merged-pr-requested-reviewer-never-reviewed-950-reviewer-a"
        assert surfaced[0].confidence == 0.85
        assert surfaced[0].evidence == [pr.url]

    def test_a_recently_unreviewed_request_is_surfaced_at_low_confidence(self):
        pr = _pr(951, ["reviewer-b"], merged_at=_NOW - timedelta(hours=6))

        surfaced, excluded = detector.compute_gaps([pr], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_requested_reviewer_who_commented_is_excluded_not_surfaced(self):
        pr = _pr(952, ["reviewer-c"], merged_at=datetime(2026, 8, 1, 9, 0, 0, tzinfo=timezone.utc))
        comment = _comment(952, "reviewer-c")

        surfaced, excluded = detector.compute_gaps([pr], [comment], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "reviewer-commented-952-reviewer-c" in excluded_slugs

    def test_a_comment_from_someone_other_than_the_requested_reviewer_does_not_fulfill_the_request(self):
        # The whole point of this recipe: it is about the SPECIFIC named
        # login, not "did anyone comment at all."
        pr = _pr(950, ["reviewer-a"], merged_at=datetime(2026, 7, 30, 9, 0, 0, tzinfo=timezone.utc))
        comment = _comment(950, "other-dev")

        surfaced, excluded = detector.compute_gaps([pr], [comment], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "merged-pr-requested-reviewer-never-reviewed-950-reviewer-a"
        assert excluded == []

    def test_an_open_pull_request_is_excluded_not_surfaced(self):
        pr = _pr(953, ["reviewer-d"], state="open", merged_at=None)

        surfaced, excluded = detector.compute_gaps([pr], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "not-merged-953"

    def test_a_closed_but_unmerged_pull_request_is_excluded_not_surfaced(self):
        pr = _pr(957, ["reviewer-d"], state="closed", merged_at=None)

        surfaced, excluded = detector.compute_gaps([pr], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "not-merged-957"

    def test_a_merged_pr_with_no_requested_reviewer_is_excluded_not_surfaced(self):
        pr = _pr(954, [], merged_at=datetime(2026, 8, 2, 9, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([pr], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-requested-reviewer-954"

    def test_a_merged_pr_with_no_merged_at_timestamp_is_excluded_as_malformed(self):
        pr = _pr(955, ["reviewer-e"], merged_at=None)

        surfaced, excluded = detector.compute_gaps([pr], [], now=_NOW)

        assert surfaced == []
        by_slug = {g.slug: g for g in excluded}
        candidate = by_slug["no-merged-timestamp-955"]
        assert "still open" not in candidate.detail
        assert "malformed" in candidate.detail

    def test_a_blank_requested_reviewer_entry_is_excluded_outright(self):
        pr = _pr(958, ["", "reviewer-h"], merged_at=datetime(2026, 7, 25, 9, 0, 0, tzinfo=timezone.utc))
        comment = _comment(958, "reviewer-h")

        surfaced, excluded = detector.compute_gaps([pr], [comment], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "blank-requested-reviewer-958" in excluded_slugs
        assert "reviewer-commented-958-reviewer-h" in excluded_slugs

    def test_multiple_requested_reviewers_are_each_judged_independently(self):
        pr = _pr(956, ["reviewer-f", "reviewer-g"], merged_at=_NOW - timedelta(hours=10))
        comment = _comment(956, "reviewer-f")

        surfaced, excluded = detector.compute_gaps([pr], [comment], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "merged-pr-requested-reviewer-never-reviewed-956-reviewer-g"
        excluded_slugs = {g.slug for g in excluded}
        assert "reviewer-commented-956-reviewer-f" in excluded_slugs

    def test_a_duplicate_requested_reviewer_login_produces_only_one_candidate(self):
        pr = _pr(960, ["reviewer-z", "reviewer-z"], merged_at=datetime(2026, 7, 20, 9, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([pr], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "merged-pr-requested-reviewer-never-reviewed-960-reviewer-z"

    def test_surfaced_candidates_are_sorted_by_confidence_descending(self):
        stale = _pr(961, ["reviewer-i"], merged_at=datetime(2026, 7, 1, 9, 0, 0, tzinfo=timezone.utc))
        recent = _pr(962, ["reviewer-j"], merged_at=_NOW - timedelta(hours=2))

        surfaced, _ = detector.compute_gaps([recent, stale], [], now=_NOW)

        assert [g.confidence for g in surfaced] == [0.85, 0.5]

    def test_an_empty_pull_request_list_produces_no_candidates_at_all(self):
        surfaced, excluded = detector.compute_gaps([], [], now=_NOW)
        assert surfaced == []
        assert excluded == []


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "merged-pr-requested-reviewer-never-reviewed-950-reviewer-a"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_two_recent_gaps_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "merged-pr-requested-reviewer-never-reviewed-951-reviewer-b" in tail_slugs
        assert "merged-pr-requested-reviewer-never-reviewed-956-reviewer-g" in tail_slugs

    def test_the_shipped_fixture_excludes_the_ordinary_and_malformed_cases(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "not-merged-953" in excluded_slugs
        assert "not-merged-957" in excluded_slugs
        assert "no-requested-reviewer-954" in excluded_slugs
        assert "no-merged-timestamp-955" in excluded_slugs
        assert "reviewer-commented-952-reviewer-c" in excluded_slugs
        assert "reviewer-commented-956-reviewer-f" in excluded_slugs
        assert "blank-requested-reviewer-958" in excluded_slugs
        assert "reviewer-commented-958-reviewer-h" in excluded_slugs

    def test_the_shipped_fixture_reports_source_fixture(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["source"] == "fixture"

    def test_the_shipped_fixture_confidence_bar_and_margin_match_the_ranking_law(self):
        from seam_engine.ranking import CONFIDENCE_BAR, SEPARATION_MARGIN

        result = detector.run_recipe_scan(now=_NOW)
        assert result["confidence_bar"] == CONFIDENCE_BAR
        assert result["separation_margin"] == SEPARATION_MARGIN


class TestLoaders:
    def test_load_pull_requests_parses_the_real_fixture(self):
        pulls = detector.load_pull_requests()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pulls)

    def test_load_review_comments_parses_the_real_fixture(self):
        comments = detector.load_review_comments()
        assert len(comments) > 0
        assert all(isinstance(c, detector.ReviewComment) for c in comments)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pull_requests_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pull_requests(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_review_comments_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_review_comments(bad_file)
