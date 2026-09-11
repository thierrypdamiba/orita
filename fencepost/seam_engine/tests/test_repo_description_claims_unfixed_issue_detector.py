"""Tests for RECIPES/repo-description-claims-unfixed-issue/detector.py's
own detection logic (ROADMAP.md #1405) -- the hundred-seventh real
recipe: the repository's own one-line description names a real GitHub
closing keyword against an issue, but the named issue never actually
closed.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "repo-description-claims-unfixed-issue" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_repo_description_claims_unfixed_issue_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)


def _issue(number: int, state: str = "open") -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestClosingKeywordNumbers:
    """`_closing_keyword_numbers` is imported verbatim from
    `seam_engine.closing_keywords` -- not retyped -- so these tests exist
    to prove the import wiring actually reaches the shared grammar, not to
    re-prove the regex itself."""

    def test_fixes_hash_n(self):
        assert detector._closing_keyword_numbers("Fixes #201.") == [201]

    def test_closes_hash_n(self):
        assert detector._closing_keyword_numbers("Closes #202.") == [202]

    def test_resolves_hash_n(self):
        assert detector._closing_keyword_numbers("Resolves #203.") == [203]

    def test_past_tense_also_matches(self):
        assert detector._closing_keyword_numbers("Fixed #204. Closed #205. Resolved #206.") == [204, 205, 206]

    def test_bare_hash_n_with_no_keyword_is_never_extracted(self):
        assert detector._closing_keyword_numbers("See #205 for background.") == []

    def test_present_participle_closing_never_matches_iron_rule_8_safe_phrasing(self):
        assert detector._closing_keyword_numbers("Closing #201 in prose only.") == []


class TestComputeGaps:
    def test_an_open_claim_is_surfaced_at_flat_high_confidence(self):
        issue = _issue(4, state="open")

        surfaced, excluded = detector.compute_gaps("Fixes #4.", [issue])

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "repo-description-claims-unfixed-issue-4"
        assert surfaced[0].confidence == 0.85

    def test_a_closed_claimed_issue_is_excluded_not_surfaced(self):
        issue = _issue(201, state="closed")

        surfaced, excluded = detector.compute_gaps("Closes #201.", [issue])

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-repo-description-201" in excluded_slugs

    def test_a_claim_naming_an_issue_that_does_not_exist_is_excluded_not_surfaced(self):
        surfaced, excluded = detector.compute_gaps("Resolves #299.", [])

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-issue-not-found-repo-description-299" in excluded_slugs

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
        issue = _issue(4, state="open")

        surfaced, excluded = detector.compute_gaps(
            "Fixes #4 and fixes #4 again for good measure.", [issue]
        )

        assert len(surfaced) == 1
        assert surfaced[0].slug == "repo-description-claims-unfixed-issue-4"

    def test_multiple_distinct_open_claims_are_both_surfaced(self):
        surfaced, excluded = detector.compute_gaps(
            "Fixes #4. Closes #5.",
            [_issue(4, state="open"), _issue(5, state="open")],
        )

        assert excluded == []
        slugs = {g.slug for g in surfaced}
        assert slugs == {"repo-description-claims-unfixed-issue-4", "repo-description-claims-unfixed-issue-5"}


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "repo-description-claims-unfixed-issue-4"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_excludes_the_true_claim_and_the_missing_issue(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-repo-description-201" in excluded_slugs
        assert "claimed-issue-not-found-repo-description-299" in excluded_slugs

    def test_the_shipped_fixture_produces_an_empty_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["tail"] == []


class TestLoaders:
    """load_description/load_issues -- proves each loader parses the real
    shipped fixture, and each refuses a syntactically valid but
    wrong-shaped JSON payload with a named ValueError rather than a bare
    crash three frames deeper -- the same discipline every other loader in
    this engine already holds itself to."""

    def test_load_description_parses_the_real_fixture(self):
        description = detector.load_description()
        assert isinstance(description, str)
        assert "Fixes #4" in description

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

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
    def test_load_issues_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issues(bad_file)
