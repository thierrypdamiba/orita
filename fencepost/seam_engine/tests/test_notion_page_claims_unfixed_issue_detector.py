"""Tests for RECIPES/notion-page-claims-unfixed-issue/detector.py's own
detection logic -- the hundred-sixteenth real recipe, and the first
Notion leg of the claims-unfixed-issue family: a Notion page invokes a
real closing keyword against an issue, but the issue never actually
closed.

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this test
exercises the exact module a live scan would import, not a copy -- same
discipline as `test_tweet_claims_unfixed_issue_detector.py` and
`test_notion_page_dangling_reference_detector.py`.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "notion-page-claims-unfixed-issue" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_notion_page_claims_unfixed_issue_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)


def _page(pid: str, text: str, last_edited_at: datetime, *, title: str = "Untitled page") -> "detector.NotionPage":
    return detector.NotionPage(
        id=pid, title=title, author="some-teammate", text=text,
        last_edited_at=last_edited_at,
        url=f"https://www.notion.so/orita-town/page-{pid}",
    )


def _issue(number: int, state: str = "open") -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state,
        url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestClaimedIssueNumbers:
    def test_fixes_hash_n(self):
        assert detector._claimed_issue_numbers("Fixes #1101.") == [1101]

    def test_closes_hash_n(self):
        assert detector._claimed_issue_numbers("Closes #1102 this time.") == [1102]

    def test_resolves_hash_n(self):
        assert detector._claimed_issue_numbers("Resolves #1103.") == [1103]

    def test_past_tense_fixed_hash_n(self):
        assert detector._claimed_issue_numbers("Fixed #1104.") == [1104]

    def test_case_insensitive(self):
        assert detector._claimed_issue_numbers("FIXES #1105.") == [1105]

    def test_present_participle_closing_never_matches(self):
        # Iron Rule #8's own prescribed safe form must never trip this
        # recipe's claim grammar either.
        assert detector._claimed_issue_numbers("Closing #1106 today, in prose only.") == []

    def test_bare_hash_n_with_no_claim_verb_is_never_extracted(self):
        assert detector._claimed_issue_numbers("See #1107 for background.") == []

    def test_multiple_claims_in_one_page(self):
        assert detector._claimed_issue_numbers("Fixes #1101. Closes #1102.") == [1101, 1102]

    def test_duplicate_claim_in_one_page_is_not_deduplicated_at_extraction(self):
        # De-duplication happens in compute_gaps, not here -- this function
        # is a pure extraction, faithfully reporting every match.
        assert detector._claimed_issue_numbers("Fixes #1101 and closes #1101 again.") == [1101, 1101]


class TestConfidenceFor:
    def test_a_page_touched_recently_scores_the_lower_bar(self):
        edited = _NOW - timedelta(hours=2)
        assert detector._confidence_for(edited, now=_NOW) == 0.55

    def test_a_page_untouched_for_a_full_day_scores_the_higher_bar(self):
        edited = _NOW - timedelta(hours=72)
        assert detector._confidence_for(edited, now=_NOW) == 0.85

    def test_exactly_the_grace_window_boundary_scores_the_higher_bar(self):
        edited = _NOW - timedelta(hours=24)
        assert detector._confidence_for(edited, now=_NOW) == 0.85

    def test_just_under_the_grace_window_scores_the_lower_bar(self):
        edited = _NOW - timedelta(hours=24) + timedelta(seconds=1)
        assert detector._confidence_for(edited, now=_NOW) == 0.55

    def test_grace_window_constant_is_twenty_four_hours(self):
        assert detector._EDIT_GRACE_WINDOW_HOURS == 24.0


class TestComputeGaps:
    def test_a_stale_unfixed_claim_is_surfaced_at_high_confidence(self):
        page = _page("p1", "Fixes #1101.", _NOW - timedelta(hours=50))
        issue = _issue(1101, state="open")

        surfaced, excluded = detector.compute_gaps([page], [issue], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "notion-page-claims-unfixed-issue-p1-1101"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_unfixed_claim_is_surfaced_at_low_confidence(self):
        page = _page("p2", "Resolves #1103.", _NOW - timedelta(hours=4))
        issue = _issue(1103, state="open")

        surfaced, excluded = detector.compute_gaps([page], [issue], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.55

    def test_a_closed_claimed_issue_is_excluded_not_surfaced(self):
        page = _page("p3", "Closes #1102.", _NOW - timedelta(hours=50))
        issue = _issue(1102, state="closed")

        surfaced, excluded = detector.compute_gaps([page], [issue], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-p3-1102" in excluded_slugs

    def test_a_claim_naming_an_issue_that_does_not_exist_is_excluded_not_surfaced(self):
        page = _page("p4", "Fix #1999 today.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([page], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-issue-not-found-p4-1999" in excluded_slugs

    def test_a_page_with_no_claim_phrase_produces_no_candidate_at_all(self):
        page = _page("p5", "Housekeeping only, see #1105 for background.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([page], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-p5"

    def test_a_duplicate_claim_in_one_page_produces_one_candidate_not_two(self):
        page = _page("p6", "Fixes #1101 and closes #1101 again.", _NOW - timedelta(hours=50))
        issue = _issue(1101, state="open")

        surfaced, excluded = detector.compute_gaps([page], [issue], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "notion-page-claims-unfixed-issue-p6-1101"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "notion-page-claims-unfixed-issue-NTN-C-9101-1101"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_fresh_claim_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "notion-page-claims-unfixed-issue-NTN-C-9102-1103" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_claim_and_the_dangling_and_no_claim_pages(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-NTN-C-9103-1102" in excluded_slugs
        assert "claimed-issue-not-found-NTN-C-9104-1999" in excluded_slugs
        assert "no-claim-phrase-NTN-C-9105" in excluded_slugs

    def test_the_shipped_fixture_returns_the_promised_output_shape(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert set(result.keys()) == {
            "generated_at", "source", "confidence_bar", "separation_margin",
            "primary_gap", "tail", "excluded",
        }
        assert result["source"] == "fixture"


class TestLoaders:
    """load_pages/load_issues -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_pages_parses_the_real_fixture(self):
        pages = detector.load_pages()
        assert len(pages) > 0
        assert all(isinstance(p, detector.NotionPage) for p in pages)

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_pages_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_pages(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_issues_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issues(bad_file)
