"""Tests for RECIPES/approved-pr-still-unmerged/detector.py's own detection
logic (ROADMAP.md #1046) -- the ninety-fourth real recipe: a pull request
already carries an approving review, and the PR itself never merged.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "approved-pr-still-unmerged" / "detector.py"

_spec = importlib.util.spec_from_file_location(
    "seam_engine._recipe_approved_pr_still_unmerged_test", DETECTOR_PATH
)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 6, 22, 0, 0, tzinfo=timezone.utc)


def _pr(
    number: int,
    state: str = "open",
    merged: bool = False,
    review_decision: str | None = "APPROVED",
    updated_at: datetime | None = None,
    title: str | None = None,
) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=title or f"PR {number}", state=state, merged=merged,
        review_decision=review_decision, updated_at=updated_at or _NOW,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestComputeGaps:
    def test_a_stale_approved_open_pr_is_surfaced_at_high_confidence(self):
        pr = _pr(501, updated_at=_NOW - timedelta(hours=48))

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "approved-pr-still-unmerged-501"
        assert surfaced[0].confidence == 0.85
        assert surfaced[0].evidence == [pr.url]

    def test_a_recently_approved_pr_is_surfaced_at_low_confidence(self):
        pr = _pr(502, updated_at=_NOW - timedelta(hours=3))

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_exactly_twenty_four_hours_counts_as_stale(self):
        pr = _pr(503, updated_at=_NOW - timedelta(hours=24))

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_changes_requested_excludes_the_pr_as_not_approved(self):
        pr = _pr(504, review_decision="CHANGES_REQUESTED", updated_at=_NOW - timedelta(hours=48))

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "approved-pr-not-approved-504"

    def test_no_review_yet_excludes_the_pr_as_not_approved(self):
        pr = _pr(505, review_decision=None, updated_at=_NOW - timedelta(hours=48))

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "approved-pr-not-approved-505"

    def test_a_merged_pr_is_excluded_even_when_approved(self):
        pr = _pr(506, state="closed", merged=True, updated_at=_NOW - timedelta(hours=48))

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "approved-pr-resolved-506"

    def test_a_closed_unmerged_pr_is_excluded_even_when_approved(self):
        pr = _pr(507, state="closed", merged=False, updated_at=_NOW - timedelta(hours=48))

        surfaced, excluded = detector.compute_gaps([pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "approved-pr-resolved-507"

    def test_multiple_open_approved_prs_each_get_their_own_candidate(self):
        prs = [
            _pr(508, updated_at=_NOW - timedelta(hours=48)),
            _pr(509, updated_at=_NOW - timedelta(hours=72)),
        ]

        surfaced, excluded = detector.compute_gaps(prs, now=_NOW)

        assert {g.slug for g in surfaced} == {
            "approved-pr-still-unmerged-508",
            "approved-pr-still-unmerged-509",
        }

    def test_surfaced_candidates_sort_by_confidence_descending(self):
        prs = [
            _pr(510, updated_at=_NOW - timedelta(hours=2)),
            _pr(511, updated_at=_NOW - timedelta(hours=100)),
        ]

        surfaced, _ = detector.compute_gaps(prs, now=_NOW)

        assert [g.confidence for g in surfaced] == [0.85, 0.5]


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "approved-pr-still-unmerged-401"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recently_touched_pr_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "approved-pr-still-unmerged-402" in tail_slugs

    def test_the_shipped_fixture_excludes_the_unapproved_and_resolved_prs(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "approved-pr-not-approved-403" in excluded_slugs
        assert "approved-pr-not-approved-404" in excluded_slugs
        assert "approved-pr-resolved-405" in excluded_slugs


class TestLoaders:
    """load_pull_requests -- mirrors every prior recipe's own _load_rows
    guard against syntactically valid but non-list JSON."""

    def test_load_pull_requests_parses_the_real_fixture(self):
        prs = detector.load_pull_requests()
        assert len(prs) > 0
        assert all(isinstance(p, detector.PullRequest) for p in prs)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pull_requests_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pull_requests(bad_file)

    def test_load_pull_requests_defaults_a_missing_review_decision_to_none(self, tmp_path: Path):
        f = tmp_path / "prs.json"
        f.write_text(json.dumps([{
            "number": 1, "title": "t", "state": "open", "merged": False,
            "updated_at": "2026-08-06T00:00:00Z", "url": "https://example.com/1",
        }]))
        prs = detector.load_pull_requests(f)
        assert prs[0].review_decision is None
