"""Tests for RECIPES/issue-body-claims-dangling-milestone/detector.py's own
detection logic -- the ninety-fifth real recipe: an issue or pull request's
own OPENING BODY claims a milestone number that doesn't exist at all.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "issue-body-claims-dangling-milestone" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_issue_body_claims_dangling_milestone_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)


def _issue(number: int, body: str | None, updated_at: datetime) -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state="open", body=body or "",
        updated_at=updated_at,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


def _pull(number: int, body: str | None, updated_at: datetime) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state="open", body=body or "",
        updated_at=updated_at,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


def _milestone(number: int, state: str = "open") -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


class TestClaimedMilestoneNumbersReuse:
    """This recipe reuses seam_engine.milestone_claims verbatim -- these
    tests prove the import actually happened, not a second retyped copy."""

    def test_milestone_hash_n(self):
        assert detector._claimed_milestone_numbers("Milestone #9301 shipped.") == [9301]

    def test_bare_hash_n_with_no_milestone_word_is_never_extracted(self):
        assert detector._claimed_milestone_numbers("See #9302 for background.") == []


class TestComputeGaps:
    def test_an_issue_body_claim_naming_a_missing_milestone_is_surfaced(self):
        issue = _issue(101, "Milestone #9301 shipped.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([issue], [], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-body-claims-dangling-milestone-issue-101-9301"
        assert surfaced[0].confidence == 0.8

    def test_a_pr_body_claim_naming_a_missing_milestone_is_surfaced_too(self):
        pull = _pull(201, "Closes out milestone #9302 too.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([], [pull], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-body-claims-dangling-milestone-pr-201-9302"
        assert surfaced[0].confidence == 0.8

    def test_confidence_is_flat_regardless_of_record_age(self):
        fresh = _issue(102, "Milestone #9303 shipped.", _NOW - timedelta(minutes=5))
        stale = _issue(103, "Milestone #9304 shipped.", _NOW - timedelta(days=365))

        surfaced, _ = detector.compute_gaps([fresh, stale], [], [], now=_NOW)

        assert {g.confidence for g in surfaced} == {0.8}

    def test_a_claim_naming_a_real_open_milestone_is_excluded_not_surfaced(self):
        issue = _issue(104, "Milestone #9305 shipped.", _NOW - timedelta(hours=1))
        milestone = _milestone(9305, state="open")

        surfaced, excluded = detector.compute_gaps([issue], [], [milestone], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-exists-issue-104-9305" in excluded_slugs

    def test_a_claim_naming_a_real_closed_milestone_is_also_excluded(self):
        pull = _pull(202, "Milestone #9306 shipped.", _NOW - timedelta(hours=1))
        milestone = _milestone(9306, state="closed")

        surfaced, excluded = detector.compute_gaps([], [pull], [milestone], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-exists-pr-202-9306" in excluded_slugs

    def test_a_body_with_no_claim_phrase_produces_no_candidate_at_all(self):
        issue = _issue(105, "Housekeeping only, see #9307 for background.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([issue], [], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_body_with_no_text_at_all_produces_no_candidate_at_all(self):
        issue = _issue(106, None, _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([issue], [], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_duplicate_claim_in_one_body_produces_one_candidate_not_two(self):
        issue = _issue(107, "Milestone #9301 and milestone #9301 again.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([issue], [], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-body-claims-dangling-milestone-issue-107-9301"

    def test_a_bare_hash_mention_alongside_a_real_claim_does_not_produce_a_second_candidate(self):
        issue = _issue(108, "Milestone #9301 shipped. See #9999 for background.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([issue], [], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-body-claims-dangling-milestone-issue-108-9301"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "issue-body-claims-dangling-milestone-issue-80-8999"
        assert result["primary_gap"]["confidence"] == 0.8

    def test_the_shipped_fixture_excludes_the_real_claims_on_both_issue_and_pr_paths(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claimed-milestone-exists-issue-81-8301" in excluded_slugs
        assert "claimed-milestone-exists-issue-82-8302" in excluded_slugs
        assert "claimed-milestone-exists-pr-56-8301" in excluded_slugs
        assert "claimed-milestone-exists-pr-57-8302" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_8999_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("issue-body-claims-dangling-milestone-issue-80-8999") == 1

    def test_the_shipped_fixture_never_examines_the_bare_reference_or_blank_body_issues(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {g["slug"] for g in result["excluded"]}
        all_slugs |= {g["slug"] for g in result["tail"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        assert not any("-83-" in s for s in all_slugs)
        assert not any("-84-" in s for s in all_slugs)

    def test_source_is_honestly_marked_fixture(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["source"] == "fixture"


class TestLoaders:
    """load_issues/load_pulls/load_milestones -- mirrors every prior
    recipe's own _load_rows guard against syntactically valid but non-list
    JSON."""

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pulls)

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

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

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_milestones_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(bad_file)
