"""Tests for RECIPES/mention-claims-unfixed-issue/detector.py's own
detection logic -- the forty-seventh real recipe: a mortal's own X mention
of the connected account invokes a real closing keyword against an issue,
but the issue never actually closed.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "mention-claims-unfixed-issue" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_mention_claims_unfixed_issue_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 6, 12, 0, 0, tzinfo=timezone.utc)


def _mention(mid: str, text: str, created_at: datetime, author: str = "some-mortal") -> "detector.Mention":
    return detector.Mention(
        id=mid, author=author, text=text, created_at=created_at,
        url=f"https://x.com/{author}/status/{mid}",
    )


def _issue(number: int, state: str = "open") -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestClaimedIssueNumbers:
    def test_fixes_hash_n(self):
        assert detector._claimed_issue_numbers("Fixes #2101.") == [2101]

    def test_closes_hash_n(self):
        assert detector._claimed_issue_numbers("Closes #2102 this time.") == [2102]

    def test_resolves_hash_n(self):
        assert detector._claimed_issue_numbers("Resolves #2103.") == [2103]

    def test_past_tense_fixed_hash_n(self):
        assert detector._claimed_issue_numbers("Fixed #2104.") == [2104]

    def test_case_insensitive(self):
        assert detector._claimed_issue_numbers("FIXES #2105.") == [2105]

    def test_present_participle_closing_never_matches(self):
        # Iron Rule #8's own prescribed safe form must never trip this
        # recipe's claim grammar either.
        assert detector._claimed_issue_numbers("Closing #2106 today, in prose only.") == []

    def test_bare_hash_n_with_no_claim_verb_is_never_extracted(self):
        # This is dangling-issue-reference's/mention-dangling-reference's
        # own broader regex; a bare "see #N" mention in prose is not a
        # fixed-it claim.
        assert detector._claimed_issue_numbers("See #2107 for background.") == []

    def test_multiple_claims_in_one_mention(self):
        assert detector._claimed_issue_numbers("Fixes #2101. Closes #2102.") == [2101, 2102]

    def test_duplicate_claim_in_one_mention_is_not_deduplicated_at_extraction(self):
        # De-duplication happens in compute_gaps, not here -- this function
        # is a pure extraction, faithfully reporting every match.
        assert detector._claimed_issue_numbers("Fixes #2101 and closes #2101 again.") == [2101, 2101]


class TestComputeGaps:
    def test_a_stale_unfixed_claim_is_surfaced_at_high_confidence(self):
        mention = _mention("M-1", "Fixes #2101.", _NOW - timedelta(hours=50))
        issue = _issue(2101, state="open")

        surfaced, excluded = detector.compute_gaps([mention], [issue], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "mention-claims-unfixed-issue-M-1-2101"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_unfixed_claim_is_surfaced_at_low_confidence(self):
        mention = _mention("M-2", "Resolves #2103.", _NOW - timedelta(hours=4))
        issue = _issue(2103, state="open")

        surfaced, excluded = detector.compute_gaps([mention], [issue], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_closed_claimed_issue_is_excluded_not_surfaced(self):
        mention = _mention("M-3", "Closes #2102.", _NOW - timedelta(hours=50))
        issue = _issue(2102, state="closed")

        surfaced, excluded = detector.compute_gaps([mention], [issue], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-M-3-2102" in excluded_slugs

    def test_a_claim_naming_an_issue_that_does_not_exist_is_excluded_not_surfaced(self):
        mention = _mention("M-4", "Fix #2999 today.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([mention], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-issue-not-found-M-4-2999" in excluded_slugs

    def test_a_mention_with_no_claim_phrase_produces_no_candidate_at_all(self):
        mention = _mention("M-5", "Housekeeping only, see #2105 for background.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([mention], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-M-5"

    def test_a_duplicate_claim_in_one_mention_produces_one_candidate_not_two(self):
        mention = _mention("M-6", "Fixes #2101 and closes #2101 again.", _NOW - timedelta(hours=50))
        issue = _issue(2101, state="open")

        surfaced, excluded = detector.compute_gaps([mention], [issue], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "mention-claims-unfixed-issue-M-6-2101"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "mention-claims-unfixed-issue-M-2101-2101"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_fresh_claim_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "mention-claims-unfixed-issue-M-2102-2103" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_claim_and_the_dangling_and_no_claim_mentions(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-M-2103-2102" in excluded_slugs
        assert "claimed-issue-not-found-M-2104-2999" in excluded_slugs
        assert "no-claim-phrase-M-2105" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_2101_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("mention-claims-unfixed-issue-M-2101-2101") == 1


class TestLoaders:
    """load_mentions/load_issues -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_mentions_parses_the_real_fixture(self):
        mentions = detector.load_mentions()
        assert len(mentions) > 0
        assert all(isinstance(m, detector.Mention) for m in mentions)

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_mentions_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_mentions(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_issues_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issues(bad_file)
