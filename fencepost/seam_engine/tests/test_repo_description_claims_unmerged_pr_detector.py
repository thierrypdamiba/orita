"""Tests for RECIPES/repo-description-claims-unmerged-pr/detector.py's
own detection logic (ROADMAP.md #1408) -- the hundred-tenth real recipe:
the repository's own one-line description names a ships/includes/merges/
via #N claim about a pull request, but the named PR never actually
merged.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "repo-description-claims-unmerged-pr" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_repo_description_claims_unmerged_pr_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 9, 11, 15, 0, 0, tzinfo=timezone.utc)


def _pull(number: int, state: str = "open", merged: bool = False) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, merged=merged,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestClaimedPrNumbers:
    """`_claimed_pr_numbers` is imported verbatim from
    `seam_engine.pr_claims` -- not retyped -- so these tests exist to
    prove the import wiring actually reaches the shared grammar, not to
    re-prove the regex itself."""

    def test_ships_hash_n(self):
        assert detector._claimed_pr_numbers("Ships #901.") == [901]

    def test_merges_hash_n(self):
        assert detector._claimed_pr_numbers("Merges #902.") == [902]

    def test_bare_hash_n_with_no_claim_verb_is_never_extracted(self):
        assert detector._claimed_pr_numbers("Background discussion lives in #905.") == []

    def test_multiple_distinct_claims_are_both_extracted(self):
        assert detector._claimed_pr_numbers("Ships #901. Merges #902.") == [901, 902]


class TestComputeGaps:
    def test_an_unmerged_open_claim_is_surfaced_at_flat_high_confidence(self):
        pr = _pull(901, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps("Ships #901.", [pr])

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "repo-description-claims-unmerged-pr-901"
        assert surfaced[0].confidence == 0.85

    def test_an_unmerged_closed_claim_is_also_surfaced(self):
        # merged=False even though state="closed" -- closed-without-merging
        # is exactly as unfulfilled a claim as still-open.
        pr = _pull(903, state="closed", merged=False)

        surfaced, excluded = detector.compute_gaps("Merges #903.", [pr])

        assert len(surfaced) == 1
        assert surfaced[0].slug == "repo-description-claims-unmerged-pr-903"

    def test_a_merged_claimed_pr_is_excluded_not_surfaced(self):
        pr = _pull(902, state="closed", merged=True)

        surfaced, excluded = detector.compute_gaps("Includes #902.", [pr])

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-repo-description-902" in excluded_slugs

    def test_a_claim_naming_a_pr_that_does_not_exist_is_excluded_not_surfaced(self):
        surfaced, excluded = detector.compute_gaps("Via #999.", [])

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-pr-not-found-repo-description-999" in excluded_slugs

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
        pr = _pull(902, state="closed", merged=True)

        surfaced, excluded = detector.compute_gaps(
            "Includes #902 and merges #902 again for good measure.", [pr]
        )

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert excluded_slugs == {"claim-true-repo-description-902"}

    def test_multiple_distinct_unmerged_claims_are_both_surfaced(self):
        surfaced, excluded = detector.compute_gaps(
            "Ships #901. Merges #903.",
            [_pull(901, state="open", merged=False), _pull(903, state="closed", merged=False)],
        )

        assert excluded == []
        slugs = {g.slug for g in surfaced}
        assert slugs == {
            "repo-description-claims-unmerged-pr-901",
            "repo-description-claims-unmerged-pr-903",
        }


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "repo-description-claims-unmerged-pr-901"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_excludes_the_true_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-repo-description-902" in excluded_slugs

    def test_the_shipped_fixture_produces_an_empty_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["tail"] == []


class TestLoaders:
    """load_description/load_pulls -- proves each loader parses the real
    shipped fixture, and each refuses a syntactically valid but
    wrong-shaped JSON payload with a named ValueError rather than a bare
    crash three frames deeper -- the same discipline every other loader in
    this engine already holds itself to."""

    def test_load_description_parses_the_real_fixture(self):
        description = detector.load_description()
        assert isinstance(description, str)
        assert "#901" in description

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pulls)

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
    def test_load_pulls_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pulls(bad_file)
