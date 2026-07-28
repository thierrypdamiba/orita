"""Tests for RECIPES/release-not-tweeted/detector.py's own detection logic
(ROADMAP.md #191) -- no test file exercised `_find_announcing_tweet`/
`compute_gaps` directly before this one; test_recipes.py only validates the
recipe manifest schema and one fixture-shaped end-to-end run, never a
tag-collision case.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "release-not-tweeted" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_release_not_tweeted_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 21, 0, 0, 0, tzinfo=timezone.utc)


def _release(tag: str, published_at: datetime = datetime(2026, 7, 10, 0, 0, 0, tzinfo=timezone.utc)) -> "detector.Release":
    return detector.Release(
        id="REL-1", title="Some release", tag=tag, published_at=published_at,
        url=f"https://github.com/example/example-repo/releases/tag/{tag}",
    )


def _tweet(text: str, created_at: datetime = datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc)) -> "detector.Tweet":
    return detector.Tweet(
        id="T-1", text=text, created_at=created_at,
        url="https://x.com/example/status/1",
    )


class TestFindAnnouncingTweet:
    def test_a_short_tag_does_not_match_inside_a_longer_tag(self):
        # v0.3 must not be considered "announced" by a tweet that only
        # names the unrelated, longer tag v0.3.0. Reproduced live against
        # the pre-fix code (plain substring containment): this returned the
        # tweet, treating the real gap as closed.
        assert detector._find_announcing_tweet("v0.3", [_tweet("v0.3.0 is out now, grab it!")]) is None

    def test_a_tag_that_is_a_prefix_of_a_word_does_not_match(self):
        assert detector._find_announcing_tweet("v1", [_tweet("v1.0.1 shipped a hotfix.")]) is None

    def test_an_exact_tag_mention_still_matches(self):
        tweet = _tweet("v0.2.1 is out — fixes the badge cache going stale.")
        assert detector._find_announcing_tweet("v0.2.1", [tweet]) is tweet

    def test_tag_mention_surrounded_by_punctuation_still_matches(self):
        tweet = _tweet("Shipped (v0.4.0)! Read the notes.")
        assert detector._find_announcing_tweet("v0.4.0", [tweet]) is tweet

    def test_case_insensitivity_is_preserved(self):
        tweet = _tweet("V0.4.0 SHIPPED")
        assert detector._find_announcing_tweet("v0.4.0", [tweet]) is tweet


class TestComputeGapsTagCollision:
    def test_a_short_tag_release_still_surfaces_when_only_a_longer_tag_is_tweeted(self):
        # The real, still-unannounced gap (v0.3) must not vanish just
        # because an unrelated tweet mentions v0.3.0.
        releases = [_release("v0.3", published_at=datetime(2026, 7, 10, tzinfo=timezone.utc))]
        tweets = [_tweet("v0.3.0 is out now, grab it!", created_at=datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc))]

        surfaced, excluded = detector.compute_gaps(releases, tweets, now=_NOW)

        assert excluded == []
        surfaced_slugs = {g.slug for g in surfaced}
        assert "release-not-tweeted-v0.3" in surfaced_slugs

    def test_an_exact_tag_match_still_excludes_the_release(self):
        releases = [_release("v0.2.1", published_at=datetime(2026, 7, 15, tzinfo=timezone.utc))]
        tweets = [_tweet("v0.2.1 is out — fixes the badge cache going stale.",
                          created_at=datetime(2026, 7, 15, 10, 15, tzinfo=timezone.utc))]

        surfaced, excluded = detector.compute_gaps(releases, tweets, now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "release-tweeted-v0.2.1" in excluded_slugs


class TestLoadReleasesAndTweets:
    """load_releases/load_tweets (task 358) -- no test in this file called
    either loader directly before this class; test_recipes.py only proves
    discover_recipes()/load_detector() can import the module. Both crashed
    with a bare TypeError on syntactically valid but non-list JSON, reproduced
    live before the fix ({"a": 1} -> "string indices must be integers"; a
    scalar/None -> "'<type>' object is not iterable")."""

    def test_load_releases_parses_the_real_fixture(self):
        releases = detector.load_releases()
        assert len(releases) > 0
        assert all(isinstance(r, detector.Release) for r in releases)

    def test_load_tweets_parses_the_real_fixture(self):
        tweets = detector.load_tweets()
        assert len(tweets) > 0
        assert all(isinstance(t, detector.Tweet) for t in tweets)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_releases_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_releases(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_tweets_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_tweets(bad_file)
