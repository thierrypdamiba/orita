"""Tests for RECIPES/readme-claims-dangling-milestone/detector.py's own
detection logic -- the eighty-eighth real recipe: README.md's own text
claims a milestone number that doesn't exist at all.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "readme-claims-dangling-milestone" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_readme_claims_dangling_milestone_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 19, 15, 0, 0, tzinfo=timezone.utc)


def _milestone(number: int, *, state: str = "open") -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


class TestClaimedMilestoneNumbersReuse:
    """This recipe reuses seam_engine.milestone_claims verbatim -- these
    tests prove the import actually happened, not an eighth retyped copy."""

    def test_milestone_hash_n(self):
        assert detector._claimed_milestone_numbers("milestone #8801 shipped.") == [8801]

    def test_bare_hash_n_with_no_milestone_word_is_never_extracted(self):
        assert detector._claimed_milestone_numbers("see #8802 for background.") == []

    def test_a_negated_claim_is_never_extracted(self):
        """The shared grammar's own negation check, inherited not retyped:
        a sentence denying a milestone was hit must not read as claiming
        it was."""
        assert detector._claimed_milestone_numbers("we have not hit milestone #8803.") == []


class TestComputeGaps:
    def test_a_claim_naming_a_milestone_that_does_not_exist_is_surfaced(self):
        surfaced, excluded = detector.compute_gaps(
            "milestone #8801 shipped.", [_milestone(1)]
        )

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "readme-claims-dangling-milestone-8801"
        assert surfaced[0].confidence == 0.8
        assert "#8801" in surfaced[0].headline

    def test_a_claim_naming_a_real_open_milestone_is_excluded_not_surfaced(self):
        """Whether a real milestone's claim is TRUE is
        readme-claims-open-milestone's own seam -- this recipe's exact
        inverse on the same surface -- not this one's."""
        surfaced, excluded = detector.compute_gaps(
            "milestone #4 shipped.", [_milestone(4, state="open")]
        )

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "claimed-milestone-exists-readme-4"
        assert excluded[0].confidence == 0.0
        assert "readme-claims-open-milestone" in excluded[0].detail

    def test_a_claim_naming_a_real_closed_milestone_is_excluded_too(self):
        """The exclusion does not depend on the target's state: the seam
        is resolution, not truth."""
        surfaced, excluded = detector.compute_gaps(
            "milestone #4 shipped.", [_milestone(4, state="closed")]
        )

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "claimed-milestone-exists-readme-4"
        assert "'closed'" in excluded[0].detail

    def test_the_real_milestones_url_is_the_excluded_candidates_evidence(self):
        surfaced, excluded = detector.compute_gaps(
            "milestone #4 shipped.", [_milestone(4)]
        )

        assert excluded[0].evidence == [
            "https://github.com/example/example-repo/milestone/4"
        ]

    def test_a_readme_with_no_claim_phrase_is_named_as_an_exclusion(self):
        """Named, not two silent empties -- the same shape
        readme-claims-open-milestone.compute_gaps already holds for this
        surface."""
        surfaced, excluded = detector.compute_gaps(
            "Nine gods run a town. See #8802 for background.", [_milestone(1)]
        )

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "no-claim-phrase-readme"
        assert excluded[0].confidence == 0.0

    def test_an_empty_readme_is_named_as_an_exclusion_too(self):
        surfaced, excluded = detector.compute_gaps("", [_milestone(1)])

        assert surfaced == []
        assert [g.slug for g in excluded] == ["no-claim-phrase-readme"]

    def test_the_same_claim_written_twice_is_deduplicated_to_one_candidate(self):
        """Two identical GapCandidates would tie each other out of rank()'s
        SEPARATION_MARGIN -- the guard every dangling-milestone sibling
        already holds."""
        surfaced, excluded = detector.compute_gaps(
            "milestone #8801 shipped. And again: milestone #8801 shipped.",
            [_milestone(1)],
        )

        assert len(surfaced) == 1
        assert surfaced[0].slug == "readme-claims-dangling-milestone-8801"

    def test_a_negated_claim_never_becomes_a_candidate(self):
        surfaced, excluded = detector.compute_gaps(
            "we have not hit milestone #8803 this cycle.", [_milestone(1)]
        )

        assert surfaced == []
        assert [g.slug for g in excluded] == ["no-claim-phrase-readme"]

    def test_a_bare_hash_n_is_never_read_as_a_milestone_claim(self):
        """readme-dangling-reference's number space, not this one's: a
        milestone lives in a separate sequence, and conflating them is the
        false positive Ogun's law calls fatal."""
        surfaced, excluded = detector.compute_gaps(
            "The gate's own count lives in #4, which is an issue.", [_milestone(1)]
        )

        assert surfaced == []
        assert [g.slug for g in excluded] == ["no-claim-phrase-readme"]

    def test_a_real_and_a_dangling_claim_in_one_readme_split_correctly(self):
        surfaced, excluded = detector.compute_gaps(
            "milestone #4 shipped. milestone #8801 shipped too.", [_milestone(4)]
        )

        assert [g.slug for g in surfaced] == ["readme-claims-dangling-milestone-8801"]
        assert [g.slug for g in excluded] == ["claimed-milestone-exists-readme-4"]

    def test_two_distinct_dangling_claims_both_surface(self):
        surfaced, _ = detector.compute_gaps(
            "milestone #8801 shipped. milestone #8804 shipped.", [_milestone(1)]
        )

        assert {g.slug for g in surfaced} == {
            "readme-claims-dangling-milestone-8801",
            "readme-claims-dangling-milestone-8804",
        }

    def test_an_empty_milestone_list_makes_every_claim_dangling(self):
        surfaced, excluded = detector.compute_gaps("milestone #4 shipped.", [])

        assert excluded == []
        assert [g.slug for g in surfaced] == ["readme-claims-dangling-milestone-4"]

    def test_a_surfaced_candidate_carries_no_evidence_url(self):
        """There is no milestone to point at -- that is the whole seam.
        Pointing at a URL that resolves to nothing would be worse than
        pointing at nothing."""
        surfaced, _ = detector.compute_gaps("milestone #8801 shipped.", [_milestone(1)])

        assert surfaced[0].evidence == []

    def test_no_self_claim_exclusion_exists_on_this_surface(self):
        """Deliberate, not an oversight: README.md carries no milestone
        number of its own, so unlike the milestone-sourced sibling there is
        no second record for a claim to collapse into. Every claim here is
        about some other record by construction."""
        surfaced, excluded = detector.compute_gaps("milestone #8801 shipped.", [])

        assert not any("self-claim" in g.slug for g in surfaced + excluded)


