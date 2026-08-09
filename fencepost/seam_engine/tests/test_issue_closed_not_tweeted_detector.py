"""Tests for RECIPES/issue-closed-not-tweeted/detector.py's own detection
logic -- the twenty-first real recipe, completing the closed-but-not-
tweeted family alongside release-not-tweeted, milestone-closed-not-tweeted,
and merged-pr-not-tweeted.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "issue-closed-not-tweeted" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_issue_closed_not_tweeted_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)


def _issue(number: int, closed_at: datetime | None = datetime(2026, 7, 20, 0, 0, 0, tzinfo=timezone.utc), state: str = "closed") -> "detector.ClosedIssue":
    return detector.ClosedIssue(
        number=number, title="Some closed issue", state=state, closed_at=closed_at,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


def _tweet(text: str, created_at: datetime = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)) -> "detector.Tweet":
    return detector.Tweet(
        id="T-1", text=text, created_at=created_at,
        url="https://x.com/example/status/1",
    )


class TestFindAnnouncingTweet:
    def test_a_short_number_does_not_match_inside_a_longer_number(self):
        # #12 must not be considered "announced" by a tweet that only
        # names the unrelated, longer #123. Reproduced live against a
        # pre-fix, plain-substring-containment version: this would return
        # the tweet, treating the real gap as closed.
        assert detector._find_announcing_tweet(12, [_tweet("#123 shipped a batch of fixes today.")]) is None

    def test_a_number_that_is_a_prefix_of_a_longer_number_does_not_match(self):
        assert detector._find_announcing_tweet(1, [_tweet("#12 shipped a hotfix.")]) is None

    def test_an_exact_number_mention_still_matches(self):
        tweet = _tweet("#13 is live now -- read-only, same as every recipe before it.")
        assert detector._find_announcing_tweet(13, [tweet]) is tweet

    def test_number_mention_surrounded_by_punctuation_still_matches(self):
        tweet = _tweet("Shipped (#13)! Read the notes.")
        assert detector._find_announcing_tweet(13, [tweet]) is tweet

    def test_a_number_preceded_by_another_digit_does_not_match(self):
        # "112" must not be read as containing a bare "#12" mention.
        assert detector._find_announcing_tweet(12, [_tweet("Batch 112 processed clean.")]) is None


class TestComputeGapsNumberCollision:
    def test_a_short_number_issue_still_surfaces_when_only_a_longer_number_is_tweeted(self):
        # The real, still-unannounced gap (#12) must not vanish just
        # because an unrelated tweet mentions #123.
        issues = [_issue(12, closed_at=datetime(2026, 7, 25, 0, 0, tzinfo=timezone.utc))]
        tweets = [_tweet("#123 shipped a batch of fixes today.", created_at=datetime(2026, 7, 26, 9, 0, tzinfo=timezone.utc))]

        surfaced, excluded = detector.compute_gaps(issues, tweets, now=_NOW)

        assert excluded == []
        surfaced_slugs = {g.slug for g in surfaced}
        assert "issue-closed-not-tweeted-12" in surfaced_slugs

    def test_an_exact_number_match_still_excludes_the_issue(self):
        issues = [_issue(13, closed_at=datetime(2026, 7, 20, 0, 0, tzinfo=timezone.utc))]
        tweets = [_tweet("#13 is live now.", created_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc))]

        surfaced, excluded = detector.compute_gaps(issues, tweets, now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "issue-tweeted-13" in excluded_slugs


class TestComputeGapsAgeGate:
    def test_a_stale_unannounced_close_scores_above_the_bar(self):
        issues = [_issue(12, closed_at=datetime(2026, 7, 25, 0, 0, tzinfo=timezone.utc))]
        surfaced, _ = detector.compute_gaps(issues, [], now=_NOW)
        assert surfaced[0].confidence == pytest.approx(0.85)

    def test_a_fresh_unannounced_close_scores_below_the_bar(self):
        issues = [_issue(14, closed_at=datetime(2026, 7, 27, 6, 0, tzinfo=timezone.utc))]
        surfaced, _ = detector.compute_gaps(issues, [], now=_NOW)
        assert surfaced[0].confidence == pytest.approx(0.55)

    def test_surfaced_gaps_sort_by_confidence_descending(self):
        issues = [
            _issue(14, closed_at=datetime(2026, 7, 27, 6, 0, tzinfo=timezone.utc)),
            _issue(12, closed_at=datetime(2026, 7, 25, 0, 0, tzinfo=timezone.utc)),
        ]
        surfaced, _ = detector.compute_gaps(issues, [], now=_NOW)
        confidences = [g.confidence for g in surfaced]
        assert confidences == sorted(confidences, reverse=True)


class TestComputeGapsClosedAtGuard:
    def test_an_issue_with_no_closed_at_raises_a_named_error_not_a_bare_assertionerror(self):
        # compute_gaps() is a public function -- nothing in the type system
        # stops a caller from handing it a ClosedIssue built directly (not
        # through load_closed_issues()'s own filter) with closed_at=None.
        # Reproduced live pre-fix: a bare `AssertionError` with no context,
        # the same "assert stripped by python -O" shape task 618/621 already
        # named. Fixed with an explicit, named ValueError.
        issue = detector.ClosedIssue(
            number=1, title="no closed_at", state="closed", closed_at=None,
            url="https://github.com/example/example-repo/issues/1",
        )
        with pytest.raises(ValueError, match="reached the surfaced-gap branch"):
            detector.compute_gaps([issue], [], now=_NOW)


class TestLoadClosedIssuesFiltersState:
    def test_load_closed_issues_excludes_open(self, tmp_path: Path):
        rows = [
            {"number": 1, "title": "closed", "state": "closed",
             "closed_at": "2026-07-20T00:00:00Z", "url": "https://example.com/1"},
            {"number": 2, "title": "still open", "state": "open",
             "closed_at": None, "url": "https://example.com/2"},
        ]
        path = tmp_path / "issues.json"
        path.write_text(json.dumps(rows))

        issues = detector.load_closed_issues(path)

        assert [i.number for i in issues] == [1]

    def test_load_closed_issues_parses_the_real_fixture(self):
        issues = detector.load_closed_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.ClosedIssue) for i in issues)
        assert all(i.number for i in issues)

    def test_load_tweets_parses_the_real_fixture(self):
        tweets = detector.load_tweets()
        assert len(tweets) > 0
        assert all(isinstance(t, detector.Tweet) for t in tweets)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_closed_issues_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_closed_issues(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_tweets_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_tweets(bad_file)


class TestRunRecipeScanAgainstShippedFixture:
    def test_elects_12_as_the_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "issue-closed-not-tweeted-12"
        assert result["primary_gap"]["confidence"] == pytest.approx(0.85)

    def test_14_is_weighed_in_the_tail_not_hidden_and_not_primary(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "issue-closed-not-tweeted-14" in tail_slugs

    def test_13_is_excluded_as_already_tweeted(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "issue-tweeted-13" in excluded_slugs

    def test_still_open_issues_produce_no_candidate_at_all(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = (
            {result["primary_gap"]["slug"]} if result["primary_gap"] else set()
        ) | {g["slug"] for g in result["tail"]} | {g["slug"] for g in result["excluded"]}
        assert not any("-15" in s for s in all_slugs)
