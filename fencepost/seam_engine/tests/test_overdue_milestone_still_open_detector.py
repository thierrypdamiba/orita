"""Tests for RECIPES/overdue-milestone-still-open/detector.py's own
detection logic (ROADMAP.md #489) -- the thirty-third real recipe: a
milestone's own due date passed, and it's still open.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "overdue-milestone-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_overdue_milestone_still_open_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 2, 20, 0, 0, tzinfo=timezone.utc)


def _milestone(
    number: int,
    title: str,
    due_on: datetime | None,
    *,
    state: str = "open",
    open_issues: int = 0,
    closed_issues: int = 0,
) -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=title, state=state, due_on=due_on,
        open_issues=open_issues, closed_issues=closed_issues,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


class TestComputeGaps:
    def test_an_open_milestone_well_past_its_due_date_is_surfaced_at_high_confidence(self):
        m = _milestone(20, "v1.3 Release", datetime(2026, 7, 10, tzinfo=timezone.utc), open_issues=3, closed_issues=9)

        surfaced, excluded = detector.compute_gaps([m], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "overdue-milestone-still-open-20"
        assert surfaced[0].confidence == 0.85
        assert surfaced[0].evidence == [m.url]

    def test_a_milestone_just_past_its_due_date_is_surfaced_at_low_confidence(self):
        m = _milestone(21, "Security patch backlog", datetime(2026, 8, 2, 9, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([m], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_milestone_not_yet_due_is_excluded_not_surfaced(self):
        m = _milestone(22, "Future roadmap", datetime(2026, 9, 1, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([m], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "not-yet-due-22"

    def test_a_milestone_with_no_due_date_is_excluded_not_surfaced(self):
        m = _milestone(23, "No due date tracked", None)

        surfaced, excluded = detector.compute_gaps([m], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "no-due-date-23"

    def test_a_closed_milestone_past_its_due_date_is_excluded_not_surfaced(self):
        m = _milestone(24, "Closed but was overdue", datetime(2026, 6, 1, tzinfo=timezone.utc), state="closed")

        surfaced, excluded = detector.compute_gaps([m], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "not-open-24"

    def test_multiple_overdue_milestones_are_ranked_highest_confidence_first(self):
        old = _milestone(1, "Old", datetime(2026, 7, 1, tzinfo=timezone.utc))
        recent = _milestone(2, "Recent", datetime(2026, 8, 2, 12, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([old, recent], now=_NOW)

        assert excluded == []
        assert [g.slug for g in surfaced] == [
            "overdue-milestone-still-open-1",
            "overdue-milestone-still-open-2",
        ]


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "overdue-milestone-still-open-20"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recently_overdue_milestone_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "overdue-milestone-still-open-21" in tail_slugs

    def test_the_shipped_fixture_excludes_not_yet_due_no_due_date_and_closed(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "not-yet-due-22" in excluded_slugs
        assert "no-due-date-23" in excluded_slugs
        assert "not-open-24" in excluded_slugs


class TestLoaders:
    """load_milestones -- mirrors every prior recipe's own _load_rows guard
    against syntactically valid but non-list JSON, plus this recipe's own
    nullable due_on handling."""

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    def test_load_milestones_leaves_due_on_none_when_absent_or_null(self):
        milestones = detector.load_milestones()
        by_number = {m.number: m for m in milestones}
        assert by_number[23].due_on is None

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_milestones_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(bad_file)
