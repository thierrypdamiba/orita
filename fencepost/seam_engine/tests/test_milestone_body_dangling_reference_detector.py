"""Tests for RECIPES/milestone-body-dangling-reference/detector.py's own
detection logic -- the forty-first real recipe, and the fifth and final
leg of the dangling-reference family (dangling-issue-reference watches
commit messages, mention-dangling-reference watches X mentions,
release-note-dangling-reference watches release notes, issue-body-
dangling-reference watches issue/PR bodies; this one watches a
milestone's own description).

Loaded the same way `seam_engine.recipes.load_detector` loads any
recipe's detector at runtime (`importlib.util.spec_from_file_location`),
so this test exercises the exact module a live scan would import, not a
copy -- same discipline as
`test_issue_body_dangling_reference_detector.py` and every sibling
detector test in this engine.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "milestone-body-dangling-reference" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_milestone_body_dangling_reference_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)


def _milestone(
    number: int, description: str | None, *, state: str = "open", hours_ago: float = 100.0,
) -> "detector.Milestone":
    updated = _NOW.timestamp() - hours_ago * 3600
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state,
        description=description or "",
        updated_at=datetime.fromtimestamp(updated, tz=timezone.utc),
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


def _issue(number: int) -> "detector.Issue":
    return detector.Issue(number=number, url=f"https://github.com/example/example-repo/issues/{number}")


def _pull(number: int) -> "detector.PullRequest":
    return detector.PullRequest(number=number, url=f"https://github.com/example/example-repo/pull/{number}")


class TestConfidenceFor:
    def test_a_description_touched_recently_scores_the_lower_bar(self):
        updated = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)  # 2h before NOW
        assert detector._confidence_for(updated, now=_NOW) == 0.55

    def test_a_description_untouched_for_a_full_day_scores_the_higher_bar(self):
        updated = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)  # 72h before NOW
        assert detector._confidence_for(updated, now=_NOW) == 0.85

    def test_exactly_the_grace_window_boundary_scores_the_higher_bar(self):
        updated = datetime(2026, 7, 31, 12, 0, 0, tzinfo=timezone.utc)  # exactly 24h
        assert detector._confidence_for(updated, now=_NOW) == 0.85

    def test_just_under_the_grace_window_scores_the_lower_bar(self):
        updated = datetime(2026, 7, 31, 12, 0, 1, tzinfo=timezone.utc)  # 23h59m59s
        assert detector._confidence_for(updated, now=_NOW) == 0.55

    def test_grace_window_constant_is_twenty_four_hours(self):
        assert detector._EDIT_GRACE_WINDOW_HOURS == 24.0


class TestComputeGaps:
    def test_a_reference_to_a_nonexistent_number_is_surfaced(self):
        milestones = [_milestone(1, "see #99 for context", hours_ago=100.0)]
        surfaced, excluded = detector.compute_gaps(milestones, [], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-body-dangling-reference-1-99"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_dangling_reference_scores_the_lower_bar(self):
        milestones = [_milestone(1, "see #99 for context", hours_ago=2.0)]
        surfaced, excluded = detector.compute_gaps(milestones, [], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.55

    def test_a_reference_matching_a_real_issue_is_excluded(self):
        milestones = [_milestone(1, "tracks #501")]
        surfaced, excluded = detector.compute_gaps(milestones, [_issue(501)], [], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "milestone-body-ref-matched-1-501"
        assert excluded[0].confidence == 0.0

    def test_a_reference_matching_a_merged_pr_is_excluded_not_surfaced(self):
        # The whole reason both lists are checked: GitHub shares one
        # number sequence between issues and PRs. Checking only issues
        # would misfire this as a false dangling-reference gap.
        milestones = [_milestone(1, "waiting on #40 to land")]
        surfaced, excluded = detector.compute_gaps(milestones, [], [_pull(40)], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "milestone-body-ref-matched-1-40"

    def test_a_milestone_with_no_description_produces_no_candidate_at_all(self):
        milestones = [_milestone(1, None)]
        surfaced, excluded = detector.compute_gaps(milestones, [], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_milestone_with_an_empty_description_produces_no_candidate_at_all(self):
        milestones = [_milestone(1, "")]
        surfaced, excluded = detector.compute_gaps(milestones, [], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_record_with_no_reference_produces_no_candidate_at_all(self):
        milestones = [_milestone(1, "housekeeping, nothing to see")]
        surfaced, excluded = detector.compute_gaps(milestones, [], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_cross_repo_reference_produces_no_candidate_at_all(self):
        milestones = [_milestone(1, "inspired by arcadeai/gasstation#42")]
        surfaced, excluded = detector.compute_gaps(milestones, [], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_two_references_in_one_description_are_judged_independently(self):
        milestones = [_milestone(1, "#501 is real but stray #999 isn't")]
        surfaced, excluded = detector.compute_gaps(milestones, [_issue(501)], [], now=_NOW)

        assert len(excluded) == 1 and excluded[0].slug == "milestone-body-ref-matched-1-501"
        assert len(surfaced) == 1 and surfaced[0].slug == "milestone-body-dangling-reference-1-999"

    def test_the_same_dangling_number_mentioned_twice_produces_only_one_candidate(self):
        # Task 442: referenced_numbers() returns every occurrence, repeats
        # included -- without a dedup, a description naming #2 twice
        # produced two identical GapCandidates that tied each other out of
        # rank()'s SEPARATION_MARGIN, silently dropping a real gap.
        milestones = [_milestone(1, "related to #2, also see #2 again")]
        surfaced, excluded = detector.compute_gaps(milestones, [], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-body-dangling-reference-1-2"

    def test_multiple_milestones_are_judged_independently_in_number_order(self):
        milestones = [
            _milestone(2, "see #999", hours_ago=100.0),
            _milestone(1, "see #501"),
        ]
        surfaced, excluded = detector.compute_gaps(milestones, [_issue(501)], [], now=_NOW)

        assert len(excluded) == 1 and excluded[0].slug == "milestone-body-ref-matched-1-501"
        assert len(surfaced) == 1 and surfaced[0].slug == "milestone-body-dangling-reference-2-999"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert result["source"] == "fixture"
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "milestone-body-dangling-reference-21-9999"
        assert result["primary_gap"]["confidence"] >= result["confidence_bar"]

    def test_the_shipped_fixture_weighs_one_coincidence_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "milestone-body-dangling-reference-22-8888" in tail_slugs

    def test_the_shipped_fixture_excludes_the_real_cross_references(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {e["slug"] for e in result["excluded"]}
        assert "milestone-body-ref-matched-20-501" in excluded_slugs
        assert "milestone-body-ref-matched-25-510" in excluded_slugs

    def test_the_shipped_fixture_has_no_candidate_for_the_no_op_milestones(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {e["slug"] for e in result["excluded"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        all_slugs |= {g["slug"] for g in result["tail"]}
        assert not any("-23-" in s for s in all_slugs)
        assert not any("-24-" in s for s in all_slugs)
        assert not any("-26-" in s for s in all_slugs)


class TestLoaders:
    """load_milestones/load_issues/load_pulls -- proves each loader parses
    the real shipped fixture, and each refuses a syntactically valid but
    non-list JSON payload with a named ValueError rather than a bare
    TypeError three frames deeper (the same bug class task 358/359 closed
    on this engine's other loaders, built in here from the start)."""

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    def test_load_milestones_treats_a_null_description_as_empty_string(self):
        milestones = detector.load_milestones()
        m23 = next(m for m in milestones if m.number == 23)
        assert m23.description == ""

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pulls)

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

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pulls_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pulls(bad_file)
