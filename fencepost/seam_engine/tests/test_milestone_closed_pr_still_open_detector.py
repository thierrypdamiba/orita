"""Tests for RECIPES/milestone-closed-pr-still-open/detector.py's own
detection logic (ROADMAP.md #380) -- the eleventh real recipe: the
pull-request-side mirror of milestone-closed-issue-still-open (task 379),
a milestone reads closed, but one of its own pull requests never did.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "milestone-closed-pr-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_milestone_closed_pr_still_open_test", DETECTOR_PATH)
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


def _pr(
    number: int,
    milestone_number: int | None,
    state: str = "open",
    merged: bool = False,
) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, merged=merged,
        milestone_number=milestone_number,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestComputeGaps:
    def test_a_stale_closed_milestone_is_surfaced_at_high_confidence(self):
        milestone = _milestone(1, closed_at=datetime(2026, 7, 24, 10, 0, 0, tzinfo=timezone.utc))
        pr = _pr(901, milestone_number=1)

        surfaced, excluded = detector.compute_gaps([milestone], [pr], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-closed-pr-still-open-901-1"
        assert surfaced[0].confidence == 0.85

    def test_a_recently_closed_milestone_is_surfaced_at_low_confidence(self):
        milestone = _milestone(2, closed_at=_NOW - timedelta(hours=3))
        pr = _pr(902, milestone_number=2)

        surfaced, excluded = detector.compute_gaps([milestone], [pr], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_pull_request_already_merged_is_never_considered(self):
        milestone = _milestone(1, closed_at=datetime(2026, 7, 24, 10, 0, 0, tzinfo=timezone.utc))
        pr = _pr(903, milestone_number=1, state="closed", merged=True)

        surfaced, excluded = detector.compute_gaps([milestone], [pr], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_pull_request_closed_unmerged_is_never_considered(self):
        milestone = _milestone(1, closed_at=datetime(2026, 7, 24, 10, 0, 0, tzinfo=timezone.utc))
        pr = _pr(910, milestone_number=1, state="closed", merged=False)

        surfaced, excluded = detector.compute_gaps([milestone], [pr], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_still_open_milestone_is_excluded_not_surfaced(self):
        milestone = _milestone(3, state="open", closed_at=None)
        pr = _pr(904, milestone_number=3)

        surfaced, excluded = detector.compute_gaps([milestone], [pr], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "milestone-still-open-904-3" in excluded_slugs

    def test_a_pull_request_with_no_milestone_produces_no_candidate_at_all(self):
        pr = _pr(905, milestone_number=None)

        surfaced, excluded = detector.compute_gaps([], [pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-milestone-905"

    def test_an_unrecognized_milestone_number_is_excluded_not_surfaced(self):
        pr = _pr(906, milestone_number=999)

        surfaced, excluded = detector.compute_gaps([], [pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "nonexistent-target-906-999"


class TestNonexistentMilestoneIsNotMislabeledStillOpen:
    """ROADMAP.md #431: `milestone is None` (the milestone number was never
    real) used to share a slug and detail with `milestone.state != "closed"`
    (a milestone that genuinely exists and is still open) -- the same
    conflation tasks 429/430 already split in the merged-pr/issue-closed
    sibling recipes."""

    def test_a_nonexistent_milestone_excludes_as_a_dangling_reference_not_still_open(self):
        pr = _pr(907, milestone_number=999)

        surfaced, excluded = detector.compute_gaps([], [pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "nonexistent-target-907-999"
        assert "still open" not in excluded[0].detail
        assert "has not closed" not in excluded[0].detail
        assert "no such milestone exists" in excluded[0].detail

    def test_a_genuinely_still_open_milestone_keeps_its_own_distinct_slug(self):
        milestone = _milestone(3, state="open", closed_at=None)
        pr = _pr(908, milestone_number=3)

        surfaced, excluded = detector.compute_gaps([milestone], [pr], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "milestone-still-open-908-3"
        assert "has not closed yet" in excluded[0].detail


class TestClosedMilestoneWithNoTimestampIsNotMislabeledStillOpen:
    """ROADMAP.md #433: `milestone.state != "closed" or milestone.closed_at
    is None` folded a genuinely still-open milestone and a milestone that
    reads closed but carries no closed_at (a malformed record) into the
    same `milestone-still-open-...` slug and its false "has not closed yet"
    detail. Split so the malformed case gets its own honest slug."""

    def test_a_closed_milestone_with_no_timestamp_is_excluded_as_malformed_not_still_open(self):
        milestone = _milestone(790, state="closed", closed_at=None)
        pr = _pr(791, milestone_number=790, state="open")

        surfaced, excluded = detector.compute_gaps([milestone], [pr], now=_NOW)

        assert surfaced == []
        by_slug = {g.slug: g for g in excluded}
        candidate = by_slug["milestone-closed-no-timestamp-791-790"]
        assert "has not closed yet" not in candidate.detail
        assert "malformed" in candidate.detail
        assert candidate.evidence == [pr.url, milestone.url]


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "milestone-closed-pr-still-open-901-1"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recently_closed_milestone_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "milestone-closed-pr-still-open-902-2" in tail_slugs

    def test_the_shipped_fixture_excludes_the_still_open_milestone_and_no_milestone_pr(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "milestone-still-open-904-3" in excluded_slugs
        assert "no-milestone-905" in excluded_slugs
        assert "nonexistent-target-906-99" in excluded_slugs

    def test_the_shipped_fixture_never_considers_the_already_merged_pull_request(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {g["slug"] for g in result["excluded"]}
        all_slugs |= {g["slug"] for g in result["tail"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        assert not any("-903-" in s for s in all_slugs)


class TestLoaders:
    """load_milestones/load_pull_requests -- mirrors every prior recipe's
    own _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    def test_load_pull_requests_parses_the_real_fixture(self):
        pull_requests = detector.load_pull_requests()
        assert len(pull_requests) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pull_requests)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_milestones_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pull_requests_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pull_requests(bad_file)
