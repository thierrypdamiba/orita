"""Tests for RECIPES/milestone-claims-dangling-milestone/detector.py's own
detection logic -- the eighty-seventh real recipe: a milestone's own
description claims a milestone number that doesn't exist at all.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "milestone-claims-dangling-milestone" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_milestone_claims_dangling_milestone_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 19, 14, 0, 0, tzinfo=timezone.utc)


def _milestone(
    number: int, description: str | None, *, state: str = "open",
) -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state,
        description=description or "",
        updated_at=_NOW,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


class TestClaimedMilestoneNumbersReuse:
    """This recipe reuses seam_engine.milestone_claims verbatim -- these
    tests prove the import actually happened, not a second retyped copy."""

    def test_milestone_hash_n(self):
        assert detector._claimed_milestone_numbers("milestone #7501 shipped.") == [7501]

    def test_bare_hash_n_with_no_milestone_word_is_never_extracted(self):
        assert detector._claimed_milestone_numbers("see #7502 for background.") == []


class TestComputeGaps:
    def test_a_claim_naming_a_milestone_that_does_not_exist_is_surfaced(self):
        milestones = [_milestone(1, "blocked on milestone #7501")]
        surfaced, excluded = detector.compute_gaps(milestones, now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-claims-dangling-milestone-1-7501"
        assert surfaced[0].confidence == 0.8

    def test_confidence_is_flat_regardless_of_which_milestone_claims(self):
        milestones = [
            _milestone(1, "blocked on milestone #7503"),
            _milestone(2, "blocked on milestone #7504"),
        ]
        surfaced, _ = detector.compute_gaps(milestones, now=_NOW)

        assert {g.confidence for g in surfaced} == {0.8}

    def test_a_claim_naming_a_real_open_milestone_is_excluded_not_surfaced(self):
        milestones = [
            _milestone(1, "follows milestone #2"),
            _milestone(2, None, state="open"),
        ]
        surfaced, excluded = detector.compute_gaps(milestones, now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-exists-milestone-1-2" in excluded_slugs

    def test_a_claim_naming_a_real_closed_milestone_is_also_excluded(self):
        milestones = [
            _milestone(1, "rolls in milestone #2, already done"),
            _milestone(2, None, state="closed"),
        ]
        surfaced, excluded = detector.compute_gaps(milestones, now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-exists-milestone-1-2" in excluded_slugs

    def test_a_milestone_claiming_itself_is_excluded_not_surfaced(self):
        milestones = [_milestone(1, "this is milestone #1 itself")]
        surfaced, excluded = detector.compute_gaps(milestones, now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "self-claim-milestone-1" in excluded_slugs

    def test_a_description_with_no_claim_phrase_produces_no_candidate_at_all(self):
        milestones = [_milestone(1, "housekeeping only, see #7505 for background")]
        surfaced, excluded = detector.compute_gaps(milestones, now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_milestone_with_no_description_at_all_produces_no_candidate_at_all(self):
        milestones = [_milestone(1, None)]
        surfaced, excluded = detector.compute_gaps(milestones, now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_duplicate_claim_in_one_description_produces_one_candidate_not_two(self):
        milestones = [_milestone(1, "milestone #7501 and milestone #7501 again")]
        surfaced, excluded = detector.compute_gaps(milestones, now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-claims-dangling-milestone-1-7501"

    def test_a_bare_hash_aside_alongside_a_real_claim_does_not_produce_a_second_candidate(self):
        milestones = [
            _milestone(1, "waits on milestone #2 to close. see #7999 for background."),
            _milestone(2, None, state="open"),
        ]
        surfaced, excluded = detector.compute_gaps(milestones, now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-exists-milestone-1-2" in excluded_slugs
        assert not any("7999" in s for s in excluded_slugs)


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "milestone-claims-dangling-milestone-90-9901"
        assert result["primary_gap"]["confidence"] == 0.8

    def test_the_shipped_fixture_excludes_the_real_claims_and_the_self_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claimed-milestone-exists-milestone-91-92" in excluded_slugs
        assert "claimed-milestone-exists-milestone-92-93" in excluded_slugs
        assert "self-claim-milestone-96" in excluded_slugs
        assert "claimed-milestone-exists-milestone-97-92" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_9901_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("milestone-claims-dangling-milestone-90-9901") == 1

    def test_the_shipped_fixture_never_examines_the_description_free_milestones_as_claimants(self):
        # 93 and 94 both carry no description at all, so neither is ever a
        # CLAIMANT (the first number in every slug this recipe emits) --
        # 93 legitimately still appears as milestone #92's real claim
        # TARGET (claimed-milestone-exists-milestone-92-93), which is not
        # the same thing as 93 itself being examined.
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {g["slug"] for g in result["excluded"]}
        all_slugs |= {g["slug"] for g in result["tail"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        assert not any(s.startswith("self-claim-milestone-93") or "-milestone-93-" in s for s in all_slugs)
        assert not any(s.startswith("self-claim-milestone-94") or "-milestone-94-" in s for s in all_slugs)

    def test_source_is_honestly_marked_fixture(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["source"] == "fixture"


class TestLoaders:
    """load_milestones -- mirrors every prior recipe's own _load_rows
    guard against syntactically valid but non-list JSON."""

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    def test_load_milestones_treats_a_null_description_as_empty_string(self):
        milestones = detector.load_milestones()
        m93 = next(m for m in milestones if m.number == 93)
        assert m93.description == ""

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_milestones_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(bad_file)
