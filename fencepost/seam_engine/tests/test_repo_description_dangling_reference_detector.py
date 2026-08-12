"""Tests for RECIPES/repo-description-dangling-reference/detector.py's own
detection logic -- the eightieth real recipe, and the tenth leg of the
dangling-reference family: the repository's own GetRepository description
field counts on an issue or pull request that isn't actually there.

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this
test exercises the exact module a live scan would import, not a copy --
same discipline as every sibling detector test in this engine.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "repo-description-dangling-reference" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_repo_description_dangling_reference_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)


def _issue(number: int, state: str = "open") -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


def _pull(number: int, state: str = "closed") -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestReferencedNumbers:
    """`_referenced_numbers` is imported verbatim from
    `seam_engine.references` -- not retyped -- so these tests exist to
    prove the import wiring actually reaches the shared grammar, the same
    discipline every other recipe that imports it already holds itself
    to."""

    def test_a_bare_reference_is_extracted(self):
        assert detector._referenced_numbers("built on top of #99") == [99]

    def test_two_bare_references_are_both_extracted(self):
        assert detector._referenced_numbers("about #1 and #2") == [1, 2]

    def test_no_reference_returns_an_empty_list(self):
        assert detector._referenced_numbers("housekeeping only, nothing to see") == []

    def test_a_cross_repo_reference_is_not_extracted(self):
        assert detector._referenced_numbers("inspired by arcadeai/gasstation#42") == []


class TestComputeGaps:
    def test_a_reference_to_a_nonexistent_number_is_surfaced(self):
        surfaced, excluded = detector.compute_gaps(
            "thanks for the review in #99", [_issue(12)], [_pull(40)]
        )

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "repo-description-dangling-reference-99"
        assert surfaced[0].confidence == detector._DANGLING_CONFIDENCE

    def test_a_reference_matching_a_real_open_issue_is_excluded(self):
        surfaced, excluded = detector.compute_gaps("built on #12", [_issue(12, "open")], [])

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "description-ref-matched-12"
        assert excluded[0].confidence == 0.0

    def test_a_reference_matching_a_closed_issue_is_still_excluded(self):
        # Existing is what matters, not open-vs-closed.
        surfaced, excluded = detector.compute_gaps("closes the loop opened by #15", [_issue(15, "closed")], [])

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "description-ref-matched-15"

    def test_a_reference_matching_a_merged_pr_number_is_excluded_not_surfaced(self):
        # The whole reason both lists are checked: GitHub shares one number
        # sequence between issues and PRs. Checking only issues would
        # misfire this as a false dangling-reference gap.
        surfaced, excluded = detector.compute_gaps("follows up on #40", [], [_pull(40)])

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "description-ref-matched-40"

    def test_a_description_with_no_reference_produces_no_candidate_at_all(self):
        surfaced, excluded = detector.compute_gaps("housekeeping only, nothing to see", [_issue(12)], [])

        assert surfaced == []
        assert excluded == []

    def test_a_none_description_is_excluded_named_not_hidden(self):
        surfaced, excluded = detector.compute_gaps(None, [_issue(12)], [])

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "no-description"

    def test_a_cross_repo_reference_produces_no_candidate_at_all(self):
        surfaced, excluded = detector.compute_gaps("inspired by arcadeai/gasstation#42", [], [])

        assert surfaced == []
        assert excluded == []

    def test_two_references_are_judged_independently(self):
        surfaced, excluded = detector.compute_gaps("#1 is real but stray #999 isn't", [_issue(1)], [])

        assert len(excluded) == 1 and excluded[0].slug == "description-ref-matched-1"
        assert len(surfaced) == 1 and surfaced[0].slug == "repo-description-dangling-reference-999"

    def test_the_same_dangling_number_mentioned_twice_produces_only_one_candidate(self):
        surfaced, excluded = detector.compute_gaps("fixes #2, see also #2 in the changelog", [], [])

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "repo-description-dangling-reference-2"

    def test_surfaced_confidence_matches_readme_dangling_references_bar(self):
        # Flat, matching readme-dangling-reference's own bar exactly -- a
        # live GetRepository read carries no staleness uncertainty at all.
        # See recipe.json's confidence_notes.
        assert detector._DANGLING_CONFIDENCE == 0.85


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan()

        assert result["source"] == "fixture"
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "repo-description-dangling-reference-4001"
        assert result["primary_gap"]["confidence"] >= result["confidence_bar"]

    def test_the_shipped_fixture_excludes_every_real_match(self):
        result = detector.run_recipe_scan()
        excluded_slugs = {e["slug"] for e in result["excluded"]}
        assert "description-ref-matched-4" in excluded_slugs
        assert "description-ref-matched-40" in excluded_slugs


class TestLoaders:
    """load_description/load_issues/load_pulls -- proves each loader
    parses the real shipped fixture, and each refuses a syntactically
    valid but wrong-shaped JSON payload with a named ValueError rather
    than a bare crash three frames deeper -- the same discipline every
    other loader in this engine already holds itself to."""

    def test_load_description_parses_the_real_fixture(self):
        content = detector.load_description()
        assert isinstance(content, str)
        assert "#4001" in content

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pulls)

    def test_load_description_returns_none_for_a_null_description(self, tmp_path: Path):
        f = tmp_path / "repository.json"
        f.write_text(json.dumps({"full_name": "a/b", "description": None, "url": "https://github.com/a/b"}))
        assert detector.load_description(f) is None

    @pytest.mark.parametrize("bad_value", [[1, 2], 5, None, "x", True])
    def test_load_description_raises_named_error_not_typeerror_when_json_is_not_an_object(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON object"):
            detector.load_description(bad_file)

    def test_load_description_raises_named_error_when_field_is_missing(self, tmp_path: Path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps({"full_name": "a/b", "url": "https://github.com/a/b"}))
        with pytest.raises(ValueError, match="expected a 'description' field"):
            detector.load_description(bad_file)

    def test_load_description_raises_named_error_when_field_is_wrong_type(self, tmp_path: Path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps({"full_name": "a/b", "description": 5, "url": "https://github.com/a/b"}))
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

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pulls_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pulls(bad_file)
