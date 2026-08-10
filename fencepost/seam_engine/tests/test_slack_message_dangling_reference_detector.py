"""Tests for RECIPES/slack-message-dangling-reference/detector.py's own
detection logic -- the seventy-fifth real recipe, and the tenth leg of
the dangling-reference family (dangling-issue-reference watches commit
messages, mention-dangling-reference watches X mentions, release-note-
dangling-reference watches release notes, issue-body-dangling-reference
watches issue/PR opening bodies, milestone-body-dangling-reference watches
milestone descriptions, own-tweet-dangling-reference watches the town's
own tweets, review-comment-dangling-reference watches a PR's own inline
review comments, issue-comment-dangling-reference watches the ordinary
issue/PR timeline, linear-comment-dangling-reference watches a comment
left on Linear; this one watches a message posted to a Slack channel).

Loaded the same way `seam_engine.recipes.load_detector` loads any
recipe's detector at runtime (`importlib.util.spec_from_file_location`),
so this test exercises the exact module a live scan would import, not a
copy -- same discipline as `test_linear_comment_dangling_reference_detector.py`
and every sibling detector test in this engine.
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "slack-message-dangling-reference" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_slack_message_dangling_reference_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 10, 12, 0, 0, tzinfo=timezone.utc)


def _message(
    id: str, text: str | None, *, channel: str = "#dev-updates", hours_ago: float = 100.0,
) -> "detector.Message":
    created = _NOW.timestamp() - hours_ago * 3600
    return detector.Message(
        id=id, channel=channel, author="some-teammate",
        text=text or "",
        created_at=datetime.fromtimestamp(created, tz=timezone.utc),
        url=f"https://orita-town.slack.com/archives/C00CHANNEL0/p{id}",
    )


def _issue(number: int) -> "detector.Issue":
    return detector.Issue(number=number, url=f"https://github.com/example/example-repo/issues/{number}")


def _pull(number: int) -> "detector.PullRequest":
    return detector.PullRequest(number=number, url=f"https://github.com/example/example-repo/pull/{number}")


class TestConfidenceFor:
    def test_a_message_touched_recently_scores_the_lower_bar(self):
        created = datetime(2026, 8, 10, 10, 0, 0, tzinfo=timezone.utc)  # 2h before NOW
        assert detector._confidence_for(created, now=_NOW) == 0.55

    def test_a_message_untouched_for_a_full_day_scores_the_higher_bar(self):
        created = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)  # 72h before NOW
        assert detector._confidence_for(created, now=_NOW) == 0.85

    def test_exactly_the_grace_window_boundary_scores_the_higher_bar(self):
        created = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)  # exactly 24h
        assert detector._confidence_for(created, now=_NOW) == 0.85

    def test_just_under_the_grace_window_scores_the_lower_bar(self):
        created = datetime(2026, 8, 9, 12, 0, 1, tzinfo=timezone.utc)  # 23h59m59s
        assert detector._confidence_for(created, now=_NOW) == 0.55

    def test_grace_window_constant_is_twenty_four_hours(self):
        assert detector._EDIT_GRACE_WINDOW_HOURS == 24.0


class TestComputeGaps:
    def test_a_reference_to_a_nonexistent_number_is_surfaced(self):
        messages = [_message("m1", "see #99 for context", hours_ago=100.0)]
        surfaced, excluded = detector.compute_gaps(messages, [], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "slack-message-dangling-reference-m1-99"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_dangling_reference_scores_the_lower_bar(self):
        messages = [_message("m1", "see #99 for context", hours_ago=2.0)]
        surfaced, excluded = detector.compute_gaps(messages, [], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.55

    def test_a_reference_matching_a_real_issue_is_excluded(self):
        messages = [_message("m1", "same root cause as #501")]
        surfaced, excluded = detector.compute_gaps(messages, [_issue(501)], [], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].confidence == 0.0

    def test_a_reference_matching_a_real_pr_is_excluded(self):
        messages = [_message("m1", "waiting on #510 to land")]
        surfaced, excluded = detector.compute_gaps(messages, [], [_pull(510)], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].confidence == 0.0

    def test_a_message_with_no_reference_produces_no_candidates(self):
        messages = [_message("m1", "just a thank-you, nothing to track", hours_ago=100.0)]
        surfaced, excluded = detector.compute_gaps(messages, [], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_cross_repo_reference_is_never_extracted(self):
        messages = [_message("m1", "saw arcadeai/gasstation#42, worth a look", hours_ago=100.0)]
        surfaced, excluded = detector.compute_gaps(messages, [], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_repeated_reference_in_one_message_is_deduped(self):
        messages = [_message("m1", "see #99 and also #99 again", hours_ago=100.0)]
        surfaced, _excluded = detector.compute_gaps(messages, [], [], now=_NOW)

        assert len(surfaced) == 1

    def test_surfaced_candidates_sort_by_confidence_descending(self):
        messages = [
            _message("m1", "see #10", hours_ago=2.0),   # 0.55
            _message("m2", "see #20", hours_ago=100.0),  # 0.85
        ]
        surfaced, _ = detector.compute_gaps(messages, [], [], now=_NOW)

        assert [g.confidence for g in surfaced] == [0.85, 0.55]


class TestRunRecipeScanAgainstOwnFixture:
    def test_the_shipped_fixture_elects_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert result["source"] == "fixture"
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "slack-message-dangling-reference-SLK-D-9001-6301"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_one_coincidence_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)

        tail_slugs = [g["slug"] for g in result["tail"]]
        assert "slack-message-dangling-reference-SLK-D-9002-6302" in tail_slugs

    def test_the_shipped_fixture_excludes_the_real_issue_and_pr_matches(self):
        result = detector.run_recipe_scan(now=_NOW)

        excluded_slugs = [g["slug"] for g in result["excluded"]]
        assert "slack-message-ref-matched-SLK-D-9003-6210" in excluded_slugs
        assert "slack-message-ref-matched-SLK-D-9004-6220" in excluded_slugs

    def test_the_shipped_fixture_produces_no_candidate_for_the_reference_free_message(self):
        result = detector.run_recipe_scan(now=_NOW)

        all_slugs = (
            [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        ) + [g["slug"] for g in result["tail"]] + [g["slug"] for g in result["excluded"]]
        assert not any("SLK-D-9005" in slug for slug in all_slugs)