class TestLoaders:
    def test_load_readme_reads_the_shipped_fixture(self):
        content = detector.load_readme()

        assert "milestone #204" in content.lower()

    def test_load_milestones_reads_the_shipped_fixture(self):
        milestones = detector.load_milestones()

        assert {m.number for m in milestones} == {7, 12}

    def test_load_readme_refuses_a_non_object_payload(self, tmp_path):
        p = tmp_path / "readme.json"
        p.write_text(json.dumps(["not", "an", "object"]))

        with pytest.raises(ValueError, match="expected a JSON object"):
            detector.load_readme(p)

    def test_load_readme_refuses_a_missing_content_field(self, tmp_path):
        p = tmp_path / "readme.json"
        p.write_text(json.dumps({"path": "README.md"}))

        with pytest.raises(ValueError, match="expected a string 'content' field"):
            detector.load_readme(p)

    def test_load_readme_refuses_a_non_string_content_field(self, tmp_path):
        p = tmp_path / "readme.json"
        p.write_text(json.dumps({"path": "README.md", "content": 12}))

        with pytest.raises(ValueError, match="expected a string 'content' field"):
            detector.load_readme(p)

    def test_load_milestones_refuses_a_non_list_payload(self, tmp_path):
        p = tmp_path / "milestones.json"
        p.write_text(json.dumps({"number": 1}))

        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(p)


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert result["source"] == "fixture"
        assert result["primary_gap"]["slug"] == "readme-claims-dangling-milestone-204"
        assert result["primary_gap"]["confidence"] == 0.8
        assert result["tail"] == []

    def test_the_shipped_fixture_excludes_both_real_milestones(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert {g["slug"] for g in result["excluded"]} == {
            "claimed-milestone-exists-readme-7",
            "claimed-milestone-exists-readme-12",
        }

    def test_the_shipped_fixtures_repeated_claim_is_deduplicated(self):
        """README.md names milestone #204 twice on purpose -- one candidate
        must come back, not two tied ones."""
        result = detector.run_recipe_scan(now=_NOW)

        assert result["tail"] == []
        assert result["primary_gap"] is not None

    def test_the_shipped_fixtures_negated_claim_never_surfaces(self):
        result = detector.run_recipe_scan(now=_NOW)
        slugs = {g["slug"] for g in result["excluded"]}
        slugs.add(result["primary_gap"]["slug"])

        assert not any("55" in s for s in slugs)

    def test_the_shipped_fixtures_bare_issue_reference_never_surfaces(self):
        result = detector.run_recipe_scan(now=_NOW)
        slugs = {g["slug"] for g in result["excluded"]}
        slugs.add(result["primary_gap"]["slug"])

        assert not any("813" in s for s in slugs)

    def test_generated_at_is_the_now_it_was_handed(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert result["generated_at"] == _NOW.isoformat()

    def test_it_defaults_now_to_the_real_clock(self):
        result = detector.run_recipe_scan()

        assert result["generated_at"] is not None
