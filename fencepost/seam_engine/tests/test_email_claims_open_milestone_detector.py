"""Tests for RECIPES/email-claims-open-milestone/detector.py's own
detection logic -- the hundredth real recipe: an inbound email claims a
milestone shipped, but the named milestone never actually closed. The
milestone-claim twin of test_email_claims_unfixed_issue_detector.py, and
the Gmail-side twin of test_linear_comment_claims_open_milestone_detector.py.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "email-claims-open-milestone" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_email_claims_open_milestone_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc)


def _email(eid: str, body: str, received_at: datetime, sender: str = "some-mortal@orita.gods", subject: str = "status update") -> "detector.Email":
    return detector.Email(id=eid, sender=sender, subject=subject, body=body, received_at=received_at)


def _milestone(number: int, state: str = "open") -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


class TestClaimedMilestoneNumbers:
    def test_milestone_hash_n(self):
        assert detector._claimed_milestone_numbers("Milestone #4501 shipped.") == [4501]

    def test_case_insensitive(self):
        assert detector._claimed_milestone_numbers("MILESTONE #4502 done.") == [4502]

    def test_bare_hash_n_with_no_milestone_word_is_never_extracted(self):
        assert detector._claimed_milestone_numbers("See #4503 for background.") == []

    def test_multiple_claims_in_one_email(self):
        assert detector._claimed_milestone_numbers("Milestone #4501. Milestone #4502.") == [4501, 4502]

    def test_duplicate_claim_in_one_email_is_not_deduplicated_at_extraction(self):
        # De-duplication happens in compute_gaps, not here -- this function
        # is a pure extraction, faithfully reporting every match.
        assert detector._claimed_milestone_numbers("Milestone #4501 and milestone #4501 again.") == [4501, 4501]


class TestComputeGaps:
    def test_a_stale_open_claim_is_surfaced_at_high_confidence(self):
        email = _email("E-1", "Milestone #4501 shipped.", _NOW - timedelta(hours=50))
        milestone = _milestone(4501, state="open")

        surfaced, excluded = detector.compute_gaps([email], [milestone], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "email-claims-open-milestone-E-1-4501"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_open_claim_is_surfaced_at_low_confidence(self):
        email = _email("E-2", "Milestone #4503 done.", _NOW - timedelta(hours=4))
        milestone = _milestone(4503, state="open")

        surfaced, excluded = detector.compute_gaps([email], [milestone], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_closed_claimed_milestone_is_excluded_not_surfaced(self):
        email = _email("E-3", "Milestone #4502 wrapped up.", _NOW - timedelta(hours=50))
        milestone = _milestone(4502, state="closed")

        surfaced, excluded = detector.compute_gaps([email], [milestone], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-E-3-4502" in excluded_slugs

    def test_a_claim_naming_a_milestone_that_does_not_exist_is_excluded_not_surfaced(self):
        email = _email("E-4", "Milestone #4999 shipped today.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([email], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-not-found-E-4-4999" in excluded_slugs

    def test_an_email_with_no_claim_phrase_produces_no_candidate_at_all(self):
        email = _email("E-5", "Housekeeping only, see #4505 for background.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([email], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-E-5"

    def test_a_duplicate_claim_in_one_email_produces_one_candidate_not_two(self):
        email = _email("E-6", "Milestone #4501 shipped and milestone #4501 confirmed again.", _NOW - timedelta(hours=50))
        milestone = _milestone(4501, state="open")

        surfaced, excluded = detector.compute_gaps([email], [milestone], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "email-claims-open-milestone-E-6-4501"

    def test_confidence_boundary_exactly_24_hours_is_stale_not_fresh(self):
        email = _email("E-7", "Milestone #4501 shipped.", _NOW - timedelta(hours=24))
        milestone = _milestone(4501, state="open")

        surfaced, excluded = detector.compute_gaps([email], [milestone], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_confidence_boundary_just_under_24_hours_is_fresh(self):
        email = _email("E-8", "Milestone #4501 shipped.", _NOW - timedelta(hours=23, minutes=59))
        milestone = _milestone(4501, state="open")

        surfaced, excluded = detector.compute_gaps([email], [milestone], now=_NOW)

        assert surfaced[0].confidence == 0.5

    def test_evidence_carries_both_the_gmail_tag_and_the_milestone_url(self):
        email = _email("E-9", "Milestone #4501 shipped.", _NOW - timedelta(hours=50))
        milestone = _milestone(4501, state="open")

        surfaced, _excluded = detector.compute_gaps([email], [milestone], now=_NOW)

        assert surfaced[0].evidence == ["gmail:E-9", milestone.url]

    def test_excluded_not_found_evidence_carries_only_the_gmail_tag(self):
        email = _email("E-10", "Milestone #4999 shipped today.", _NOW - timedelta(hours=50))

        _surfaced, excluded = detector.compute_gaps([email], [], now=_NOW)

        assert excluded[0].evidence == ["gmail:E-10"]

    def test_no_surfaced_or_excluded_candidates_for_an_empty_email_list(self):
        surfaced, excluded = detector.compute_gaps([], [_milestone(4501)], now=_NOW)
        assert surfaced == []
        assert excluded == []

    def test_surfaced_candidates_are_sorted_by_confidence_descending(self):
        stale = _email("E-11", "Milestone #4501 shipped.", _NOW - timedelta(hours=50))
        fresh = _email("E-12", "Milestone #4503 shipped.", _NOW - timedelta(hours=4))
        milestones = [_milestone(4501, state="open"), _milestone(4503, state="open")]

        surfaced, _excluded = detector.compute_gaps([fresh, stale], milestones, now=_NOW)

        assert [g.confidence for g in surfaced] == [0.85, 0.5]

    def test_headline_and_detail_never_grade_or_blame_the_sender(self):
        # CONTRIBUTING.md's "No grading, ever" law: the text may name the
        # gap, never the sender's own error.
        email = _email("E-13", "Milestone #4501 shipped.", _NOW - timedelta(hours=50), sender="some-mortal@orita.gods")
        milestone = _milestone(4501, state="open")

        surfaced, _excluded = detector.compute_gaps([email], [milestone], now=_NOW)

        combined = (surfaced[0].headline + surfaced[0].detail).lower()
        for word in ("mistake", "wrong", "blame", "dropped the ball", "error", "fault"):
            assert word not in combined


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "email-claims-open-milestone-EML-4501-4501"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_fresh_claim_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "email-claims-open-milestone-EML-4502-4503" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_claim_and_the_not_found_and_no_claim_emails(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-EML-4503-4502" in excluded_slugs
        assert "claimed-milestone-not-found-EML-4504-4999" in excluded_slugs
        assert "no-claim-phrase-EML-4505" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_4501_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("email-claims-open-milestone-EML-4501-4501") == 1

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
    """load_emails/load_milestones -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_emails_parses_the_real_fixture(self):
        emails = detector.load_emails()
        assert len(emails) > 0
        assert all(isinstance(e, detector.Email) for e in emails)

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_emails_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_emails(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_milestones_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(bad_file)


class TestManifest:
    """The manifest itself: schema-valid, clears the oath, matches the
    fixture/detector this test file exercises."""

    def test_recipe_json_clears_validate_recipe(self):
        from seam_engine.recipes import load_recipe_manifest, validate_recipe

        manifest_path = FENCEPOST_ROOT / "RECIPES" / "email-claims-open-milestone" / "recipe.json"
        manifest = load_recipe_manifest(manifest_path)
        validated = validate_recipe(manifest)
        assert validated.slug == "email-claims-open-milestone"
        assert validated.toolkit == "gmail+github"
        assert set(validated.scopes) == {"ListEmails", "ListMilestones"}
