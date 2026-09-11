"""Tests for RECIPES/repo-description-claims-open-milestone/detector.py's
own detection logic (ROADMAP.md #1407) -- the hundred-ninth real recipe:
the repository's own one-line description names a "milestone #N shipped"
claim phrase, but the named milestone is still open.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "repo-description-claims-open-milestone" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_repo_description_claims_open_milestone_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 9, 11, 14, 0, 0, tzinfo=timezone.utc)


def _milestone(number: int, state: str = "open") -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


class TestClaimedMilestoneNumbers:
    """`_claimed_milestone_numbers` is imported verbatim from
    `seam_engine.milestone_claims` -- not retyped -- so these tests exist
    to prove the import wiring actually reaches the shared grammar, not to
    re-prove the regex itself."""

    def test_milestone_hash_n_is_extracted(self):
        assert detector._claimed_milestone_numbers("Milestone #7 shipped.") == [7]

    def test_bare_hash_n_with_no_milestone_word_is_never_extracted(self):
        assert detector._claimed_milestone_numbers("See #7 for background.") == []

    def test_multiple_distinct_claims_are_both_extracted(self):
        assert detector._claimed_milestone_numbers("Milestone #7 shipped. Milestone #42 shipped.") == [7, 42]


class TestComputeGaps:
    def test_an_open_claim_is_surfaced_at_flat_high_confidence(self):
        milestone = _milestone(12, state="open")

        surfaced, excluded = detector.compute_gaps("Milestone #12 shipped.", [milestone])

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "repo-description-claims-open-milestone-12"
        assert surfaced[0].confidence == 0.85

    def test_a_closed_claimed_milestone_is_excluded_not_surfaced(self):
        milestone = _milestone(7, state="closed")

        surfaced, excluded = detector.compute_gaps("Milestone #7 wrapped up.", [milestone])

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-repo-description-7" in excluded_slugs

    def test_a_claim_naming_a_milestone_that_does_not_exist_is_excluded_not_surfaced(self):
        surfaced, excluded = detector.compute_gaps("Milestone #99 shipped.", [])

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-not-found-repo-description-99" in excluded_slugs

    def test_a_description_with_no_claim_phrase_produces_no_candidate_at_all(self):
        surfaced, excluded = detector.compute_gaps("A small example repo, see #205 for background.", [])

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-repo-description"

    def test_a_none_description_is_excluded_as_no_description(self):
        surfaced, excluded = detector.compute_gaps(None, [])

        assert surfaced == []
        assert excluded == [
            detector.GapCandidate(
                slug="no-description",
                headline="This repository carries no description",
                detail="GetRepository's own description field reads null. No seam here.",
                confidence=0.0,
                evidence=[],
            )
        ]

    def test_a_duplicate_claim_in_one_description_produces_one_candidate_not_two(self):
        milestone = _milestone(7, state="open")

        surfaced, excluded = detector.compute_gaps(
            "Milestone #7 shipped and milestone #7 confirmed again.", [milestone]
        )

        assert len(surfaced) == 1
        assert surfaced[0].slug == "repo-description-claims-open-milestone-7"

    def test_multiple_distinct_open_claims_are_both_surfaced(self):
        surfaced, excluded = detector.compute_gaps(
            "Milestone #7 shipped. Milestone #12 shipped.",
            [_milestone(7, state="open"), _milestone(12, state="open")],
        )

        assert excluded == []
        slugs = {g.slug for g in surfaced}
        assert slugs == {
            "repo-description-claims-open-milestone-7",
            "repo-description-claims-open-milestone-12",
        }


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "repo-description-claims-open-milestone-12"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_excludes_the_true_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-repo-description-7" in excluded_slugs

    def test_the_shipped_fixture_produces_an_empty_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["tail"] == []


class TestLoaders:
    """load_description/load_milestones -- proves each loader parses the
    real shipped fixture, and each refuses a syntactically valid but
    wrong-shaped JSON payload with a named ValueError rather than a bare
    crash three frames deeper -- the same discipline every other loader in
    this engine already holds itself to."""

    def test_load_description_parses_the_real_fixture(self):
        description = detector.load_description()
        assert isinstance(description, str)
        assert "milestone #12" in description.lower()

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    def test_load_description_returns_none_for_a_null_field(self, tmp_path: Path):
        f = tmp_path / "repository.json"
        f.write_text(json.dumps({"full_name": "x/y", "description": None, "url": "https://x"}))
        assert detector.load_description(f) is None

    @pytest.mark.parametrize("bad_value", [[1, 2], 5, None, "x", True])
    def test_load_description_raises_named_error_not_typeerror_when_json_is_not_an_object(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON object"):
            detector.load_description(bad_file)

    def test_load_description_raises_named_error_when_description_field_missing(self, tmp_path: Path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps({"full_name": "x/y", "url": "https://x"}))
        with pytest.raises(ValueError, match="expected a 'description' field"):
            detector.load_description(bad_file)

    def test_load_description_raises_named_error_when_description_field_is_wrong_type(self, tmp_path: Path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps({"full_name": "x/y", "description": 5, "url": "https://x"}))
        with pytest.raises(ValueError, match="expected 'description' to be a string or null"):
            detector.load_description(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_milestones_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(bad_file)
