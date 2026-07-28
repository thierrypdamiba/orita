"""Tests for RECIPES/dangling-issue-reference/detector.py's own detection
logic -- the fourth real recipe, and the first proof that CONTRIBUTING.md's
"the day a fourth recipe merges" (named directly in
test_recipe_count_doctrine.py's own docstring) is not hypothetical.

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this test
exercises the exact module a live scan would import, not a copy -- same
discipline as `test_merged_pr_issue_still_open_detector.py` and
`test_release_not_tweeted_detector.py`.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "dangling-issue-reference" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_dangling_issue_reference_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc)


def _commit(message: str, sha: str = "abc1234") -> "detector.Commit":
    return detector.Commit(
        sha=sha, message=message, url=f"https://github.com/example/example-repo/commit/{sha}",
        ts=datetime(2026, 7, 20, 0, 0, 0, tzinfo=timezone.utc), author="test",
    )


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
    def test_a_bare_reference_is_extracted(self):
        assert detector._referenced_numbers("part of #12") == [12]

    def test_two_bare_references_are_both_extracted(self):
        assert detector._referenced_numbers("relates to #1 and #2") == [1, 2]

    def test_no_reference_returns_an_empty_list(self):
        assert detector._referenced_numbers("Routine cleanup, nothing here") == []

    def test_a_cross_repo_reference_is_not_extracted(self):
        assert detector._referenced_numbers("see arcadeai/gasstation#42") == []

    def test_a_same_repo_slug_prefixed_reference_is_not_extracted(self):
        assert detector._referenced_numbers("see repo#42") == []

    def test_a_reference_at_the_very_start_of_the_message_is_extracted(self):
        assert detector._referenced_numbers("#7 fixed") == [7]

    def test_a_reference_preceded_by_punctuation_is_extracted(self):
        assert detector._referenced_numbers("(see #7)") == [7]


class TestComputeGaps:
    def test_a_reference_to_a_nonexistent_number_is_surfaced(self):
        commits = [_commit("see #99 for context")]
        surfaced, excluded = detector.compute_gaps(commits, [_issue(12)], [_pull(40)], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "dangling-issue-reference-abc1234-99"
        assert surfaced[0].confidence == detector._DANGLING_CONFIDENCE

    def test_a_reference_matching_a_real_open_issue_is_excluded(self):
        commits = [_commit("part of #12")]
        surfaced, excluded = detector.compute_gaps(commits, [_issue(12, "open")], [], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "dangling-ref-matched-abc1234-12"
        assert excluded[0].confidence == 0.0

    def test_a_reference_matching_a_closed_issue_is_still_excluded(self):
        # Existing is what matters, not open-vs-closed -- a reference to a
        # closed issue is not this recipe's seam to watch (state, not
        # existence, is the concern of a DIFFERENT detector entirely).
        commits = [_commit("relates to #15")]
        surfaced, excluded = detector.compute_gaps(commits, [_issue(15, "closed")], [], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "dangling-ref-matched-abc1234-15"

    def test_a_reference_matching_a_merged_pr_number_is_excluded_not_surfaced(self):
        # The whole reason both lists are checked: GitHub shares one number
        # sequence between issues and PRs. Checking only issues would
        # misfire this as a false dangling-reference gap.
        commits = [_commit("Fixes the bug from #40")]
        surfaced, excluded = detector.compute_gaps(commits, [], [_pull(40)], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "dangling-ref-matched-abc1234-40"

    def test_a_commit_with_no_reference_produces_no_candidate_at_all(self):
        commits = [_commit("Routine cleanup, no reference here")]
        surfaced, excluded = detector.compute_gaps(commits, [_issue(12)], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_cross_repo_reference_produces_no_candidate_at_all(self):
        commits = [_commit("see arcadeai/gasstation#42")]
        surfaced, excluded = detector.compute_gaps(commits, [], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_two_references_in_one_commit_are_judged_independently(self):
        commits = [_commit("closes #1, references stray #999")]
        surfaced, excluded = detector.compute_gaps(commits, [_issue(1)], [], now=_NOW)

        assert len(excluded) == 1 and excluded[0].slug == "dangling-ref-matched-abc1234-1"
        assert len(surfaced) == 1 and surfaced[0].slug == "dangling-issue-reference-abc1234-999"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert result["source"] == "fixture"
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "dangling-issue-reference-b2c3d4e-99"
        assert result["primary_gap"]["confidence"] >= result["confidence_bar"]

    def test_the_shipped_fixture_excludes_both_real_matches(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {e["slug"] for e in result["excluded"]}
        assert "dangling-ref-matched-a1b2c3d-12" in excluded_slugs
        assert "dangling-ref-matched-e5f6a7b-15" in excluded_slugs


class TestLoaders:
    """load_commits/load_issues/load_pulls -- proves each loader parses the
    real shipped fixture, and each refuses a syntactically valid but
    non-list JSON payload with a named ValueError rather than a bare
    TypeError three frames deeper (the same bug class task 358/359 closed
    on this engine's other loaders, built in here from the start)."""

    def test_load_commits_parses_the_real_fixture(self):
        commits = detector.load_commits()
        assert len(commits) > 0
        assert all(isinstance(c, detector.Commit) for c in commits)

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pulls)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_commits_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_commits(bad_file)

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
