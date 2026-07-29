"""Tests for RECIPES/mention-dangling-reference/detector.py's own detection
logic -- the eighteenth real recipe, and the first to exercise `GetMyMentions`
(a scope cleared on SCOPES.md's oath table since founding, never used by any
recipe until this one).

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this test
exercises the exact module a live scan would import, not a copy -- same
discipline as `test_dangling_issue_reference_detector.py` and every sibling
detector test in this engine.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "mention-dangling-reference" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_mention_dangling_reference_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)


def _mention(text: str, mention_id: str = "X-abc", author: str = "test-mortal") -> "detector.Mention":
    return detector.Mention(
        id=mention_id, author=author, text=text,
        url=f"https://x.com/{author}/status/{mention_id}",
        ts=datetime(2026, 7, 20, 0, 0, 0, tzinfo=timezone.utc),
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
        assert detector._referenced_numbers("following up on #99") == [99]

    def test_two_bare_references_are_both_extracted(self):
        assert detector._referenced_numbers("about #1 and #2") == [1, 2]

    def test_no_reference_returns_an_empty_list(self):
        assert detector._referenced_numbers("love this project, following every day") == []

    def test_a_cross_repo_reference_is_not_extracted(self):
        assert detector._referenced_numbers("is this like arcadeai/gasstation#42?") == []

    def test_a_same_repo_slug_prefixed_reference_is_not_extracted(self):
        assert detector._referenced_numbers("see repo#42") == []

    def test_a_reference_at_the_very_start_of_the_mention_is_extracted(self):
        assert detector._referenced_numbers("#7 -- any update?") == [7]

    def test_a_reference_preceded_by_punctuation_is_extracted(self):
        assert detector._referenced_numbers("(re: #7)") == [7]


class TestComputeGaps:
    def test_a_reference_to_a_nonexistent_number_is_surfaced(self):
        mentions = [_mention("following up on #99 -- any update?", "X-1001")]
        surfaced, excluded = detector.compute_gaps(mentions, [_issue(12)], [_pull(40)], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "mention-dangling-reference-X-1001-99"
        assert surfaced[0].confidence == detector._DANGLING_CONFIDENCE

    def test_a_reference_matching_a_real_open_issue_is_excluded(self):
        mentions = [_mention("nice catch on #12", "X-1002")]
        surfaced, excluded = detector.compute_gaps(mentions, [_issue(12, "open")], [], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "mention-ref-matched-X-1002-12"
        assert excluded[0].confidence == 0.0

    def test_a_reference_matching_a_closed_issue_is_still_excluded(self):
        # Existing is what matters, not open-vs-closed -- a reference to a
        # closed issue is not this recipe's seam to watch.
        mentions = [_mention("saw #15 already got closed", "X-1005")]
        surfaced, excluded = detector.compute_gaps(mentions, [_issue(15, "closed")], [], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "mention-ref-matched-X-1005-15"

    def test_a_reference_matching_a_merged_pr_number_is_excluded_not_surfaced(self):
        # The whole reason both lists are checked: GitHub shares one number
        # sequence between issues and PRs. Checking only issues would
        # misfire this as a false dangling-reference gap.
        mentions = [_mention("thanks for landing #40", "X-1006")]
        surfaced, excluded = detector.compute_gaps(mentions, [], [_pull(40)], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "mention-ref-matched-X-1006-40"

    def test_a_mention_with_no_reference_produces_no_candidate_at_all(self):
        mentions = [_mention("this whole town is wild, following every day", "X-1004")]
        surfaced, excluded = detector.compute_gaps(mentions, [_issue(12)], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_cross_repo_reference_produces_no_candidate_at_all(self):
        mentions = [_mention("is this arcadeai/gasstation#42?", "X-1003")]
        surfaced, excluded = detector.compute_gaps(mentions, [], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_two_references_in_one_mention_are_judged_independently(self):
        mentions = [_mention("#1 is real but stray #999 isn't", "X-1007")]
        surfaced, excluded = detector.compute_gaps(mentions, [_issue(1)], [], now=_NOW)

        assert len(excluded) == 1 and excluded[0].slug == "mention-ref-matched-X-1007-1"
        assert len(surfaced) == 1 and surfaced[0].slug == "mention-dangling-reference-X-1007-999"

    def test_surfaced_confidence_is_lower_than_the_commit_sourced_twins(self):
        # An honest, reasoned gap versus dangling-issue-reference's own
        # flat 0.8 -- not a copy-pasted number. See recipe.json's
        # confidence_notes for the full reasoning.
        assert detector._DANGLING_CONFIDENCE < 0.8
        assert detector._DANGLING_CONFIDENCE >= 0.70  # still clears CONFIDENCE_BAR


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert result["source"] == "fixture"
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "mention-dangling-reference-X-1001-99"
        assert result["primary_gap"]["confidence"] >= result["confidence_bar"]

    def test_the_shipped_fixture_excludes_both_real_matches(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {e["slug"] for e in result["excluded"]}
        assert "mention-ref-matched-X-1002-12" in excluded_slugs
        assert "mention-ref-matched-X-1005-15" in excluded_slugs

    def test_the_shipped_fixture_has_no_candidate_for_the_cross_repo_or_bare_mentions(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {e["slug"] for e in result["excluded"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        all_slugs |= {g["slug"] for g in result["tail"]}
        assert not any("X-1003" in s for s in all_slugs)
        assert not any("X-1004" in s for s in all_slugs)


class TestLoaders:
    """load_mentions/load_issues/load_pulls -- proves each loader parses the
    real shipped fixture, and each refuses a syntactically valid but
    non-list JSON payload with a named ValueError rather than a bare
    TypeError three frames deeper (the same bug class task 358/359 closed
    on this engine's other loaders, built in here from the start)."""

    def test_load_mentions_parses_the_real_fixture(self):
        mentions = detector.load_mentions()
        assert len(mentions) > 0
        assert all(isinstance(m, detector.Mention) for m in mentions)

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pulls)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_mentions_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_mentions(bad_file)

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
