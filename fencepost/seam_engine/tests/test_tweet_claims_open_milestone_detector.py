"""Tests for RECIPES/tweet-claims-open-milestone/detector.py's own
detection logic (ROADMAP.md #452) -- the twenty-ninth real recipe: a tweet
from the connected X account claims a milestone shipped, but the named
milestone never actually closed.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "tweet-claims-open-milestone" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_tweet_claims_open_milestone_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)


def _tweet(tid: str, text: str, created_at: datetime) -> "detector.Tweet":
    return detector.Tweet(
        id=tid, text=text, created_at=created_at,
        url=f"https://x.com/oritatown/status/{tid}",
    )


def _milestone(number: int, state: str = "open") -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


class TestClaimedMilestoneNumbers:
    def test_milestone_hash_n(self):
        assert detector._claimed_milestone_numbers("Milestone #5001 shipped.") == [5001]

    def test_case_insensitive(self):
        assert detector._claimed_milestone_numbers("MILESTONE #5002 done.") == [5002]

    def test_bare_hash_n_with_no_milestone_word_is_never_extracted(self):
        assert detector._claimed_milestone_numbers("See #5003 for background.") == []

    def test_multiple_claims_in_one_tweet(self):
        assert detector._claimed_milestone_numbers("Milestone #5001. Milestone #5002.") == [5001, 5002]

    def test_duplicate_claim_in_one_tweet_is_not_deduplicated_at_extraction(self):
        # De-duplication happens in compute_gaps, not here -- this function
        # is a pure extraction, faithfully reporting every match.
        assert detector._claimed_milestone_numbers("Milestone #5001 and milestone #5001 again.") == [5001, 5001]


class TestComputeGaps:
    def test_a_stale_open_claim_is_surfaced_at_high_confidence(self):
        tweet = _tweet("T-1", "Milestone #5001 shipped.", _NOW - timedelta(hours=50))
        milestone = _milestone(5001, state="open")

        surfaced, excluded = detector.compute_gaps([tweet], [milestone], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "tweet-claims-open-milestone-T-1-5001"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_open_claim_is_surfaced_at_low_confidence(self):
        tweet = _tweet("T-2", "Milestone #5003 done.", _NOW - timedelta(hours=4))
        milestone = _milestone(5003, state="open")

        surfaced, excluded = detector.compute_gaps([tweet], [milestone], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_closed_claimed_milestone_is_excluded_not_surfaced(self):
        tweet = _tweet("T-3", "Milestone #5002 wrapped up.", _NOW - timedelta(hours=50))
        milestone = _milestone(5002, state="closed")

        surfaced, excluded = detector.compute_gaps([tweet], [milestone], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-T-3-5002" in excluded_slugs

    def test_a_claim_naming_a_milestone_that_does_not_exist_is_excluded_not_surfaced(self):
        tweet = _tweet("T-4", "Milestone #5999 shipped.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([tweet], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-not-found-T-4-5999" in excluded_slugs

    def test_a_tweet_with_no_claim_phrase_produces_no_candidate_at_all(self):
        tweet = _tweet("T-5", "Housekeeping only, see #5005 for background.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([tweet], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-T-5"

    def test_a_duplicate_claim_in_one_tweet_produces_one_candidate_not_two(self):
        tweet = _tweet("T-6", "Milestone #5001 shipped and milestone #5001 confirmed again.", _NOW - timedelta(hours=50))
        milestone = _milestone(5001, state="open")

        surfaced, excluded = detector.compute_gaps([tweet], [milestone], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "tweet-claims-open-milestone-T-6-5001"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "tweet-claims-open-milestone-T-1201-5001"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_fresh_claim_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "tweet-claims-open-milestone-T-1202-5003" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_claim_and_the_dangling_and_no_claim_tweets(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-T-1203-5002" in excluded_slugs
        assert "claimed-milestone-not-found-T-1204-5999" in excluded_slugs
        assert "no-claim-phrase-T-1205" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_5001_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("tweet-claims-open-milestone-T-1201-5001") == 1


class TestLoaders:
    """load_tweets/load_milestones -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_tweets_parses_the_real_fixture(self):
        tweets = detector.load_tweets()
        assert len(tweets) > 0
        assert all(isinstance(t, detector.Tweet) for t in tweets)

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_tweets_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_tweets(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_milestones_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(bad_file)
