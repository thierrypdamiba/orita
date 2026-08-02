"""Tests for RECIPES/readme-claims-open-milestone/detector.py's own
detection logic (ROADMAP.md #491) -- the thirty-fifth real recipe:
README.md itself claims a milestone shipped, but the named milestone
never actually closed.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "readme-claims-open-milestone" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_readme_claims_open_milestone_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)


def _milestone(number: int, state: str = "open") -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


class TestClaimedMilestoneNumbers:
    """`_claimed_milestone_numbers` is imported verbatim from
    `seam_engine.milestone_claims` -- not retyped -- so these tests exist
    to prove the import wiring actually reaches the shared grammar, not to
    re-prove the regex itself (already covered by the module it lives in
    and by the two sibling recipes that import it too)."""

    def test_milestone_hash_n(self):
        assert detector._claimed_milestone_numbers("Milestone #7 shipped.") == [7]

    def test_case_insensitive(self):
        assert detector._claimed_milestone_numbers("MILESTONE #12 done.") == [12]

    def test_bare_hash_n_with_no_milestone_word_is_never_extracted(self):
        assert detector._claimed_milestone_numbers("See #13 for background.") == []

    def test_multiple_claims_in_one_readme(self):
        assert detector._claimed_milestone_numbers("Milestone #7. Milestone #12.") == [7, 12]

    def test_duplicate_claim_in_one_readme_is_not_deduplicated_at_extraction(self):
        # De-duplication happens in compute_gaps, not here -- this function
        # is a pure extraction, faithfully reporting every match.
        assert detector._claimed_milestone_numbers("Milestone #7 and milestone #7 again.") == [7, 7]


class TestComputeGaps:
    def test_an_open_claim_is_surfaced_at_flat_high_confidence(self):
        milestone = _milestone(12, state="open")

        surfaced, excluded = detector.compute_gaps("Milestone #12 shipped.", [milestone])

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "readme-claims-open-milestone-12"
        assert surfaced[0].confidence == 0.85

    def test_a_closed_claimed_milestone_is_excluded_not_surfaced(self):
        milestone = _milestone(7, state="closed")

        surfaced, excluded = detector.compute_gaps("Milestone #7 wrapped up.", [milestone])

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-readme-7" in excluded_slugs

    def test_a_claim_naming_a_milestone_that_does_not_exist_is_excluded_not_surfaced(self):
        surfaced, excluded = detector.compute_gaps("Milestone #99 shipped.", [])

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-not-found-readme-99" in excluded_slugs

    def test_a_readme_with_no_claim_phrase_produces_no_candidate_at_all(self):
        surfaced, excluded = detector.compute_gaps("Housekeeping only, see #13 for background.", [])

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-readme"

    def test_a_duplicate_claim_in_one_readme_produces_one_candidate_not_two(self):
        milestone = _milestone(7, state="open")

        surfaced, excluded = detector.compute_gaps(
            "Milestone #7 shipped and milestone #7 confirmed again.", [milestone]
        )

        assert len(surfaced) == 1
        assert surfaced[0].slug == "readme-claims-open-milestone-7"

    def test_multiple_distinct_open_claims_are_both_surfaced(self):
        surfaced, excluded = detector.compute_gaps(
            "Milestone #7 shipped. Milestone #12 shipped.",
            [_milestone(7, state="open"), _milestone(12, state="open")],
        )

        assert excluded == []
        slugs = {g.slug for g in surfaced}
        assert slugs == {"readme-claims-open-milestone-7", "readme-claims-open-milestone-12"}


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "readme-claims-open-milestone-12"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_excludes_the_true_claim_and_the_dangling_reference(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-readme-7" in excluded_slugs
        assert "claimed-milestone-not-found-readme-99" in excluded_slugs

    def test_the_shipped_fixture_produces_an_empty_tail(self):
        # Only one genuine open claim exists in the shipped fixture, so
        # nothing is left over to weigh in the tail once it is elected
        # primary.
        result = detector.run_recipe_scan(now=_NOW)
        assert result["tail"] == []


class TestLoaders:
    """load_readme/load_milestones -- proves each loader parses the real
    shipped fixture, and each refuses a syntactically valid but
    wrong-shaped JSON payload with a named ValueError rather than a bare
    crash three frames deeper -- the same discipline every other loader in
    this engine already holds itself to."""

    def test_load_readme_parses_the_real_fixture(self):
        content = detector.load_readme()
        assert isinstance(content, str)
        assert "Milestone #12" in content

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    @pytest.mark.parametrize("bad_value", [[1, 2], 5, None, "x", True])
    def test_load_readme_raises_named_error_not_typeerror_when_json_is_not_an_object(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON object"):
            detector.load_readme(bad_file)

    def test_load_readme_raises_named_error_when_content_field_is_not_a_string(self, tmp_path: Path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps({"path": "README.md", "content": 5}))
        with pytest.raises(ValueError, match="expected a string 'content' field"):
            detector.load_readme(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_milestones_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(bad_file)
