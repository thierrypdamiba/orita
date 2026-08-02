"""Tests for RECIPES/star-milestone-not-announced/detector.py's own
detection logic (ROADMAP.md #486) -- the thirty-first real recipe: a
repository's live star count crosses a round-number milestone, but no
tweet from the connected X account ever announces it.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "star-milestone-not-announced" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_star_milestone_not_announced_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 2, 17, 0, 0, tzinfo=timezone.utc)


def _stars(count: int, checked_at: datetime = _NOW, url: str = "https://github.com/example/example-repo/stargazers") -> "detector.StarCount":
    return detector.StarCount(count=count, checked_at=checked_at, url=url)


def _tweet(text: str, tweet_id: str = "T-x", created_at: datetime = _NOW) -> "detector.Tweet":
    return detector.Tweet(id=tweet_id, text=text, created_at=created_at, url=f"https://x.com/oritatown/status/{tweet_id}")


class TestHighestCrossedMilestone:
    def test_below_the_smallest_milestone_returns_none(self):
        assert detector._highest_crossed_milestone(3) is None

    def test_exactly_on_a_milestone_returns_that_milestone(self):
        assert detector._highest_crossed_milestone(100) == 100

    def test_between_two_milestones_returns_the_lower_one(self):
        assert detector._highest_crossed_milestone(267) == 250

    def test_only_the_highest_crossed_is_ever_returned(self):
        assert detector._highest_crossed_milestone(50_000) == 50_000
        assert detector._highest_crossed_milestone(99_999) == 50_000


class TestFormatVariants:
    def test_below_a_thousand_has_only_one_spelling(self):
        assert detector._format_variants(250) == ["250"]

    def test_a_thousand_and_above_has_both_spellings(self):
        assert detector._format_variants(1000) == ["1000", "1,000"]
        assert detector._format_variants(25_000) == ["25000", "25,000"]


class TestFindAnnouncingTweet:
    def test_a_tweet_naming_the_number_and_star_matches(self):
        tweets = [_tweet("we just crossed 250 stars, thank you")]
        assert detector._find_announcing_tweet(250, tweets) is not None

    def test_a_tweet_naming_the_number_without_the_word_star_does_not_match(self):
        tweets = [_tweet("#250 closed today")]
        assert detector._find_announcing_tweet(250, tweets) is None

    def test_a_tweet_naming_star_without_the_number_does_not_match(self):
        tweets = [_tweet("stars keep coming in, thank you all")]
        assert detector._find_announcing_tweet(250, tweets) is None

    def test_digit_boundary_guards_a_longer_number_from_matching_a_shorter_one(self):
        # "2500 stars" must not be mistaken for an announcement of 250.
        tweets = [_tweet("2500 stars now, unreal")]
        assert detector._find_announcing_tweet(250, tweets) is None

    def test_comma_formatted_thousand_still_matches(self):
        tweets = [_tweet("1,000 stars. sat with that for a minute.")]
        assert detector._find_announcing_tweet(1000, tweets) is not None

    def test_no_matching_tweet_at_all_returns_none(self):
        tweets = [_tweet("today's report shipped, nothing else")]
        assert detector._find_announcing_tweet(250, tweets) is None


class TestComputeGaps:
    def test_below_the_first_milestone_is_excluded_not_surfaced(self):
        surfaced, excluded = detector.compute_gaps(_stars(3), [])

        assert surfaced == []
        assert excluded[0].slug == "no-star-milestone-crossed"
        assert excluded[0].confidence == 0.0

    def test_a_crossed_milestone_already_announced_is_excluded_not_surfaced(self):
        stars = _stars(267)
        tweet = _tweet("250 stars! didn't see that coming", tweet_id="T-1")

        surfaced, excluded = detector.compute_gaps(stars, [tweet])

        assert surfaced == []
        assert excluded[0].slug == "star-milestone-250-announced"
        assert excluded[0].confidence == 0.0
        assert tweet.url in excluded[0].evidence

    def test_a_crossed_milestone_never_announced_is_surfaced_at_high_confidence(self):
        stars = _stars(267)

        surfaced, excluded = detector.compute_gaps(stars, [])

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "star-milestone-250-not-announced"
        assert surfaced[0].confidence == 0.85

    def test_a_tweet_announcing_a_lower_milestone_does_not_excuse_the_higher_one(self):
        stars = _stars(267)
        tweet = _tweet("100 stars, thank you", tweet_id="T-2")

        surfaced, excluded = detector.compute_gaps(stars, [tweet])

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "star-milestone-250-not-announced"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "star-milestone-250-not-announced"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_has_no_excluded_or_tail_candidates(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["excluded"] == []
        assert result["tail"] == []

    def test_the_shipped_fixture_source_is_fixture(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["source"] == "fixture"


class TestLoaders:
    """load_star_count/load_tweets -- mirrors every prior recipe's own
    guard against syntactically valid but wrongly-shaped JSON."""

    def test_load_star_count_parses_the_real_fixture(self):
        stars = detector.load_star_count()
        assert isinstance(stars, detector.StarCount)
        assert stars.count == 267

    def test_load_tweets_parses_the_real_fixture(self):
        tweets = detector.load_tweets()
        assert len(tweets) > 0
        assert all(isinstance(t, detector.Tweet) for t in tweets)

    @pytest.mark.parametrize("bad_value", [[1, 2], 5, None, "x", True])
    def test_load_star_count_raises_named_error_when_json_is_not_an_object(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON object"):
            detector.load_star_count(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_tweets_raises_named_error_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_tweets(bad_file)
