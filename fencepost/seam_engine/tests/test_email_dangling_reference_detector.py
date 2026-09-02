"""Tests for RECIPES/email-dangling-reference/detector.py's own detection
logic -- the ninety-eighth real recipe, and the eleventh leg of the
dangling-reference family (dangling-issue-reference watches commit
messages, mention-dangling-reference watches X mentions, release-note-
dangling-reference watches release notes, issue-body-dangling-reference
watches issue/PR opening bodies, milestone-body-dangling-reference watches
milestone descriptions, own-tweet-dangling-reference watches the town's
own tweets, review-comment-dangling-reference watches a PR's own inline
review comments, issue-comment-dangling-reference watches the ordinary
issue/PR timeline, linear-comment-dangling-reference watches a comment
left on Linear, slack-message-dangling-reference watches a message posted
to Slack; this one watches an inbound email).

Loaded the same way `seam_engine.recipes.load_detector` loads any
recipe's detector at runtime (`importlib.util.spec_from_file_location`),
so this test exercises the exact module a live scan would import, not a
copy -- same discipline as `test_mention_dangling_reference_detector.py`
and every sibling detector test in this engine.
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "email-dangling-reference" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_email_dangling_reference_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 10, 12, 0, 0, tzinfo=timezone.utc)


def _email(id: str, body: str | None, *, sender: str = "some-correspondent@example.com") -> "detector.Email":
    return detector.Email(
        id=id, sender=sender, subject="test", body=body or "",
        received_at=datetime(2026, 8, 6, 9, 0, 0, tzinfo=timezone.utc),
    )


def _issue(number: int) -> "detector.Issue":
    return detector.Issue(number=number, title="an issue", state="open", url=f"https://github.com/example/example-repo/issues/{number}")


def _pull(number: int) -> "detector.PullRequest":
    return detector.PullRequest(number=number, title="a pr", state="open", url=f"https://github.com/example/example-repo/pull/{number}")


class TestDanglingConfidenceIsFlat:
    def test_the_flat_confidence_constant_is_seventy_five_hundredths(self):
        assert detector._DANGLING_CONFIDENCE == 0.75


class TestComputeGaps:
    def test_a_reference_to_a_nonexistent_number_is_surfaced(self):
        emails = [_email("e1", "see #99 for context")]
        surfaced, excluded = detector.compute_gaps(emails, [], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "email-dangling-reference-e1-99"
        assert surfaced[0].confidence == 0.75

    def test_a_reference_matching_a_real_issue_is_excluded(self):
        emails = [_email("e1", "same root cause as #501")]
        surfaced, excluded = detector.compute_gaps(emails, [_issue(501)], [], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].confidence == 0.0

    def test_a_reference_matching_a_real_pr_is_excluded(self):
        emails = [_email("e1", "waiting on #510 to land")]
        surfaced, excluded = detector.compute_gaps(emails, [], [_pull(510)], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].confidence == 0.0

    def test_an_email_with_no_body_is_excluded_outright(self):
        emails = [_email("e1", None)]
        surfaced, excluded = detector.compute_gaps(emails, [], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_an_email_with_no_reference_produces_no_candidates(self):
        emails = [_email("e1", "just a thank-you, nothing to track")]
        surfaced, excluded = detector.compute_gaps(emails, [], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_cross_repo_reference_is_never_extracted(self):
        emails = [_email("e1", "saw arcadeai/gasstation#42, worth a look")]
        surfaced, excluded = detector.compute_gaps(emails, [], [], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_a_repeated_reference_in_one_email_is_deduped(self):
        emails = [_email("e1", "see #99 and also #99 again")]
        surfaced, _excluded = detector.compute_gaps(emails, [], [], now=_NOW)

        assert len(surfaced) == 1

    def test_all_surfaced_candidates_share_the_flat_confidence(self):
        emails = [_email("e1", "see #10"), _email("e2", "see #20")]
        surfaced, _ = detector.compute_gaps(emails, [], [], now=_NOW)

        assert [g.confidence for g in surfaced] == [0.75, 0.75]


class TestRunRecipeScanAgainstOwnFixture:
    def test_the_shipped_fixture_elects_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert result["source"] == "fixture"
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "email-dangling-reference-EML-5101-4501"
        assert result["primary_gap"]["confidence"] == 0.75

    def test_the_shipped_fixture_excludes_the_real_issue_and_pr_matches(self):
        result = detector.run_recipe_scan(now=_NOW)

        excluded_slugs = [g["slug"] for g in result["excluded"]]
        assert "email-ref-matched-EML-5102-4102" in excluded_slugs
        assert "email-ref-matched-EML-5105-4103" in excluded_slugs

    def test_the_shipped_fixture_has_no_tail_coincidence(self):
        result = detector.run_recipe_scan(now=_NOW)

        assert result["tail"] == []
