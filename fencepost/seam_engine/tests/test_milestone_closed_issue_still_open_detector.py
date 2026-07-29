"""Tests for RECIPES/milestone-closed-issue-still-open/detector.py's own
detection logic (ROADMAP.md #379) -- the tenth real recipe: a milestone
reads closed, but one of its own issues never did.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "milestone-closed-issue-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_milestone_closed_issue_still_open_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 26, 12, 0, 0, tzinfo=timezone.utc)


def _milestone(
    number: int,
    state: str = "closed",
    closed_at: datetime | None = None,
) -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state, closed_at=closed_at,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


def _issue(
    number: int,
    milestone_number: int | None,
    state: str = "open",
) -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state,
        milestone_number=milestone_number,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestComputeGaps:
    def test_a_stale_closed_milestone_is_surfaced_at_high_confidence(self):
        milestone = _milestone(1, closed_at=datetime(2026, 7, 24, 10, 0, 0, tzinfo=timezone.utc))
        issue = _issue(801, milestone_number=1)

        surfaced, excluded = detector.compute_gaps([milestone], [issue], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-closed-issue-still-open-801-1"
        assert surfaced[0].confidence == 0.85

    def test_a_recently_closed_milestone_is_surfaced_at_low_confidence(self):
        milestone = _milestone(2, closed_at=_NOW - timedelta(hours=3))
        issue = _issue(802, milestone_number=2)

        surfaced, excluded = detector.compute_gaps([milestone], [issue], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_an_issue_already_closed_is_never_considered(self):
        milestone = _milestone(1, closed_at=datetime(2026, 7, 24, 10, 0, 0, tzinfo=timezone.utc))
        issue = _issue(803, milestone_number=1, state="closed")

        surfaced, excluded = detector.compute_gaps([milestone], [issue], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_still_open_milestone_is_excluded_not_surfaced(self):
        milestone = _milestone(3, state="open", closed_at=None)
        issue = _issue(804, milestone_number=3)

        surfaced, excluded = detector.compute_gaps([milestone], [issue], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "milestone-still-open-804-3" in excluded_slugs

    def test_an_issue_with_no_milestone_produces_no_candidate_at_all(self):
        issue = _issue(805, milestone_number=None)

        surfaced, excluded = detector.compute_gaps([], [issue], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-milestone-805"

    def test_an_unrecognized_milestone_number_is_excluded_not_surfaced(self):
        issue = _issue(806, milestone_number=999)

        surfaced, excluded = detector.compute_gaps([], [issue], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "milestone-still-open-806-999"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "milestone-closed-issue-still-open-801-1"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recently_closed_milestone_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "milestone-closed-issue-still-open-802-2" in tail_slugs

    def test_the_shipped_fixture_excludes_the_still_open_milestone_and_no_milestone_issue(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "milestone-still-open-804-3" in excluded_slugs
        assert "no-milestone-805" in excluded_slugs

    def test_the_shipped_fixture_never_considers_the_already_closed_issue(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {g["slug"] for g in result["excluded"]}
        all_slugs |= {g["slug"] for g in result["tail"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        assert not any("-803-" in s for s in all_slugs)


class TestLoaders:
    """load_milestones/load_issues -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_milestones_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_issues_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issues(bad_file)
