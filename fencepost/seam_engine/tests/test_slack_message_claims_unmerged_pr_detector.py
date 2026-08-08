"""Tests for RECIPES/slack-message-claims-unmerged-pr/detector.py's own
detection logic -- the seventy-second real recipe: a message posted to a
Slack channel claims a pull request shipped, but the named PR never
actually merged. The PR-claim twin of
test_slack_message_claims_open_milestone_detector.py, and the Slack-side
twin of test_linear_comment_claims_unmerged_pr_detector.py.

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this test
exercises the exact module a live scan would import, not a copy.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "slack-message-claims-unmerged-pr" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_slack_message_claims_unmerged_pr_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 8, 12, 0, 0, tzinfo=timezone.utc)


def _message(mid: str, text: str, created_at: datetime, author: str = "some-mortal", channel: str = "#dev-updates") -> "detector.Message":
    return detector.Message(
        id=mid, channel=channel, author=author, text=text, created_at=created_at,
        url=f"https://orita-town.slack.com/archives/C0DEVCHAN0/p{mid}",
    )


def _pull(number: int, state: str = "open", merged: bool = False) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, merged=merged,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestClaimedPrNumbersReuse:
    """detector.py imports seam_engine.pr_claims.claimed_pr_numbers rather
    than retyping the grammar -- these tests exercise it through the
    detector's own bound name, proving the import actually landed and
    behaves as every sibling *-claims-unmerged-pr recipe expects."""

    def test_ships_hash_n(self):
        assert detector._claimed_pr_numbers("This also ships #601.") == [601]

    def test_includes_hash_n(self):
        assert detector._claimed_pr_numbers("Includes #602 as a side effect.") == [602]

    def test_merges_hash_n(self):
        assert detector._claimed_pr_numbers("I think this merges #603 too.") == [603]

    def test_via_hash_n(self):
        assert detector._claimed_pr_numbers("Fixed via #604 in the last commit.") == [604]

    def test_case_insensitive(self):
        assert detector._claimed_pr_numbers("SHIPS #605.") == [605]

    def test_bare_hash_n_with_no_claim_verb_is_never_extracted(self):
        assert detector._claimed_pr_numbers("Same root cause as #607, not touching here.") == []

    def test_multiple_claims_in_one_message(self):
        assert detector._claimed_pr_numbers("Ships #601. Also merges #602.") == [601, 602]

    def test_duplicate_claim_in_one_message_is_not_deduplicated_at_extraction(self):
        assert detector._claimed_pr_numbers("Ships #601 -- yes, really via #601.") == [601, 601]


class TestComputeGaps:
    def test_a_stale_unmerged_claim_is_surfaced_at_high_confidence(self):
        message = _message("S-1", "Ships #601 finally.", _NOW - timedelta(hours=50))
        pr = _pull(601, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([message], [pr], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "slack-message-claims-unmerged-pr-S-1-601"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_unmerged_claim_is_surfaced_at_low_confidence(self):
        message = _message("S-2", "Heard this merges #603, nice fix.", _NOW - timedelta(hours=4))
        pr = _pull(603, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([message], [pr], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_confidence_boundary_exactly_24_hours_is_stale_not_fresh(self):
        message = _message("S-3", "Includes #603.", _NOW - timedelta(hours=24))
        pr = _pull(603, state="open", merged=False)

        surfaced, _excluded = detector.compute_gaps([message], [pr], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_confidence_boundary_just_under_24_hours_is_fresh(self):
        message = _message("S-4", "Includes #603.", _NOW - timedelta(hours=23, minutes=59))
        pr = _pull(603, state="open", merged=False)

        surfaced, _excluded = detector.compute_gaps([message], [pr], now=_NOW)

        assert surfaced[0].confidence == 0.5

    def test_a_merged_claimed_pr_is_excluded_not_surfaced(self):
        message = _message("S-5", "Includes #602 as a side effect.", _NOW - timedelta(hours=50))
        pr = _pull(602, state="closed", merged=True)

        surfaced, excluded = detector.compute_gaps([message], [pr], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-S-5-602" in excluded_slugs

    def test_a_closed_but_unmerged_claimed_pr_is_still_surfaced(self):
        # Closed without merging is still a false "shipped" claim -- the
        # PR's own state disagrees with the Slack message either way.
        message = _message("S-6", "Ships #604 today.", _NOW - timedelta(hours=50))
        pr = _pull(604, state="closed", merged=False)

        surfaced, excluded = detector.compute_gaps([message], [pr], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.85

    def test_a_claim_naming_a_pr_that_does_not_exist_is_excluded_not_surfaced(self):
        message = _message("S-7", "Ships #999 today, guess it landed.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([message], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-pr-not-found-S-7-999" in excluded_slugs

    def test_a_message_with_no_claim_phrase_produces_no_candidate_at_all(self):
        message = _message("S-8", "Another quiet week, see #605 for background.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([message], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-S-8"

    def test_a_duplicate_claim_in_one_message_produces_one_candidate_not_two(self):
        message = _message("S-9", "Ships #601 -- yes, really via #601.", _NOW - timedelta(hours=50))
        pr = _pull(601, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([message], [pr], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "slack-message-claims-unmerged-pr-S-9-601"

    def test_evidence_carries_both_the_message_url_and_the_pr_url(self):
        message = _message("S-10", "Ships #601 finally.", _NOW - timedelta(hours=50))
        pr = _pull(601, state="open", merged=False)

        surfaced, _excluded = detector.compute_gaps([message], [pr], now=_NOW)

        assert surfaced[0].evidence == [message.url, pr.url]

    def test_excluded_not_found_evidence_carries_only_the_message_url(self):
        message = _message("S-11", "Ships #999 today.", _NOW - timedelta(hours=50))

        _surfaced, excluded = detector.compute_gaps([message], [], now=_NOW)

        assert excluded[0].evidence == [message.url]

    def test_no_surfaced_or_excluded_candidates_for_an_empty_message_list(self):
        surfaced, excluded = detector.compute_gaps([], [_pull(601)], now=_NOW)
        assert surfaced == []
        assert excluded == []

    def test_surfaced_candidates_are_sorted_by_confidence_descending(self):
        stale = _message("S-12", "Ships #601 finally.", _NOW - timedelta(hours=50))
        fresh = _message("S-13", "Ships #603 finally.", _NOW - timedelta(hours=4))
        pulls = [_pull(601, state="open", merged=False), _pull(603, state="open", merged=False)]

        surfaced, _excluded = detector.compute_gaps([fresh, stale], pulls, now=_NOW)

        assert [g.confidence for g in surfaced] == [0.85, 0.5]

    def test_headline_and_detail_never_grade_or_blame_the_poster(self):
        # CONTRIBUTING.md's "No grading, ever" law: the text may name the
        # gap, never the poster's own error.
        message = _message("S-14", "Ships #601 finally.", _NOW - timedelta(hours=50), author="some-mortal")
        pr = _pull(601, state="open", merged=False)

        surfaced, _excluded = detector.compute_gaps([message], [pr], now=_NOW)

        combined = (surfaced[0].headline + surfaced[0].detail).lower()
        for word in ("mistake", "wrong", "blame", "dropped the ball", "error", "fault"):
            assert word not in combined


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "slack-message-claims-unmerged-pr-SLK-4101-601"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_fresh_claim_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "slack-message-claims-unmerged-pr-SLK-4102-603" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_not_found_and_no_claim_messages(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-SLK-4103-602" in excluded_slugs
        assert "claimed-pr-not-found-SLK-4104-999" in excluded_slugs
        assert "no-claim-phrase-SLK-4105" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_601_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("slack-message-claims-unmerged-pr-SLK-4101-601") == 1

    def test_source_is_marked_fixture_not_live(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["source"] == "fixture"

    def test_run_recipe_scan_defaults_now_to_the_real_wall_clock_when_omitted(self):
        before = datetime.now(timezone.utc)
        result = detector.run_recipe_scan()
        after = datetime.now(timezone.utc)
        generated_at = datetime.fromisoformat(result["generated_at"])
        assert before <= generated_at <= after


class TestLoaders:
    """load_messages/load_pulls -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_messages_parses_the_real_fixture(self):
        messages = detector.load_messages()
        assert len(messages) > 0
        assert all(isinstance(m, detector.Message) for m in messages)

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pulls)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_messages_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_messages(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pulls_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pulls(bad_file)


class TestManifest:
    """The manifest itself: schema-valid, clears the oath, matches the
    fixture/detector this test file exercises."""

    def test_recipe_json_clears_validate_recipe(self):
        from seam_engine.recipes import load_recipe_manifest, validate_recipe

        manifest_path = FENCEPOST_ROOT / "RECIPES" / "slack-message-claims-unmerged-pr" / "recipe.json"
        manifest = load_recipe_manifest(manifest_path)
        validated = validate_recipe(manifest)
        assert validated.slug == "slack-message-claims-unmerged-pr"
        assert validated.toolkit == "slack+github"
        assert set(validated.scopes) == {"SearchChannelMessages", "ListPullRequests"}
