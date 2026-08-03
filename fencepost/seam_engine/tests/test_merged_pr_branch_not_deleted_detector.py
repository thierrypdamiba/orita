"""Tests for RECIPES/merged-pr-branch-not-deleted/detector.py's own
detection logic -- the fortieth real recipe: a pull request reached a
terminal state (merged or closed), but its own head branch was never
deleted.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "merged-pr-branch-not-deleted" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_merged_pr_branch_not_deleted_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)


def _pr(number: int, head_ref: str, state: str = "merged", resolved_at: datetime | None = None) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, head_ref=head_ref,
        url=f"https://github.com/example/example-repo/pull/{number}", resolved_at=resolved_at,
    )


def _deletion(ref: str, created_at: datetime) -> "detector.Activity":
    return detector.Activity(
        type="branch_deletion", ref=ref, actor="some-contributor", created_at=created_at,
        url=f"https://github.com/example/example-repo/activity#branch_deletion-{ref}",
    )


class TestComputeGaps:
    def test_a_stale_resolved_pr_with_no_deletion_is_surfaced_at_high_confidence(self):
        pr = _pr(200, "feature/x", state="merged", resolved_at=_NOW - timedelta(days=3))

        surfaced, excluded = detector.compute_gaps([pr], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "merged-pr-branch-not-deleted-200"
        assert surfaced[0].confidence == 0.85

    def test_a_recently_resolved_pr_with_no_deletion_is_surfaced_at_low_confidence(self):
        pr = _pr(201, "feature/y", state="closed", resolved_at=_NOW - timedelta(hours=6))

        surfaced, excluded = detector.compute_gaps([pr], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_resolved_pr_whose_branch_was_already_deleted_is_excluded_not_surfaced(self):
        pr = _pr(202, "chore/deps", state="merged", resolved_at=_NOW - timedelta(days=2))
        deletion = _deletion("chore/deps", _NOW - timedelta(days=2) + timedelta(minutes=5))

        surfaced, excluded = detector.compute_gaps([pr], [deletion], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "branch-already-deleted-202"

    def test_a_still_open_pr_is_excluded_not_surfaced(self):
        pr = _pr(203, "wip/thing", state="open", resolved_at=None)

        surfaced, excluded = detector.compute_gaps([pr], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "pr-not-yet-resolved-203"

    def test_a_deletion_for_an_unrelated_ref_does_not_suppress_the_gap(self):
        pr = _pr(204, "feature/z", state="merged", resolved_at=_NOW - timedelta(days=3))
        unrelated = _deletion("some/other-branch", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([pr], [unrelated], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "merged-pr-branch-not-deleted-204"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "merged-pr-branch-not-deleted-145"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_ranks_the_recent_closure_into_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "merged-pr-branch-not-deleted-150" in tail_slugs

    def test_the_shipped_fixture_excludes_the_already_deleted_branch_and_the_open_pr(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "branch-already-deleted-152" in excluded_slugs
        assert "pr-not-yet-resolved-160" in excluded_slugs


class TestLoaders:
    """load_pull_requests/load_activities -- mirrors every prior recipe's
    own `_load_rows` guard against syntactically valid but non-list JSON."""

    def test_load_pull_requests_parses_the_real_fixture(self):
        pull_requests = detector.load_pull_requests()
        assert len(pull_requests) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pull_requests)

    def test_load_activities_parses_the_real_fixture(self):
        activities = detector.load_activities()
        assert len(activities) > 0
        assert all(isinstance(a, detector.Activity) for a in activities)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pull_requests_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pull_requests(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_activities_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_activities(bad_file)
