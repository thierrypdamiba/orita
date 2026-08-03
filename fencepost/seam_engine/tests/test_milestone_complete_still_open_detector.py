"""Tests for RECIPES/milestone-complete-still-open/detector.py's own
detection logic (ROADMAP.md #512) -- the thirty-ninth real recipe: every
issue inside an open milestone has closed, and the milestone itself
never did.

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this test
exercises the exact module a live scan would import, not a copy.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "milestone-complete-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_milestone_complete_still_open_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 3, 18, 0, 0, tzinfo=timezone.utc)


def _milestone(
    number: int,
    title: str,
    updated_at: datetime,
    *,
    state: str = "open",
    open_issues: int = 0,
    closed_issues: int = 1,
) -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=title, state=state,
        open_issues=open_issues, closed_issues=closed_issues,
        updated_at=updated_at,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


class TestComputeGaps:
    def test_a_complete_milestone_idle_well_past_the_bar_is_surfaced_at_high_confidence(self):
        m = _milestone(30, "v2.0 Cutover", datetime(2026, 7, 25, 9, 0, 0, tzinfo=timezone.utc), closed_issues=11)

        surfaced, excluded = detector.compute_gaps([m], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-complete-still-open-30"
        assert surfaced[0].confidence == 0.85
        assert surfaced[0].evidence == [m.url]

    def test_a_complete_milestone_just_gone_idle_is_surfaced_at_low_confidence(self):
        m = _milestone(31, "Docs pass", datetime(2026, 8, 3, 10, 0, 0, tzinfo=timezone.utc), closed_issues=4)

        surfaced, excluded = detector.compute_gaps([m], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_milestone_still_carrying_open_issues_is_excluded_not_surfaced(self):
        m = _milestone(32, "Still in flight", datetime(2026, 7, 20, 9, 0, 0, tzinfo=timezone.utc), open_issues=2, closed_issues=6)

        surfaced, excluded = detector.compute_gaps([m], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "not-complete-32"

    def test_a_milestone_with_no_issues_tracked_at_all_is_excluded_not_surfaced(self):
        m = _milestone(33, "Empty from the start", datetime(2026, 7, 15, 9, 0, 0, tzinfo=timezone.utc), open_issues=0, closed_issues=0)

        surfaced, excluded = detector.compute_gaps([m], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "no-issues-tracked-33"

    def test_a_closed_milestone_that_completed_is_excluded_not_surfaced(self):
        m = _milestone(34, "Closed on time", datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc), state="closed", closed_issues=8)

        surfaced, excluded = detector.compute_gaps([m], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "not-open-34"

    def test_multiple_complete_milestones_are_ranked_highest_confidence_first(self):
        old = _milestone(1, "Old", datetime(2026, 7, 1, tzinfo=timezone.utc))
        recent = _milestone(2, "Recent", datetime(2026, 8, 3, 12, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([old, recent], now=_NOW)

        assert excluded == []
        assert [g.slug for g in surfaced] == [
            "milestone-complete-still-open-1",
            "milestone-complete-still-open-2",
        ]


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "milestone-complete-still-open-30"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recently_idle_milestone_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "milestone-complete-still-open-31" in tail_slugs

    def test_the_shipped_fixture_excludes_not_complete_no_issues_and_closed(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "not-complete-32" in excluded_slugs
        assert "no-issues-tracked-33" in excluded_slugs
        assert "not-open-34" in excluded_slugs


class TestLoaders:
    """load_milestones -- mirrors every prior recipe's own _load_rows guard
    against syntactically valid but non-list JSON."""

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_milestones_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(bad_file)
