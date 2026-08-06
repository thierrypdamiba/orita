"""Tests for RECIPES/milestone-claims-unmerged-pr/detector.py's own
detection logic -- the fiftieth real recipe: a milestone's own
description names a real ships/includes/merges/via #N PR-claim phrase,
but the named PR never actually merged.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "milestone-claims-unmerged-pr" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_milestone_claims_unmerged_pr_test", DETECTOR_PATH)
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


def _pull(number: int, *, state: str = "open", merged: bool = False) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, merged=merged,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestClaimedPrNumbers:
    """`_claimed_pr_numbers` is imported verbatim from
    `seam_engine.pr_claims` -- not retyped -- so these tests exist to
    prove the import wiring actually reaches the shared grammar, not to
    re-prove the regex itself (already covered by the module it lives in
    and by the four sibling recipes that import it too)."""

    def test_ships_hash_n(self):
        assert detector._claimed_pr_numbers("Ships #301.") == [301]

    def test_includes_hash_n(self):
        assert detector._claimed_pr_numbers("Includes #302.") == [302]

    def test_merges_hash_n(self):
        assert detector._claimed_pr_numbers("Merges #303.") == [303]

    def test_via_hash_n(self):
        assert detector._claimed_pr_numbers("Ships via #304.") == [304]

    def test_case_insensitive(self):
        assert detector._claimed_pr_numbers("SHIPS #301.") == [301]

    def test_bare_hash_n_with_no_claim_verb_is_never_extracted(self):
        assert detector._claimed_pr_numbers("See #305 for background.") == []


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
    def test_an_unmerged_claim_is_surfaced_at_the_stale_bar_past_grace(self):
        milestones = [_milestone(1, "ships #301", hours_ago=100.0)]
        surfaced, excluded = detector.compute_gaps(milestones, [_pull(301)], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-claims-unmerged-pr-1-301"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_unmerged_claim_scores_the_lower_bar(self):
        milestones = [_milestone(1, "ships #301", hours_ago=2.0)]
        surfaced, excluded = detector.compute_gaps(milestones, [_pull(301)], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.55

    def test_a_claim_about_a_merged_pr_is_excluded_not_surfaced(self):
        milestones = [_milestone(1, "merges #301")]
        surfaced, excluded = detector.compute_gaps(
            milestones, [_pull(301, state="closed", merged=True)], now=_NOW,
        )

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "claim-true-milestone-1-301"
        assert excluded[0].confidence == 0.0

    def test_a_claim_about_a_closed_not_merged_pr_is_still_surfaced(self):
        milestones = [_milestone(1, "ships #301", hours_ago=100.0)]
        surfaced, excluded = detector.compute_gaps(
            milestones, [_pull(301, state="closed", merged=False)], now=_NOW,
        )

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-claims-unmerged-pr-1-301"

    def test_a_claim_about_a_nonexistent_pr_is_excluded_not_surfaced(self):
        milestones = [_milestone(1, "ships #9999")]
        surfaced, excluded = detector.compute_gaps(milestones, [], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "claimed-pr-not-found-milestone-1-9999"
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

    def test_a_description_with_no_claim_phrase_produces_no_candidate_at_all(self):
        milestones = [_milestone(1, "housekeeping, nothing to see")]
        surfaced, excluded = detector.compute_gaps(milestones, [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_bare_hash_n_with_no_claim_verb_produces_no_candidate_at_all(self):
        milestones = [_milestone(1, "see #301 for background")]
        surfaced, excluded = detector.compute_gaps(milestones, [_pull(301)], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_two_claims_in_one_description_are_judged_independently(self):
        milestones = [_milestone(1, "ships #301 and merges #302")]
        surfaced, excluded = detector.compute_gaps(
            milestones, [_pull(301, state="closed", merged=True), _pull(302)], now=_NOW,
        )

        assert len(excluded) == 1 and excluded[0].slug == "claim-true-milestone-1-301"
        assert len(surfaced) == 1 and surfaced[0].slug == "milestone-claims-unmerged-pr-1-302"

    def test_the_same_claimed_number_mentioned_twice_produces_only_one_candidate(self):
        # Task 442's dedup discipline, applied here too -- without it, a
        # description naming #301 twice via two different verbs would
        # produce two identical GapCandidates that tie each other out of
        # rank()'s SEPARATION_MARGIN, silently dropping a real gap.
        milestones = [_milestone(1, "ships #301, also includes #301")]
        surfaced, excluded = detector.compute_gaps(milestones, [_pull(301)], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-claims-unmerged-pr-1-301"

    def test_multiple_milestones_are_judged_independently_in_number_order(self):
        milestones = [
            _milestone(2, "ships #999", hours_ago=100.0),
            _milestone(1, "merges #301"),
        ]
        surfaced, excluded = detector.compute_gaps(
            milestones, [_pull(301, state="closed", merged=True), _pull(999)], now=_NOW,
        )

        assert len(excluded) == 1 and excluded[0].slug == "claim-true-milestone-1-301"
        assert len(surfaced) == 1 and surfaced[0].slug == "milestone-claims-unmerged-pr-2-999"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert result["source"] == "fixture"
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "milestone-claims-unmerged-pr-70-901"
        assert result["primary_gap"]["confidence"] >= result["confidence_bar"]

    def test_the_shipped_fixture_weighs_one_coincidence_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "milestone-claims-unmerged-pr-71-903" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_claim_and_the_missing_pr(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {e["slug"] for e in result["excluded"]}
        assert "claim-true-milestone-72-902" in excluded_slugs
        assert "claimed-pr-not-found-milestone-73-9999" in excluded_slugs

    def test_the_shipped_fixture_has_no_candidate_for_the_no_op_milestones(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {e["slug"] for e in result["excluded"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        all_slugs |= {g["slug"] for g in result["tail"]}
        assert not any("-74-" in s for s in all_slugs)
        assert not any("-75-" in s for s in all_slugs)
        assert not any("-76-" in s for s in all_slugs)


class TestLoaders:
    """load_milestones/load_pulls -- proves each loader parses the real
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
        m74 = next(m for m in milestones if m.number == 74)
        assert m74.description == ""

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
    def test_load_pulls_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pulls(bad_file)
