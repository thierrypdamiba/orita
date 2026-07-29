"""Tests for RECIPES/readme-credited-not-thanked/detector.py's own detection
logic -- the fifteenth real recipe, and the deliberate inverse of
`contributor-thanked-not-credited` (task 371).

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this test
exercises the exact module a live scan would import, not a copy -- same
discipline as `test_contributor_thanked_not_credited_detector.py` and every
sibling recipe test in this file.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "readme-credited-not-thanked" / "detector.py"

_spec = importlib.util.spec_from_file_location(
    "seam_engine._recipe_readme_credited_not_thanked_test", DETECTOR_PATH
)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

# Matches the shipped fixture's own span: oldest tweet 2026-07-15T08:00:00Z.
# Pinned past the fixture's own oldest tweet by more than the 96h coverage
# bar, so the shipped-fixture tests below exercise the real "coverage
# sufficient" branch, not a coincidence of wall-clock drift.
_NOW = datetime(2026, 7, 22, 12, 0, 0, tzinfo=timezone.utc)

_README = (
    "# Repo\n\n## Thanks\n\n- @mortal-fixer -- the badge-cache fix.\n"
    "- @quiet-helper -- a typo fix.\n\n"
    "## Houses\n\n- @off-by-one -- the Warden of the Gap.\n"
)


def _tweet(text: str, *, id: str = "T-x", created_at: datetime | None = None) -> "detector.Tweet":
    return detector.Tweet(
        id=id, text=text,
        created_at=created_at or datetime(2026, 7, 16, 9, 0, 0, tzinfo=timezone.utc),
        url=f"https://x.com/oritatown/status/{id}",
    )


class TestCreditedHandles:
    def test_extracts_every_handle_in_the_thanks_section(self):
        assert detector.credited_handles(_README) == ["mortal-fixer", "quiet-helper"]

    def test_a_handle_outside_the_thanks_section_is_never_extracted(self):
        # @off-by-one lives under "## Houses", not "## Thanks" -- the whole
        # point of section-scoping, proven here rather than just asserted.
        assert "off-by-one" not in detector.credited_handles(_README)

    def test_a_readme_with_no_thanks_section_credits_nobody(self):
        assert detector.credited_handles("# Repo\n\nNo thanks section here.\n") == []

    def test_a_thanks_section_at_the_end_of_the_file_is_still_read_in_full(self):
        readme = "# Repo\n\n## Thanks\n\n- @lonewolf -- the only entry.\n"
        assert detector.credited_handles(readme) == ["lonewolf"]


class TestThankedHandles:
    def test_a_thanks_shaped_tweet_marks_its_handle_thanked(self):
        tweets = [_tweet("Thanks @mortal-fixer for the fix")]
        assert detector._thanked_handles(tweets) == {"mortal-fixer"}

    def test_a_bare_mention_does_not_count_as_thanked(self):
        tweets = [_tweet("cc @mortal-fixer, thoughts?")]
        assert detector._thanked_handles(tweets) == set()

    def test_case_insensitive(self):
        tweets = [_tweet("THANKS @Mortal-Fixer!!")]
        assert detector._thanked_handles(tweets) == {"mortal-fixer"}


class TestMentionedAnywhere:
    def test_a_bare_mention_counts_as_mentioned(self):
        tweets = [_tweet("cc @quiet-helper, thoughts?")]
        assert detector._mentioned_anywhere("quiet-helper", tweets) is True

    def test_no_mention_at_all_is_not_mentioned(self):
        tweets = [_tweet("Today's Fencepost Report: nothing cleared the bar.")]
        assert detector._mentioned_anywhere("quiet-helper", tweets) is False

    def test_a_handle_that_is_a_substring_of_a_mentioned_one_is_not_falsely_mentioned(self):
        tweets = [_tweet("cc @quiet-helper-two, thoughts?")]
        assert detector._mentioned_anywhere("quiet-helper", tweets) is False


class TestComputeGaps:
    def test_an_already_thanked_credited_handle_is_excluded_not_surfaced(self):
        tweets = [_tweet("Thanks @mortal-fixer for the fix")]
        surfaced, excluded = detector.compute_gaps(["mortal-fixer"], tweets, now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "readme-handle-already-thanked-mortal-fixer"
        assert excluded[0].confidence == 0.0

    def test_total_silence_past_the_coverage_window_is_surfaced_at_high_confidence(self):
        tweets = [_tweet("Today's Fencepost Report: nothing cleared the bar.",
                          created_at=datetime(2026, 7, 15, 8, 0, 0, tzinfo=timezone.utc))]
        surfaced, excluded = detector.compute_gaps(["quiet-helper"], tweets, now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "readme-credited-not-thanked-quiet-helper"
        assert surfaced[0].confidence == 0.85

    def test_total_silence_inside_the_coverage_window_is_surfaced_at_low_confidence(self):
        tweets = [_tweet("Today's Fencepost Report: nothing cleared the bar.",
                          created_at=datetime(2026, 7, 21, 6, 0, 0, tzinfo=timezone.utc))]
        surfaced, excluded = detector.compute_gaps(["quiet-helper"], tweets, now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_mere_mention_scores_low_confidence_even_past_the_coverage_window(self):
        tweets = [_tweet("cc @quiet-helper, thoughts?",
                          created_at=datetime(2026, 7, 15, 8, 0, 0, tzinfo=timezone.utc))]
        surfaced, excluded = detector.compute_gaps(["quiet-helper"], tweets, now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_no_tweets_at_all_is_the_shortest_possible_coverage_window(self):
        surfaced, excluded = detector.compute_gaps(["quiet-helper"], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_multiple_handles_are_judged_independently(self):
        tweets = [
            _tweet("Thanks @mortal-fixer for the fix", id="T-1",
                   created_at=datetime(2026, 7, 16, 9, 0, 0, tzinfo=timezone.utc)),
            _tweet("Today's Fencepost Report: nothing cleared the bar.", id="T-2",
                   created_at=datetime(2026, 7, 15, 8, 0, 0, tzinfo=timezone.utc)),
        ]
        surfaced, excluded = detector.compute_gaps(["mortal-fixer", "quiet-helper"], tweets, now=_NOW)

        assert len(surfaced) == 1 and surfaced[0].slug == "readme-credited-not-thanked-quiet-helper"
        assert len(excluded) == 1 and excluded[0].slug == "readme-handle-already-thanked-mortal-fixer"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert result["source"] == "fixture"
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "readme-credited-not-thanked-quiet-helper"
        assert result["primary_gap"]["confidence"] >= result["confidence_bar"]

    def test_the_shipped_fixture_weighs_the_mentioned_but_not_thanked_handle_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = [g["slug"] for g in result["tail"]]
        assert any("early-scout" in s for s in tail_slugs)

    def test_the_shipped_fixture_excludes_the_already_thanked_handle(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {e["slug"] for e in result["excluded"]}
        assert "readme-handle-already-thanked-mortal-fixer" in excluded_slugs

    def test_the_houses_section_handles_never_become_candidates(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = (
            [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        ) + [g["slug"] for g in result["tail"]] + [e["slug"] for e in result["excluded"]]
        assert not any("off-by-one" in s or "nisaba" in s for s in all_slugs)


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
        assert "quiet-helper" in content

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
