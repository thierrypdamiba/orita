"""Tests for RECIPES/readme-claims-unfixed-issue/detector.py's own
detection logic (ROADMAP.md #492) -- the thirty-sixth real recipe:
README.md itself names a real GitHub closing keyword against an issue,
but the named issue never actually closed.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "readme-claims-unfixed-issue" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_readme_claims_unfixed_issue_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 2, 23, 0, 0, tzinfo=timezone.utc)


def _issue(number: int, state: str = "open") -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestClosingKeywordNumbers:
    """`_closing_keyword_numbers` is imported verbatim from
    `seam_engine.closing_keywords` -- not retyped -- so these tests exist
    to prove the import wiring actually reaches the shared grammar, not to
    re-prove the regex itself (already covered by the module it lives in
    and by the three sibling recipes that import it too)."""

    def test_fixes_hash_n(self):
        assert detector._closing_keyword_numbers("Fixes #201.") == [201]

    def test_closes_hash_n(self):
        assert detector._closing_keyword_numbers("Closes #202.") == [202]

    def test_resolves_hash_n(self):
        assert detector._closing_keyword_numbers("Resolves #203.") == [203]

    def test_past_tense_also_matches(self):
        assert detector._closing_keyword_numbers("Fixed #204. Closed #205. Resolved #206.") == [204, 205, 206]

    def test_case_insensitive(self):
        assert detector._closing_keyword_numbers("FIXES #201.") == [201]

    def test_bare_hash_n_with_no_keyword_is_never_extracted(self):
        assert detector._closing_keyword_numbers("See #205 for background.") == []

    def test_present_participle_closing_never_matches_iron_rule_8_safe_phrasing(self):
        # "closing #N" is the safe present-participle form Iron Rule #8
        # prescribes for prose that must discuss this pattern without
        # triggering it -- proven not to match here, live, not just claimed.
        assert detector._closing_keyword_numbers("Closing #201 in prose only.") == []

    def test_multiple_claims_in_one_readme(self):
        assert detector._closing_keyword_numbers("Fixes #201. Closes #202.") == [201, 202]

    def test_duplicate_claim_in_one_readme_is_not_deduplicated_at_extraction(self):
        # De-duplication happens in compute_gaps, not here -- this function
        # is a pure extraction, faithfully reporting every match.
        assert detector._closing_keyword_numbers("Fixes #201 and fixes #201 again.") == [201, 201]


class TestComputeGaps:
    def test_an_open_claim_is_surfaced_at_flat_high_confidence(self):
        issue = _issue(202, state="open")

        surfaced, excluded = detector.compute_gaps("Closes #202.", [issue])

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "readme-claims-unfixed-issue-202"
        assert surfaced[0].confidence == 0.85

    def test_a_closed_claimed_issue_is_excluded_not_surfaced(self):
        issue = _issue(201, state="closed")

        surfaced, excluded = detector.compute_gaps("Fixes #201.", [issue])

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-readme-201" in excluded_slugs

    def test_a_claim_naming_an_issue_that_does_not_exist_is_excluded_not_surfaced(self):
        surfaced, excluded = detector.compute_gaps("Resolves #299.", [])

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-issue-not-found-readme-299" in excluded_slugs

    def test_a_readme_with_no_claim_phrase_produces_no_candidate_at_all(self):
        surfaced, excluded = detector.compute_gaps("Housekeeping only, see #205 for background.", [])

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-readme"

    def test_a_duplicate_claim_in_one_readme_produces_one_candidate_not_two(self):
        issue = _issue(202, state="open")

        surfaced, excluded = detector.compute_gaps(
            "Closes #202 and fixes #202 again for good measure.", [issue]
        )

        assert len(surfaced) == 1
        assert surfaced[0].slug == "readme-claims-unfixed-issue-202"

    def test_multiple_distinct_open_claims_are_both_surfaced(self):
        surfaced, excluded = detector.compute_gaps(
            "Fixes #201. Closes #202.",
            [_issue(201, state="open"), _issue(202, state="open")],
        )

        assert excluded == []
        slugs = {g.slug for g in surfaced}
        assert slugs == {"readme-claims-unfixed-issue-201", "readme-claims-unfixed-issue-202"}


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "readme-claims-unfixed-issue-202"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_excludes_the_true_claim_and_the_dangling_reference(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-readme-201" in excluded_slugs
        assert "claimed-issue-not-found-readme-299" in excluded_slugs

    def test_the_shipped_fixture_produces_an_empty_tail(self):
        # Only one genuine open claim exists in the shipped fixture, so
        # nothing is left over to weigh in the tail once it is elected
        # primary.
        result = detector.run_recipe_scan(now=_NOW)
        assert result["tail"] == []


class TestLoaders:
    """load_readme/load_issues -- proves each loader parses the real
    shipped fixture, and each refuses a syntactically valid but
    wrong-shaped JSON payload with a named ValueError rather than a bare
    crash three frames deeper -- the same discipline every other loader in
    this engine already holds itself to."""

    def test_load_readme_parses_the_real_fixture(self):
        content = detector.load_readme()
        assert isinstance(content, str)
        assert "Closes #202" in content

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

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
    def test_load_issues_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issues(bad_file)
