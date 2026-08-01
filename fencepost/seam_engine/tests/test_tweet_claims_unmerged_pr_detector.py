"""Tests for RECIPES/tweet-claims-unmerged-pr/detector.py's own detection
logic (ROADMAP.md #450) -- the twenty-seventh real recipe: a tweet from
the connected X account claims a pull request shipped in it, but the PR
never actually merged.

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this test
exercises the exact module a live scan would import, not a copy.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "tweet-claims-unmerged-pr" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_tweet_claims_unmerged_pr_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)


def _tweet(tid: str, text: str, created_at: datetime) -> "detector.Tweet":
    return detector.Tweet(
        id=tid, text=text, created_at=created_at,
        url=f"https://x.com/oritatown/status/{tid}",
    )


def _pull(number: int, state: str = "open", merged: bool = False) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, merged=merged,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestClaimedPrNumbers:
    def test_ships_hash_n(self):
        assert detector._claimed_pr_numbers("Ships #901.") == [901]

    def test_includes_hash_n(self):
        assert detector._claimed_pr_numbers("Includes #902 this time.") == [902]

    def test_merges_hash_n(self):
        assert detector._claimed_pr_numbers("Merges #903.") == [903]

    def test_via_hash_n(self):
        assert detector._claimed_pr_numbers("Shipped via #904.") == [904]

    def test_case_insensitive(self):
        assert detector._claimed_pr_numbers("SHIPS #905.") == [905]

    def test_bare_hash_n_with_no_claim_verb_is_never_extracted(self):
        # This is dangling-issue-reference's/mention-dangling-reference's
        # own broader regex; a bare "see #N" mention in prose is not a
        # shipped-it claim.
        assert detector._claimed_pr_numbers("See #906 for background.") == []

    def test_multiple_claims_in_one_tweet(self):
        assert detector._claimed_pr_numbers("Ships #901. Includes #902.") == [901, 902]

    def test_duplicate_claim_in_one_tweet_is_not_deduplicated_at_extraction(self):
        # De-duplication happens in compute_gaps, not here -- this function
        # is a pure extraction, faithfully reporting every match.
        assert detector._claimed_pr_numbers("Ships #901 and via #901 again.") == [901, 901]


class TestComputeGaps:
    def test_a_stale_unmerged_claim_is_surfaced_at_high_confidence(self):
        tweet = _tweet("T-1", "Ships #901.", _NOW - timedelta(hours=50))
        pull = _pull(901, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([tweet], [pull], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "tweet-claims-unmerged-pr-T-1-901"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_unmerged_claim_is_surfaced_at_low_confidence(self):
        tweet = _tweet("T-2", "Merges #903.", _NOW - timedelta(hours=4))
        pull = _pull(903, state="closed", merged=False)

        surfaced, excluded = detector.compute_gaps([tweet], [pull], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_merged_claimed_pr_is_excluded_not_surfaced(self):
        tweet = _tweet("T-3", "Includes #902.", _NOW - timedelta(hours=50))
        pull = _pull(902, state="closed", merged=True)

        surfaced, excluded = detector.compute_gaps([tweet], [pull], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-T-3-902" in excluded_slugs

    def test_a_claim_naming_a_pr_that_does_not_exist_is_excluded_not_surfaced(self):
        tweet = _tweet("T-4", "Via #999 fix.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([tweet], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-pr-not-found-T-4-999" in excluded_slugs

    def test_a_tweet_with_no_claim_phrase_produces_no_candidate_at_all(self):
        tweet = _tweet("T-5", "Housekeeping only, see #905 for background.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([tweet], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-T-5"

    def test_a_duplicate_claim_in_one_tweet_produces_one_candidate_not_two(self):
        tweet = _tweet("T-6", "Ships #901 and via #901 again.", _NOW - timedelta(hours=50))
        pull = _pull(901, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([tweet], [pull], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "tweet-claims-unmerged-pr-T-6-901"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "tweet-claims-unmerged-pr-T-901-901"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_fresh_claim_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "tweet-claims-unmerged-pr-T-902-903" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_claim_and_the_dangling_and_no_claim_tweets(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-T-903-902" in excluded_slugs
        assert "claimed-pr-not-found-T-904-999" in excluded_slugs
        assert "no-claim-phrase-T-905" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_901_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("tweet-claims-unmerged-pr-T-901-901") == 1


class TestLoaders:
    """load_tweets/load_pulls -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_tweets_parses_the_real_fixture(self):
        tweets = detector.load_tweets()
        assert len(tweets) > 0
        assert all(isinstance(t, detector.Tweet) for t in tweets)

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
    def test_load_pulls_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pulls(bad_file)
