"""Tests for RECIPES/deleted-branch-pr-still-open/detector.py's own
detection logic (ROADMAP.md #485) -- the thirtieth real recipe: a pull
request's head branch was deleted upstream, but the PR itself was never
closed.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "deleted-branch-pr-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_deleted_branch_pr_still_open_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)


def _activity(ref: str, created_at: datetime, activity_type: str = "branch_deletion") -> "detector.Activity":
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
        assert detector._slug_ref("feature/login-fix") == "feature-login-fix"

    def test_no_slash_is_unchanged(self):
        assert detector._slug_ref("main") == "main"


class TestComputeGaps:
    def test_a_stale_deletion_against_an_open_pr_is_surfaced_at_high_confidence(self):
        activity = _activity("feature/x", _NOW - timedelta(days=3))
        pr = _pr(88, "feature/x", state="open")

        surfaced, excluded = detector.compute_gaps([activity], [pr], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "deleted-branch-pr-still-open-88"
        assert surfaced[0].confidence == 0.85

    def test_a_recent_deletion_against_an_open_pr_is_surfaced_at_low_confidence(self):
        activity = _activity("feature/y", _NOW - timedelta(hours=6))
        pr = _pr(90, "feature/y", state="open")

        surfaced, excluded = detector.compute_gaps([activity], [pr], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_deletion_with_no_matching_pr_is_excluded_not_surfaced(self):
        activity = _activity("spike/nothing", _NOW - timedelta(days=1))

        surfaced, excluded = detector.compute_gaps([activity], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-pr-for-deleted-branch-spike-nothing"

    def test_a_deletion_against_an_already_merged_pr_is_excluded_not_surfaced(self):
        activity = _activity("chore/deps", _NOW - timedelta(days=2))
        pr = _pr(81, "chore/deps", state="merged")

        surfaced, excluded = detector.compute_gaps([activity], [pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "pr-already-merged-81"

    def test_a_non_branch_deletion_activity_produces_no_candidate_at_all(self):
        activity = _activity("main", _NOW - timedelta(hours=1), activity_type="push")
        pr = _pr(1, "main", state="open")

        surfaced, excluded = detector.compute_gaps([activity], [pr], now=_NOW)

        assert surfaced == []
        assert excluded == []


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "deleted-branch-pr-still-open-88"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_excludes_the_already_merged_pr_and_the_orphan_deletion(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "pr-already-merged-81" in excluded_slugs
        assert "no-pr-for-deleted-branch-spike-cache-experiment" in excluded_slugs

    def test_the_shipped_fixture_never_surfaces_the_push_activity(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {g["slug"] for g in result["excluded"]}
        all_slugs |= {g["slug"] for g in result["tail"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        assert not any("main" in s for s in all_slugs)


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
