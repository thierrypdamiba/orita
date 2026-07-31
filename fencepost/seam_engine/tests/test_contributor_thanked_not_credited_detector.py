"""Tests for RECIPES/contributor-thanked-not-credited/detector.py's own
detection logic -- the fifth real recipe, and the second cross-toolkit one
(X + GitHub) after `release-not-tweeted`.

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this test
exercises the exact module a live scan would import, not a copy -- same
discipline as `test_release_not_tweeted_detector.py` and
`test_dangling_issue_reference_detector.py`.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "contributor-thanked-not-credited" / "detector.py"

_spec = importlib.util.spec_from_file_location(
    "seam_engine._recipe_contributor_thanked_not_credited_test", DETECTOR_PATH
)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=timezone.utc)


def _tweet(text: str, *, id: str = "T-x", created_at: datetime | None = None) -> "detector.Tweet":
    return detector.Tweet(
        id=id, text=text,
        created_at=created_at or datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc),
        url=f"https://x.com/oritatown/status/{id}",
    )


_README = "# Repo\n\n## Thanks\n\n- @mortal-fixer -- the badge-cache fix.\n"


class TestThankedHandleExtraction:
    def test_a_thanks_shaped_mention_is_extracted(self):
        assert detector._thanked_handle("Thanks @newcomer99 for the PR") == "newcomer99"

    def test_a_thank_you_shaped_mention_is_extracted(self):
        assert detector._thanked_handle("Thank you @newcomer99 for the PR") == "newcomer99"

    def test_a_bare_mention_with_no_thanks_language_is_not_extracted(self):
        assert detector._thanked_handle("Cc @newcomer99, thoughts?") is None

    def test_a_tweet_with_no_mention_at_all_is_not_extracted(self):
        assert detector._thanked_handle("Today's Fencepost Report: nothing cleared the bar.") is None

    def test_case_insensitive(self):
        assert detector._thanked_handle("THANKS @newcomer99!!") == "newcomer99"


class TestIsCredited:
    def test_a_handle_present_in_the_readme_is_credited(self):
        assert detector._is_credited("mortal-fixer", _README) is True

    def test_a_handle_absent_from_the_readme_is_not_credited(self):
        assert detector._is_credited("newcomer99", _README) is False

    def test_case_insensitive(self):
        assert detector._is_credited("MORTAL-FIXER", _README) is True

    def test_a_handle_that_is_a_substring_of_a_credited_one_is_not_falsely_credited(self):
        # @mortal is not @mortal-fixer -- word-boundary matching, not bare substring.
        assert detector._is_credited("mortal", _README) is False


class TestComputeGaps:
    def test_a_thanked_uncredited_handle_past_the_window_is_surfaced_at_high_confidence(self):
        tweets = [_tweet("Thanks @newcomer99 for the PR", created_at=datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc))]
        surfaced, excluded = detector.compute_gaps(tweets, _README, now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "contributor-thanked-not-credited-newcomer99"
        assert surfaced[0].confidence == 0.85

    def test_a_thanked_uncredited_handle_inside_the_window_is_surfaced_at_low_confidence(self):
        tweets = [_tweet("Thanks @freshcontributor for the fix", created_at=datetime(2026, 7, 21, 6, 0, 0, tzinfo=timezone.utc))]
        surfaced, excluded = detector.compute_gaps(tweets, _README, now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_thanked_already_credited_handle_is_excluded_not_surfaced(self):
        tweets = [_tweet("Thanks @mortal-fixer for the fix")]
        surfaced, excluded = detector.compute_gaps(tweets, _README, now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "contributor-credited-mortal-fixer"
        assert excluded[0].confidence == 0.0

    def test_a_tweet_with_no_thanks_shaped_language_produces_no_candidate_at_all(self):
        tweets = [_tweet("Today's Fencepost Report: nothing cleared the bar.")]
        surfaced, excluded = detector.compute_gaps(tweets, _README, now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_multiple_tweets_are_judged_independently(self):
        tweets = [
            _tweet("Thanks @mortal-fixer for the fix", id="T-1"),
            _tweet("Thanks @newcomer99 for the PR", id="T-2", created_at=datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc)),
            _tweet("Today's Fencepost Report: nothing cleared the bar.", id="T-3"),
        ]
        surfaced, excluded = detector.compute_gaps(tweets, _README, now=_NOW)

        assert len(surfaced) == 1 and surfaced[0].slug == "contributor-thanked-not-credited-newcomer99"
        assert len(excluded) == 1 and excluded[0].slug == "contributor-credited-mortal-fixer"

    def test_two_tweets_thanking_the_same_uncredited_handle_produce_one_candidate(self):
        # Task 443: pre-fix, two tweets thanking the same still-uncredited
        # handle produced two identically-slugged surfaced candidates that
        # tied each other out of rank()'s SEPARATION_MARGIN -- the exact
        # false-negative shape task 442 already fixed for the
        # *-dangling-reference family, unswept here until now.
        tweets = [
            _tweet("Thanks @newcomer99 for the PR", id="T-1",
                   created_at=datetime(2026, 7, 15, 8, 0, 0, tzinfo=timezone.utc)),
            _tweet("Thank you @newcomer99 for the follow-up too", id="T-2",
                   created_at=datetime(2026, 7, 19, 8, 0, 0, tzinfo=timezone.utc)),
        ]
        surfaced, excluded = detector.compute_gaps(tweets, _README, now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "contributor-thanked-not-credited-newcomer99"
        # The earlier (2026-07-15) tweet is the one used -- it's the one
        # that actually determines how overdue the credit is.
        assert "T-1" in surfaced[0].evidence[0]

    def test_a_repeat_thank_you_is_deduped_case_insensitively(self):
        tweets = [
            _tweet("Thanks @Newcomer99 for the PR", id="T-1",
                   created_at=datetime(2026, 7, 15, 8, 0, 0, tzinfo=timezone.utc)),
            _tweet("Thanks @newcomer99 again", id="T-2",
                   created_at=datetime(2026, 7, 19, 8, 0, 0, tzinfo=timezone.utc)),
        ]
        surfaced, excluded = detector.compute_gaps(tweets, _README, now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert result["source"] == "fixture"
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "contributor-thanked-not-credited-newcomer99"
        assert result["primary_gap"]["confidence"] >= result["confidence_bar"]

    def test_the_shipped_fixture_weighs_the_fresh_thank_you_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = [g["slug"] for g in result["tail"]]
        assert any("freshcontributor" in s for s in tail_slugs)

    def test_the_shipped_fixture_excludes_the_already_credited_handle(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {e["slug"] for e in result["excluded"]}
        assert "contributor-credited-mortal-fixer" in excluded_slugs

    def test_two_tweets_thanking_the_same_handle_still_elects_a_primary(self, tmp_path: Path):
        # Task 443: pre-fix, this exact shape (one still-uncredited handle
        # thanked in two separate tweets) produced two identically-slugged
        # surfaced candidates that tied each other out of rank()'s
        # SEPARATION_MARGIN -- primary_gap came back None even though there
        # is exactly one real, single gap.
        tweets_path = tmp_path / "tweets.json"
        tweets_path.write_text(json.dumps([
            {
                "id": "T-1", "text": "Thanks @newcomer99 for the PR",
                "created_at": "2026-07-15T08:00:00Z",
                "url": "https://x.com/oritatown/status/1",
            },
            {
                "id": "T-2", "text": "Thank you @newcomer99 for the follow-up too",
                "created_at": "2026-07-19T08:00:00Z",
                "url": "https://x.com/oritatown/status/2",
            },
        ]))
        readme_path = tmp_path / "readme.json"
        readme_path.write_text(json.dumps({"path": "README.md", "content": "# Repo\n"}))

        result = detector.run_recipe_scan(tweets_path, readme_path, now=_NOW)

        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "contributor-thanked-not-credited-newcomer99"


class TestLoaders:
    """load_tweets/load_readme -- proves each loader parses the real shipped
    fixture, and each refuses a syntactically valid but wrong-shaped JSON
    payload with a named ValueError rather than a bare crash three frames
    deeper -- the same bug class tasks 358/359/361/362 closed on this
    engine's other loaders, built in here from the start."""

    def test_load_tweets_parses_the_real_fixture(self):
        tweets = detector.load_tweets()
        assert len(tweets) > 0
        assert all(isinstance(t, detector.Tweet) for t in tweets)

    def test_load_readme_parses_the_real_fixture(self):
        content = detector.load_readme()
        assert isinstance(content, str)
        assert "mortal-fixer" in content

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_tweets_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_tweets(bad_file)

    @pytest.mark.parametrize("bad_value", [[1, 2], 5, None, "x", True])
    def test_load_readme_raises_named_error_not_typeerror_when_json_is_not_an_object(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON object"):
            detector.load_readme(bad_file)

    def test_load_readme_raises_named_error_when_content_field_is_not_a_string(self, tmp_path: Path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps({"path": "README.md", "content": 5}))
        with pytest.raises(ValueError, match="expected a string 'content' field"):
            detector.load_readme(bad_file)
