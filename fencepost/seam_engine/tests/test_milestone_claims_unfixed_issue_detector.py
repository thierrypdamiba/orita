"""Tests for RECIPES/milestone-claims-unfixed-issue/detector.py's own
detection logic -- the forty-fifth real recipe: a milestone's own
description names a real GitHub closing keyword against an issue, but
the named issue is still open.

Loaded the same way `seam_engine.recipes.load_detector` loads any
recipe's detector at runtime (`importlib.util.spec_from_file_location`),
so this test exercises the exact module a live scan would import, not a
copy -- same discipline as every sibling detector test in this engine.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "milestone-claims-unfixed-issue" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_milestone_claims_unfixed_issue_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)


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


def _issue(number: int, state: str = "open") -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestClaimedIssueNumbers:
    """`_claimed_issue_numbers` is imported verbatim from
    `seam_engine.closing_keywords` -- not retyped -- so these tests exist
    to prove the import wiring actually reaches the shared grammar, not
    to re-prove the regex itself (already covered by the module it lives
    in and by the four sibling recipes that import it too)."""

    def test_fixes_hash_n(self):
        assert detector._claimed_issue_numbers("Fixes #201.") == [201]

    def test_closes_hash_n(self):
        assert detector._claimed_issue_numbers("Closes #202.") == [202]

    def test_resolves_hash_n(self):
        assert detector._claimed_issue_numbers("Resolves #203.") == [203]

    def test_past_tense_also_matches(self):
        assert detector._claimed_issue_numbers("Fixed #204. Closed #205. Resolved #206.") == [204, 205, 206]

    def test_case_insensitive(self):
        assert detector._claimed_issue_numbers("FIXES #201.") == [201]

    def test_bare_hash_n_with_no_keyword_is_never_extracted(self):
        assert detector._claimed_issue_numbers("See #205 for background.") == []

    def test_present_participle_closing_never_matches_iron_rule_8_safe_phrasing(self):
        # "closing #N" is the safe present-participle form Iron Rule #8
        # prescribes for prose that must discuss this pattern without
        # triggering it -- proven not to match here, live, not just
        # claimed.
        assert detector._claimed_issue_numbers("Closing #201 in prose only.") == []


class TestConfidenceFor:
    def test_a_claim_touched_recently_scores_the_lower_bar(self):
        updated = datetime(2026, 8, 4, 10, 0, 0, tzinfo=timezone.utc)  # 2h before NOW
        assert detector._confidence_for(updated, now=_NOW) == 0.55

    def test_a_claim_untouched_for_a_full_day_scores_the_higher_bar(self):
        updated = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)  # 72h before NOW
        assert detector._confidence_for(updated, now=_NOW) == 0.85

    def test_exactly_the_grace_window_boundary_scores_the_higher_bar(self):
        updated = datetime(2026, 8, 3, 12, 0, 0, tzinfo=timezone.utc)  # exactly 24h
        assert detector._confidence_for(updated, now=_NOW) == 0.85

    def test_just_under_the_grace_window_scores_the_lower_bar(self):
        updated = datetime(2026, 8, 3, 12, 0, 1, tzinfo=timezone.utc)  # 23h59m59s
        assert detector._confidence_for(updated, now=_NOW) == 0.55

    def test_grace_window_constant_is_twenty_four_hours(self):
        assert detector._EDIT_GRACE_WINDOW_HOURS == 24.0


class TestComputeGaps:
    def test_an_open_claim_is_surfaced_at_the_stale_bar_past_grace(self):
        milestones = [_milestone(1, "fixes #201", hours_ago=100.0)]
        surfaced, excluded = detector.compute_gaps(milestones, [_issue(201)], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-claims-unfixed-issue-1-201"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_open_claim_scores_the_lower_bar(self):
        milestones = [_milestone(1, "fixes #201", hours_ago=2.0)]
        surfaced, excluded = detector.compute_gaps(milestones, [_issue(201)], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.55

    def test_a_claim_about_a_closed_issue_is_excluded_not_surfaced(self):
        milestones = [_milestone(1, "closes #201")]
        surfaced, excluded = detector.compute_gaps(milestones, [_issue(201, state="closed")], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "claim-true-milestone-1-201"
        assert excluded[0].confidence == 0.0

    def test_a_claim_about_a_nonexistent_issue_is_excluded_not_surfaced(self):
        milestones = [_milestone(1, "fixes #9999")]
        surfaced, excluded = detector.compute_gaps(milestones, [], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "claimed-issue-not-found-milestone-1-9999"
        assert excluded[0].confidence == 0.0

    def test_a_milestone_with_no_description_produces_no_candidate_at_all(self):
        milestones = [_milestone(1, None)]
        surfaced, excluded = detector.compute_gaps(milestones, [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_milestone_with_an_empty_description_produces_no_candidate_at_all(self):
        milestones = [_milestone(1, "")]
        surfaced, excluded = detector.compute_gaps(milestones, [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_description_with_no_closing_keyword_produces_no_candidate_at_all(self):
        milestones = [_milestone(1, "housekeeping, nothing to see")]
        surfaced, excluded = detector.compute_gaps(milestones, [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_present_participle_only_produces_no_candidate_at_all(self):
        milestones = [_milestone(1, "closing #201 slowly")]
        surfaced, excluded = detector.compute_gaps(milestones, [_issue(201)], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_two_claims_in_one_description_are_judged_independently(self):
        milestones = [_milestone(1, "fixes #201 and closes #202")]
        surfaced, excluded = detector.compute_gaps(
            milestones, [_issue(201, state="closed"), _issue(202)], now=_NOW,
        )

        assert len(excluded) == 1 and excluded[0].slug == "claim-true-milestone-1-201"
        assert len(surfaced) == 1 and surfaced[0].slug == "milestone-claims-unfixed-issue-1-202"

    def test_the_same_claimed_number_mentioned_twice_produces_only_one_candidate(self):
        # Task 442's dedup discipline, applied here too -- without it, a
        # description naming #201 twice via two different keywords would
        # produce two identical GapCandidates that tie each other out of
        # rank()'s SEPARATION_MARGIN, silently dropping a real gap.
        milestones = [_milestone(1, "fixes #201, also closes #201")]
        surfaced, excluded = detector.compute_gaps(milestones, [_issue(201)], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-claims-unfixed-issue-1-201"

    def test_multiple_milestones_are_judged_independently_in_number_order(self):
        milestones = [
            _milestone(2, "fixes #999", hours_ago=100.0),
            _milestone(1, "closes #201"),
        ]
        surfaced, excluded = detector.compute_gaps(
            milestones, [_issue(201, state="closed"), _issue(999)], now=_NOW,
        )

        assert len(excluded) == 1 and excluded[0].slug == "claim-true-milestone-1-201"
        assert len(surfaced) == 1 and surfaced[0].slug == "milestone-claims-unfixed-issue-2-999"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert result["source"] == "fixture"
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "milestone-claims-unfixed-issue-60-601"
        assert result["primary_gap"]["confidence"] >= result["confidence_bar"]

    def test_the_shipped_fixture_weighs_one_coincidence_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "milestone-claims-unfixed-issue-61-602" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_claim_and_the_missing_issue(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {e["slug"] for e in result["excluded"]}
        assert "claim-true-milestone-62-603" in excluded_slugs
        assert "claimed-issue-not-found-milestone-63-9999" in excluded_slugs

    def test_the_shipped_fixture_has_no_candidate_for_the_no_op_milestones(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {e["slug"] for e in result["excluded"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        all_slugs |= {g["slug"] for g in result["tail"]}
        assert not any("-64-" in s for s in all_slugs)
        assert not any("-65-" in s for s in all_slugs)
        assert not any("-66-" in s for s in all_slugs)


class TestLoaders:
    """load_milestones/load_issues -- proves each loader parses the real
    shipped fixture, and each refuses a syntactically valid but non-list
    JSON payload with a named ValueError rather than a bare TypeError
    three frames deeper (the same bug class task 358/359 closed on this
    engine's other loaders, built in here from the start)."""

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    def test_load_milestones_treats_a_null_description_as_empty_string(self):
        milestones = detector.load_milestones()
        m64 = next(m for m in milestones if m.number == 64)
        assert m64.description == ""

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
