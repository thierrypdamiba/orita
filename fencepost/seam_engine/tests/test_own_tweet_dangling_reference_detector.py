"""Tests for RECIPES/own-tweet-dangling-reference/detector.py's own detection
logic -- the forty-second real recipe (ROADMAP.md #527), and the sixth leg
of the dangling-reference family: the first to read the connected X
account's OWN tweets rather than a mortal's mention of it
(`mention-dangling-reference`), a commit message (`dangling-issue-
reference`), an issue/PR body (`issue-body-dangling-reference`), a
milestone description (`milestone-body-dangling-reference`), or a release
note (`release-note-dangling-reference`).

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this test
exercises the exact module a live scan would import, not a copy -- same
discipline as every sibling detector test in this engine.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "own-tweet-dangling-reference" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_own_tweet_dangling_reference_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)


def _tweet(text: str, tweet_id: str = "T-9000") -> "detector.Tweet":
    return detector.Tweet(
        id=tweet_id, text=text,
        created_at=datetime(2026, 7, 30, 0, 0, 0, tzinfo=timezone.utc),
        url=f"https://x.com/oritatown/status/{tweet_id}",
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
        assert detector._referenced_numbers("shipped it, see #412 for the story") == [412]

    def test_two_bare_references_are_both_extracted(self):
        assert detector._referenced_numbers("about #1 and #2") == [1, 2]

    def test_no_reference_returns_an_empty_list(self):
        assert detector._referenced_numbers("quiet hour, the town builds") == []

    def test_a_cross_repo_reference_is_not_extracted(self):
        assert detector._referenced_numbers("is this like arcadeai/gasstation#42?") == []

    def test_a_same_repo_slug_prefixed_reference_is_not_extracted(self):
        assert detector._referenced_numbers("see repo#42") == []


class TestComputeGaps:
    def test_a_reference_to_a_nonexistent_number_is_surfaced(self):
        tweets = [_tweet("shipped it, see #412 for the story", "T-1")]
        surfaced, excluded = detector.compute_gaps(tweets, [_issue(12)], [_pull(40)], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "own-tweet-dangling-reference-T-1-412"
        assert surfaced[0].confidence == detector._DANGLING_CONFIDENCE

    def test_a_reference_matching_a_real_closed_issue_is_excluded(self):
        tweets = [_tweet("grateful for everyone following -- #219 closed clean", "T-2")]
        surfaced, excluded = detector.compute_gaps(tweets, [_issue(219, "closed")], [], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "own-tweet-ref-matched-T-2-219"
        assert excluded[0].confidence == 0.0

    def test_a_reference_matching_a_merged_pr_number_is_excluded_not_surfaced(self):
        # The whole reason both lists are checked: GitHub shares one number
        # sequence between issues and PRs. Checking only issues would
        # misfire this as a false dangling-reference gap.
        tweets = [_tweet("merged #300 today", "T-3")]
        surfaced, excluded = detector.compute_gaps(tweets, [], [_pull(300)], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "own-tweet-ref-matched-T-3-300"

    def test_a_tweet_with_no_reference_produces_no_candidate_at_all(self):
        tweets = [_tweet("quiet hour, the town builds", "T-4")]
        surfaced, excluded = detector.compute_gaps(tweets, [_issue(12)], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_cross_repo_reference_produces_no_candidate_at_all(self):
        tweets = [_tweet("is this arcadeai/gasstation#42?", "T-5")]
        surfaced, excluded = detector.compute_gaps(tweets, [], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_two_references_in_one_tweet_are_judged_independently(self):
        tweets = [_tweet("#1 is real but stray #999 isn't", "T-6")]
        surfaced, excluded = detector.compute_gaps(tweets, [_issue(1)], [], now=_NOW)

        assert len(excluded) == 1 and excluded[0].slug == "own-tweet-ref-matched-T-6-1"
        assert len(surfaced) == 1 and surfaced[0].slug == "own-tweet-dangling-reference-T-6-999"

    def test_the_same_dangling_number_referenced_twice_produces_only_one_candidate(self):
        # Same class of bug task 442 fixed for mention-dangling-reference:
        # a repeated #N in one tweet must not produce two identical
        # GapCandidates that tie each other out of rank()'s
        # SEPARATION_MARGIN, silently dropping a real gap as "ambiguous."
        tweets = [_tweet("saw #2 earlier, still no #2 anywhere", "T-7")]
        surfaced, excluded = detector.compute_gaps(tweets, [], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "own-tweet-dangling-reference-T-7-2"

    def test_confidence_is_higher_than_the_mention_sourced_twin(self):
        # Authored by the town itself on purpose (like a commit), not a
        # stranger's own possibly-different numbering scheme in their
        # head (like a mortal's mention) -- see recipe.json's
        # confidence_notes for the full reasoning.
        assert detector._DANGLING_CONFIDENCE == 0.8
        assert detector._DANGLING_CONFIDENCE >= 0.70  # still clears CONFIDENCE_BAR


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert result["source"] == "fixture"
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "own-tweet-dangling-reference-T-4001-412"
        assert result["primary_gap"]["confidence"] >= result["confidence_bar"]

    def test_the_shipped_fixture_excludes_both_real_matches(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {e["slug"] for e in result["excluded"]}
        assert "own-tweet-ref-matched-T-4002-219" in excluded_slugs
        assert "own-tweet-ref-matched-T-4005-219" in excluded_slugs

    def test_the_shipped_fixture_has_no_candidate_for_the_cross_repo_or_bare_tweets(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {e["slug"] for e in result["excluded"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        all_slugs |= {g["slug"] for g in result["tail"]}
        assert not any("T-4003" in s for s in all_slugs)
        assert not any("T-4004" in s for s in all_slugs)


class TestLoaders:
    """load_tweets/load_issues/load_pulls -- proves each loader parses the
    real shipped fixture, and each refuses a syntactically valid but
    non-list JSON payload with a named ValueError rather than a bare
    TypeError three frames deeper (the same bug class task 358/359 closed
    on this engine's other loaders, built in here from the start)."""

    def test_load_tweets_parses_the_real_fixture(self):
        tweets = detector.load_tweets()
        assert len(tweets) > 0
        assert all(isinstance(t, detector.Tweet) for t in tweets)

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pulls)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_tweets_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_tweets(bad_file)

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
