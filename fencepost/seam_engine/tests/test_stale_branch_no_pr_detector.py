"""Tests for RECIPES/stale-branch-no-pr/detector.py's own detection logic
(ROADMAP.md #490) -- the thirty-fourth real recipe: a branch was created,
and no pull request has ever been opened from it.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "stale-branch-no-pr" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_stale_branch_no_pr_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 2, 12, 0, 0, tzinfo=timezone.utc)


def _activity(ref: str, created_at: datetime, activity_type: str = "branch_creation") -> "detector.Activity":
    return detector.Activity(
        type=activity_type, ref=ref, actor="some-contributor", created_at=created_at,
        url=f"https://github.com/example/example-repo/activity#{activity_type}-{ref}",
    )


def _pr(number: int, head_ref: str, state: str = "open") -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, head_ref=head_ref,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestSlugRef:
    def test_slashes_become_dashes(self):
        assert detector._slug_ref("feature/dark-mode") == "feature-dark-mode"

    def test_no_slash_is_unchanged(self):
        assert detector._slug_ref("main") == "main"


class TestComputeGaps:
    def test_a_stale_branch_with_no_pr_is_surfaced_at_high_confidence(self):
        activity = _activity("spike/x", _NOW - timedelta(days=5))

        surfaced, excluded = detector.compute_gaps([activity], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "stale-branch-no-pr-spike-x"
        assert surfaced[0].confidence == 0.85

    def test_a_recent_branch_with_no_pr_is_surfaced_at_low_confidence(self):
        activity = _activity("feature/y", _NOW - timedelta(hours=6))

        surfaced, excluded = detector.compute_gaps([activity], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_exactly_ninety_six_hours_counts_as_stale(self):
        activity = _activity("feature/edge", _NOW - timedelta(hours=96))

        surfaced, excluded = detector.compute_gaps([activity], [], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_a_branch_with_an_open_pr_is_excluded_not_surfaced(self):
        activity = _activity("feature/z", _NOW - timedelta(days=3))
        pr = _pr(10, "feature/z", state="open")

        surfaced, excluded = detector.compute_gaps([activity], [pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "branch-has-pr-feature-z"

    def test_a_branch_with_a_merged_pr_is_excluded_not_surfaced(self):
        # Unlike deleted-branch-pr-still-open, ANY pr state clears this seam
        # -- the promise here is only "was a PR ever opened," not "is it
        # still open."
        activity = _activity("chore/deps", _NOW - timedelta(days=6))
        pr = _pr(11, "chore/deps", state="merged")

        surfaced, excluded = detector.compute_gaps([activity], [pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "branch-has-pr-chore-deps"

    def test_a_branch_with_a_closed_unmerged_pr_is_excluded_not_surfaced(self):
        activity = _activity("spike/dead-end", _NOW - timedelta(days=10))
        pr = _pr(12, "spike/dead-end", state="closed")

        surfaced, excluded = detector.compute_gaps([activity], [pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "branch-has-pr-spike-dead-end"

    def test_the_default_branch_main_is_excluded_not_surfaced(self):
        activity = _activity("main", _NOW - timedelta(days=30))

        surfaced, excluded = detector.compute_gaps([activity], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "default-branch-main"

    def test_the_default_branch_master_is_excluded_not_surfaced(self):
        activity = _activity("master", _NOW - timedelta(days=30))

        surfaced, excluded = detector.compute_gaps([activity], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "default-branch-master"

    def test_a_non_branch_creation_activity_produces_no_candidate_at_all(self):
        activity = _activity("main", _NOW - timedelta(hours=1), activity_type="push")

        surfaced, excluded = detector.compute_gaps([activity], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_branch_deletion_activity_produces_no_candidate_at_all(self):
        activity = _activity("feature/gone", _NOW - timedelta(days=2), activity_type="branch_deletion")

        surfaced, excluded = detector.compute_gaps([activity], [], now=_NOW)

        assert surfaced == []
        assert excluded == []


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "stale-branch-no-pr-spike-rate-limit-cache"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_puts_the_young_branch_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "stale-branch-no-pr-feature-dark-mode" in tail_slugs

    def test_the_shipped_fixture_excludes_the_claimed_branch_and_the_default_branch(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "branch-has-pr-chore-lockfile-bump" in excluded_slugs
        assert "default-branch-main" in excluded_slugs

    def test_the_shipped_fixture_never_surfaces_the_push_activity(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {g["slug"] for g in result["excluded"]}
        all_slugs |= {g["slug"] for g in result["tail"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        assert not any("push" in s for s in all_slugs)


class TestLoaders:
    """load_activities/load_pull_requests -- mirrors every prior recipe's
    own `_load_rows` guard against syntactically valid but non-list JSON."""

    def test_load_activities_parses_the_real_fixture(self):
        activities = detector.load_activities()
        assert len(activities) > 0
        assert all(isinstance(a, detector.Activity) for a in activities)

    def test_load_pull_requests_parses_the_real_fixture(self):
        pull_requests = detector.load_pull_requests()
        assert len(pull_requests) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pull_requests)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_activities_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_activities(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pull_requests_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pull_requests(bad_file)
