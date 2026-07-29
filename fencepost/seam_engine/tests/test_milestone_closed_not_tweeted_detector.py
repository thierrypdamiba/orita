"""Tests for RECIPES/milestone-closed-not-tweeted/detector.py's own
detection logic (ROADMAP.md #390) -- the nineteenth real recipe: a
milestone closed, but no tweet from the connected X account ever named
it. The milestone-side twin of release-not-tweeted (task 110): that
recipe watches a release's own silence within a fixed announce window,
matched by exact tag substring; this one watches the identical silence
one level up, against a milestone, matched by the shared "milestone #N"
claim phrase instead (a milestone has no tag to match by substring).

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this
test exercises the exact module a live scan would import, not a copy.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "milestone-closed-not-tweeted" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_milestone_closed_not_tweeted_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)


def _milestone(
    number: int,
    state: str = "closed",
    closed_at: datetime | None = None,
) -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state,
        closed_at=closed_at,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


def _tweet(text: str, created_at: datetime | None = None) -> "detector.Tweet":
    return detector.Tweet(
        id="T-1", text=text, created_at=created_at or _NOW,
        url="https://x.com/example/status/1",
    )


class TestComputeGaps:
    def test_a_stale_unannounced_close_is_surfaced_at_high_confidence(self):
        milestone = _milestone(5001, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([milestone], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-closed-not-tweeted-5001"
        assert surfaced[0].confidence == 0.85

    def test_a_recently_closed_milestone_is_surfaced_at_low_confidence(self):
        milestone = _milestone(5002, closed_at=_NOW - timedelta(hours=6))

        surfaced, excluded = detector.compute_gaps([milestone], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.55

    def test_a_close_exactly_at_the_announce_window_is_high_confidence(self):
        milestone = _milestone(5003, closed_at=_NOW - timedelta(hours=24))

        surfaced, _ = detector.compute_gaps([milestone], [], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_a_milestone_named_by_a_tweet_is_excluded_not_surfaced(self):
        milestone = _milestone(5004, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        tweet = _tweet("Milestone #5004 is done and nothing else.")

        surfaced, excluded = detector.compute_gaps([milestone], [tweet], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "milestone-tweeted-5004"

    def test_a_milestone_named_by_an_older_tweet_not_just_the_newest_is_excluded(self):
        # A milestone credited by an OLDER tweet, not the most recently read
        # one -- proves the check scans every tweet read so far, not only
        # the newest `GetUserTweets` snapshot.
        milestone = _milestone(5005, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        old_tweet = _tweet("Milestone #5005 shipped.", created_at=datetime(2026, 7, 21, 0, 0, 0, tzinfo=timezone.utc))
        newest_tweet = _tweet("Today's Fencepost Report: nothing cleared the bar.", created_at=_NOW)

        surfaced, excluded = detector.compute_gaps([milestone], [old_tweet, newest_tweet], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "milestone-tweeted-5005"

    def test_a_still_open_milestone_is_excluded_not_surfaced(self):
        milestone = _milestone(5006, state="open", closed_at=None)

        surfaced, excluded = detector.compute_gaps([milestone], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "milestone-not-closed-5006"

    def test_a_tweet_naming_an_unrelated_milestone_number_does_not_clear_the_real_one(self):
        milestone = _milestone(5007, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        tweet = _tweet("Milestone #9999 shipped, unrelated to this fixture.")

        surfaced, excluded = detector.compute_gaps([milestone], [tweet], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-closed-not-tweeted-5007"

    def test_a_bare_hash_mention_with_no_milestone_word_does_not_clear_it(self):
        # "check out #N" is not an announcement -- the claim phrase requires
        # the literal word "milestone" before the number.
        milestone = _milestone(5008, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        tweet = _tweet("Check out #5008 for background context.")

        surfaced, excluded = detector.compute_gaps([milestone], [tweet], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-closed-not-tweeted-5008"

    def test_the_claim_phrase_is_case_insensitive(self):
        milestone = _milestone(5009, closed_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc))
        tweet = _tweet("MILESTONE #5009 is done.")

        surfaced, excluded = detector.compute_gaps([milestone], [tweet], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "milestone-tweeted-5009"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "milestone-closed-not-tweeted-4001"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recent_close_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "milestone-closed-not-tweeted-4002" in tail_slugs

    def test_the_shipped_fixture_excludes_the_tweeted_and_open_milestones(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "milestone-tweeted-4003" in excluded_slugs
        assert "milestone-not-closed-4004" in excluded_slugs

    def test_the_shipped_fixture_never_considers_4003_4004_as_candidates(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {g["slug"] for g in result["tail"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        assert not any("-4003" in s or "-4004" in s for s in all_slugs)


class TestLoaders:
    """load_milestones/load_tweets -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    def test_load_tweets_parses_the_real_fixture(self):
        tweets = detector.load_tweets()
        assert len(tweets) > 0
        assert all(isinstance(t, detector.Tweet) for t in tweets)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_milestones_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_tweets_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_tweets(bad_file)
