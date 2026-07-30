"""Tests for RECIPES/merged-pr-not-tweeted/detector.py's own detection logic
(ROADMAP.md #398) -- the twentieth real recipe.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "merged-pr-not-tweeted" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_merged_pr_not_tweeted_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)


def _pull(number: int, merged_at: datetime = datetime(2026, 7, 20, 0, 0, 0, tzinfo=timezone.utc)) -> "detector.MergedPull":
    return detector.MergedPull(
        id=f"PR-{number}", number=number, title="Some merged change", merged_at=merged_at,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


def _tweet(text: str, created_at: datetime = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)) -> "detector.Tweet":
    return detector.Tweet(
        id="T-1", text=text, created_at=created_at,
        url="https://x.com/example/status/1",
    )


class TestFindAnnouncingTweet:
    def test_a_short_number_does_not_match_inside_a_longer_number(self):
        # #1301 must not be considered "announced" by a tweet that only
        # names the unrelated, longer #13010. Reproduced live against a
        # pre-fix, plain-substring-containment version: this would return
        # the tweet, treating the real gap as closed.
        assert detector._find_announcing_tweet(1301, [_tweet("#13010 shipped a batch of fixes today.")]) is None

    def test_a_number_that_is_a_prefix_of_a_longer_number_does_not_match(self):
        assert detector._find_announcing_tweet(13, [_tweet("#1301 shipped a hotfix.")]) is None

    def test_an_exact_number_mention_still_matches(self):
        tweet = _tweet("#1303 is live now -- read-only, same as every recipe before it.")
        assert detector._find_announcing_tweet(1303, [tweet]) is tweet

    def test_number_mention_surrounded_by_punctuation_still_matches(self):
        tweet = _tweet("Shipped (#1303)! Read the notes.")
        assert detector._find_announcing_tweet(1303, [tweet]) is tweet

    def test_a_number_preceded_by_another_digit_does_not_match(self):
        # "11301" must not be read as containing a bare "#1301" mention.
        assert detector._find_announcing_tweet(1301, [_tweet("Batch 11301 processed clean.")]) is None


class TestComputeGapsNumberCollision:
    def test_a_short_number_pr_still_surfaces_when_only_a_longer_number_is_tweeted(self):
        # The real, still-unannounced gap (#1301) must not vanish just
        # because an unrelated tweet mentions #13010.
        pulls = [_pull(1301, merged_at=datetime(2026, 7, 25, 0, 0, tzinfo=timezone.utc))]
        tweets = [_tweet("#13010 shipped a batch of fixes today.", created_at=datetime(2026, 7, 26, 9, 0, tzinfo=timezone.utc))]

        surfaced, excluded = detector.compute_gaps(pulls, tweets, now=_NOW)

        assert excluded == []
        surfaced_slugs = {g.slug for g in surfaced}
        assert "merged-pr-not-tweeted-1301" in surfaced_slugs

    def test_an_exact_number_match_still_excludes_the_pull(self):
        pulls = [_pull(1303, merged_at=datetime(2026, 7, 20, 0, 0, tzinfo=timezone.utc))]
        tweets = [_tweet("#1303 is live now.", created_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc))]

        surfaced, excluded = detector.compute_gaps(pulls, tweets, now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "merged-pr-tweeted-1303" in excluded_slugs


class TestComputeGapsAgeGate:
    def test_a_stale_unannounced_merge_scores_above_the_bar(self):
        pulls = [_pull(1301, merged_at=datetime(2026, 7, 25, 0, 0, tzinfo=timezone.utc))]
        surfaced, _ = detector.compute_gaps(pulls, [], now=_NOW)
        assert surfaced[0].confidence == pytest.approx(0.85)

    def test_a_fresh_unannounced_merge_scores_below_the_bar(self):
        pulls = [_pull(1302, merged_at=datetime(2026, 7, 27, 6, 0, tzinfo=timezone.utc))]
        surfaced, _ = detector.compute_gaps(pulls, [], now=_NOW)
        assert surfaced[0].confidence == pytest.approx(0.55)

    def test_surfaced_gaps_sort_by_confidence_descending(self):
        pulls = [
            _pull(1302, merged_at=datetime(2026, 7, 27, 6, 0, tzinfo=timezone.utc)),
            _pull(1301, merged_at=datetime(2026, 7, 25, 0, 0, tzinfo=timezone.utc)),
        ]
        surfaced, _ = detector.compute_gaps(pulls, [], now=_NOW)
        confidences = [g.confidence for g in surfaced]
        assert confidences == sorted(confidences, reverse=True)


class TestLoadMergedPullsFiltersState:
    def test_load_merged_pulls_excludes_open_and_closed_unmerged(self, tmp_path: Path):
        rows = [
            {"id": "A", "number": 1, "title": "merged", "state": "merged",
             "merged_at": "2026-07-20T00:00:00Z", "url": "https://example.com/1"},
            {"id": "B", "number": 2, "title": "still open", "state": "open",
             "merged_at": None, "url": "https://example.com/2"},
            {"id": "C", "number": 3, "title": "closed unmerged", "state": "closed",
             "merged_at": None, "url": "https://example.com/3"},
        ]
        path = tmp_path / "pulls.json"
        path.write_text(json.dumps(rows))

        pulls = detector.load_merged_pulls(path)

        assert [p.number for p in pulls] == [1]

    def test_load_merged_pulls_parses_the_real_fixture(self):
        pulls = detector.load_merged_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.MergedPull) for p in pulls)
        assert all(p.number for p in pulls)

    def test_load_tweets_parses_the_real_fixture(self):
        tweets = detector.load_tweets()
        assert len(tweets) > 0
        assert all(isinstance(t, detector.Tweet) for t in tweets)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_merged_pulls_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_merged_pulls(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_tweets_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_tweets(bad_file)


class TestRunRecipeScanAgainstShippedFixture:
    def test_elects_1301_as_the_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "merged-pr-not-tweeted-1301"
        assert result["primary_gap"]["confidence"] == pytest.approx(0.85)

    def test_1302_is_weighed_in_the_tail_not_hidden_and_not_primary(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "merged-pr-not-tweeted-1302" in tail_slugs

    def test_1303_is_excluded_as_already_tweeted(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "merged-pr-tweeted-1303" in excluded_slugs

    def test_never_merged_pulls_produce_no_candidate_at_all(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = (
            {result["primary_gap"]["slug"]} if result["primary_gap"] else set()
        ) | {g["slug"] for g in result["tail"]} | {g["slug"] for g in result["excluded"]}
        assert not any("1304" in s for s in all_slugs)
        assert not any("1305" in s for s in all_slugs)
