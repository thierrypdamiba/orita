"""Tests for RECIPES/duplicate-milestone-still-open/detector.py's own
detection logic (ROADMAP.md #488) -- the thirty-second real recipe: two
open milestones share the exact same title, and nothing on GitHub ever
flags it.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "duplicate-milestone-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_duplicate_milestone_still_open_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 2, 12, 0, 0, tzinfo=timezone.utc)


def _milestone(
    number: int,
    title: str,
    created_at: datetime,
    state: str = "open",
) -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=title, state=state, created_at=created_at,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


class TestComputeGaps:
    def test_two_open_milestones_sharing_a_title_past_the_bar_are_surfaced_at_high_confidence(self):
        original = _milestone(8, "Fencepost v0.2", datetime(2026, 7, 1, tzinfo=timezone.utc))
        dup = _milestone(9, "Fencepost v0.2", datetime(2026, 7, 3, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([original, dup], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "duplicate-milestone-still-open-9-8"
        assert surfaced[0].confidence == 0.85
        assert surfaced[0].evidence == [dup.url, original.url]

    def test_a_recently_created_duplicate_title_is_surfaced_at_low_confidence(self):
        original = _milestone(13, "Docs cleanup", datetime(2026, 8, 2, 6, 0, 0, tzinfo=timezone.utc))
        dup = _milestone(14, "Docs cleanup", datetime(2026, 8, 2, 9, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([original, dup], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_title_reused_after_the_first_closed_is_excluded_not_surfaced(self):
        closed_first = _milestone(1, "v1.0 Launch", datetime(2026, 6, 1, tzinfo=timezone.utc), state="closed")
        reused = _milestone(5, "v1.0 Launch", datetime(2026, 6, 15, tzinfo=timezone.utc), state="open")

        surfaced, excluded = detector.compute_gaps([closed_first, reused], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "not-live-duplicate-1-5"

    def test_a_title_held_by_only_one_milestone_produces_no_candidate_at_all(self):
        m = _milestone(12, "Beta feedback", datetime(2026, 7, 30, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([m], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-duplicate-title-12"

    def test_a_third_milestone_sharing_the_title_pairs_against_the_original_too(self):
        original = _milestone(20, "Repeat offender", datetime(2026, 6, 1, tzinfo=timezone.utc))
        dup_a = _milestone(21, "Repeat offender", datetime(2026, 6, 10, tzinfo=timezone.utc))
        dup_b = _milestone(22, "Repeat offender", datetime(2026, 6, 20, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([original, dup_a, dup_b], now=_NOW)

        assert excluded == []
        slugs = {g.slug for g in surfaced}
        assert slugs == {
            "duplicate-milestone-still-open-21-20",
            "duplicate-milestone-still-open-22-20",
        }

    def test_two_milestones_both_closed_with_a_shared_title_produce_no_live_candidate(self):
        a = _milestone(30, "Old sprint", datetime(2026, 5, 1, tzinfo=timezone.utc), state="closed")
        b = _milestone(31, "Old sprint", datetime(2026, 5, 8, tzinfo=timezone.utc), state="closed")

        surfaced, excluded = detector.compute_gaps([a, b], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "not-live-duplicate-30-31"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "duplicate-milestone-still-open-9-8"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recent_duplicate_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "duplicate-milestone-still-open-14-13" in tail_slugs

    def test_the_shipped_fixture_excludes_the_resolved_and_unique_titles(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "not-live-duplicate-1-5" in excluded_slugs
        assert "no-duplicate-title-12" in excluded_slugs


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
