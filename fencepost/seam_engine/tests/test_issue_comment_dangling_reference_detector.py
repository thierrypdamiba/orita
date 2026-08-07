"""Tests for RECIPES/issue-comment-dangling-reference/detector.py's own
detection logic -- the fifty-third real recipe, and an eighth leg of the
dangling-reference family (dangling-issue-reference watches commit
messages, mention-dangling-reference watches X mentions, release-note-
dangling-reference watches release notes, issue-body-dangling-reference
watches issue/PR opening bodies, milestone-body-dangling-reference watches
milestone descriptions, own-tweet-dangling-reference watches the town's
own tweets, review-comment-dangling-reference watches a PR's own inline
review comments; this one watches the ordinary issue/PR timeline
conversation, shared between issues and pull requests).

Loaded the same way `seam_engine.recipes.load_detector` loads any
recipe's detector at runtime (`importlib.util.spec_from_file_location`),
so this test exercises the exact module a live scan would import, not a
copy -- same discipline as
`test_review_comment_dangling_reference_detector.py` and every sibling
detector test in this engine.
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "issue-comment-dangling-reference" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_issue_comment_dangling_reference_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)


def _comment(
    id: int, body: str | None, *, issue_number: int = 1, hours_ago: float = 100.0,
) -> "detector.IssueComment":
    updated = _NOW.timestamp() - hours_ago * 3600
    return detector.IssueComment(
        id=id, issue_number=issue_number,
        body=body or "",
        updated_at=datetime.fromtimestamp(updated, tz=timezone.utc),
        url=f"https://github.com/example/example-repo/issues/{issue_number}#issuecomment-{id}",
    )


def _issue(number: int) -> "detector.Issue":
    return detector.Issue(number=number, url=f"https://github.com/example/example-repo/issues/{number}")


def _pull(number: int) -> "detector.PullRequest":
    return detector.PullRequest(number=number, url=f"https://github.com/example/example-repo/pull/{number}")


class TestConfidenceFor:
    def test_a_comment_touched_recently_scores_the_lower_bar(self):
        updated = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)  # 2h before NOW
        assert detector._confidence_for(updated, now=_NOW) == 0.55

    def test_a_comment_untouched_for_a_full_day_scores_the_higher_bar(self):
        updated = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)  # 72h before NOW
        assert detector._confidence_for(updated, now=_NOW) == 0.85

    def test_exactly_the_grace_window_boundary_scores_the_higher_bar(self):
        updated = datetime(2026, 7, 31, 12, 0, 0, tzinfo=timezone.utc)  # exactly 24h
        assert detector._confidence_for(updated, now=_NOW) == 0.85

    def test_just_under_the_grace_window_scores_the_lower_bar(self):
        updated = datetime(2026, 7, 31, 12, 0, 1, tzinfo=timezone.utc)  # 23h59m59s
        assert detector._confidence_for(updated, now=_NOW) == 0.55

    def test_grace_window_constant_is_twenty_four_hours(self):
        assert detector._EDIT_GRACE_WINDOW_HOURS == 24.0


class TestComputeGaps:
    def test_a_reference_to_a_nonexistent_number_is_surfaced(self):
        comments = [_comment(1, "see #99 for context", hours_ago=100.0)]
        surfaced, excluded = detector.compute_gaps(comments, [], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "issue-comment-dangling-reference-1-99"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_dangling_reference_scores_the_lower_bar(self):
        comments = [_comment(1, "see #99 for context", hours_ago=2.0)]
        surfaced, excluded = detector.compute_gaps(comments, [], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.55

    def test_a_reference_matching_a_real_issue_is_excluded(self):
        comments = [_comment(1, "same root cause as #501")]
        surfaced, excluded = detector.compute_gaps(comments, [_issue(501)], [], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].confidence == 0.0

    def test_a_reference_matching_a_real_pr_is_excluded(self):
        comments = [_comment(1, "waiting on #510 to land")]
        surfaced, excluded = detector.compute_gaps(comments, [], [_pull(510)], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].confidence == 0.0

    def test_a_comment_on_a_pull_request_is_checked_the_same_way(self):
        # GitHub's own issue-comments endpoint is shared between issues and
        # PRs -- this recipe's whole reason to exist is that shared surface,
        # so a comment whose issue_number actually names a PR must behave
        # identically to one that names an issue.
        comments = [_comment(1, "see #99 for context", issue_number=42, hours_ago=100.0)]
        surfaced, excluded = detector.compute_gaps(comments, [], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.85

    def test_a_comment_with_no_body_is_excluded_outright(self):
        comments = [_comment(1, None, hours_ago=100.0)]
        surfaced, excluded = detector.compute_gaps(comments, [], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_comment_with_empty_body_is_excluded_outright(self):
        comments = [_comment(1, "", hours_ago=100.0)]
        surfaced, excluded = detector.compute_gaps(comments, [], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_cross_repo_reference_is_never_extracted(self):
        comments = [_comment(1, "saw arcadeai/gasstation#42, worth a look", hours_ago=100.0)]
        surfaced, excluded = detector.compute_gaps(comments, [], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_comment_with_no_reference_produces_no_candidates(self):
        comments = [_comment(1, "just a thank-you, nothing to track", hours_ago=100.0)]
        surfaced, excluded = detector.compute_gaps(comments, [], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_repeated_reference_in_one_comment_is_deduped(self):
        comments = [_comment(1, "see #99 and also #99 again", hours_ago=100.0)]
        surfaced, _excluded = detector.compute_gaps(comments, [], [], now=_NOW)

        assert len(surfaced) == 1

    def test_surfaced_candidates_sort_by_confidence_descending(self):
        comments = [
            _comment(1, "see #10", hours_ago=2.0),   # 0.55
            _comment(2, "see #20", hours_ago=100.0),  # 0.85
        ]
        surfaced, _ = detector.compute_gaps(comments, [], [], now=_NOW)

        assert [g.confidence for g in surfaced] == [0.85, 0.55]


class TestRunRecipeScanAgainstOwnFixture:
    def test_the_shipped_fixture_elects_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert result["source"] == "fixture"
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "issue-comment-dangling-reference-7002-9999"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_one_coincidence_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)

        tail_slugs = [g["slug"] for g in result["tail"]]
        assert "issue-comment-dangling-reference-7003-8888" in tail_slugs

    def test_the_shipped_fixture_excludes_the_real_issue_and_pr_matches(self):
        result = detector.run_recipe_scan(now=_NOW)

        excluded_slugs = [g["slug"] for g in result["excluded"]]
        assert "issue-comment-ref-matched-7001-501" in excluded_slugs
        assert "issue-comment-ref-matched-7006-510" in excluded_slugs
