"""Tests for RECIPES/merged-pr-pr-still-open/detector.py's own detection
logic -- mirrors test_merged_pr_issue_still_open_detector.py's own
discipline (compute_gaps, the loaders, and their error handling), applied
to the PR-target half of the same closing-keyword seam.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "merged-pr-pr-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_merged_pr_pr_still_open_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)


def _pull(body: str, number: int = 100, merged_at: datetime = datetime(2026, 7, 15, 0, 0, 0, tzinfo=timezone.utc)) -> "detector.MergedPull":
    return detector.MergedPull(
        id=f"PR-{number}", title="Some fix", number=number, body=body, merged_at=merged_at,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


def _pr(number: int, state: str, merged: bool = False, merged_at: datetime | None = None) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, merged=merged, merged_at=merged_at,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestClosingRefs:
    def test_a_single_closing_keyword_returns_one_number(self):
        assert detector._closing_refs("Closes #55") == [55]

    def test_two_closing_keywords_return_both_numbers(self):
        assert detector._closing_refs("This closes #1 and fixes #2") == [1, 2]

    def test_no_closing_keyword_returns_an_empty_list(self):
        assert detector._closing_refs("No linked PR, docs only.") == []

    def test_present_participle_phrasing_never_matches(self):
        # Iron Rule #8's own prescribed safe form -- "closing #N" must never
        # fire the same trigger "closes #N" does.
        assert detector._closing_refs("Closing #55 for discussion, not actually resolved.") == []


class TestComputeGaps:
    def test_target_still_open_and_stale_is_surfaced(self):
        pull = _pull("Closes #150", number=201)
        prs = [_pr(150, "open")]

        surfaced, excluded = detector.compute_gaps([pull], prs, now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "merged-pr-pr-still-open-201-150"
        assert surfaced[0].confidence == 0.85

    def test_target_still_open_but_fresh_scores_below_the_bar(self):
        pull = _pull("Closes #150", number=201, merged_at=datetime(2026, 7, 20, 6, 0, 0, tzinfo=timezone.utc))
        prs = [_pr(150, "open")]

        surfaced, excluded = detector.compute_gaps([pull], prs, now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.55

    def test_already_merged_target_is_excluded_not_surfaced(self):
        pull = _pull("Fixes #151", number=202)
        prs = [_pr(151, "closed", merged=True, merged_at=datetime(2026, 7, 14, 10, 0, 0, tzinfo=timezone.utc))]

        surfaced, excluded = detector.compute_gaps([pull], prs, now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "already-resolved-202-151"

    def test_closed_without_merging_target_is_also_excluded(self):
        pull = _pull("Resolves #152", number=204)
        prs = [_pr(152, "closed", merged=False)]

        surfaced, excluded = detector.compute_gaps([pull], prs, now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "already-resolved-204-152"

    def test_no_closing_keyword_is_excluded(self):
        pull = _pull("No linked PR, docs only.", number=203)

        surfaced, excluded = detector.compute_gaps([pull], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-closing-keyword-203"

    def test_self_reference_is_excluded_not_a_false_gap(self):
        pull = _pull("Closes #205 -- self-note only.", number=205)
        prs = [_pr(205, "open")]

        surfaced, excluded = detector.compute_gaps([pull], prs, now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "self-reference-205"

    def test_nonexistent_target_is_excluded_as_a_broken_link(self):
        pull = _pull("Closes #999", number=206)

        surfaced, excluded = detector.compute_gaps([pull], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "nonexistent-target-206-999"

    def test_two_closing_keywords_check_each_target_on_its_own_merits(self):
        pull = _pull("Closes #1 and fixes #2", number=300)
        prs = [_pr(1, "closed", merged=True, merged_at=datetime(2026, 7, 14, 0, 0, 0, tzinfo=timezone.utc)), _pr(2, "open")]

        surfaced, excluded = detector.compute_gaps([pull], prs, now=_NOW)

        surfaced_slugs = {g.slug for g in surfaced}
        excluded_slugs = {g.slug for g in excluded}
        assert "merged-pr-pr-still-open-300-2" in surfaced_slugs
        assert "already-resolved-300-1" in excluded_slugs


class TestLoadPullsAndPrs:
    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.MergedPull) for p in pulls)

    def test_load_prs_parses_the_real_fixture(self):
        prs = detector.load_prs()
        assert len(prs) > 0
        assert all(isinstance(p, detector.PullRequest) for p in prs)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pulls_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pulls(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_prs_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_prs(bad_file)


class TestRunRecipeScan:
    def test_runs_against_the_real_fixture_end_to_end(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["source"] == "fixture"
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"].startswith("merged-pr-pr-still-open-")
