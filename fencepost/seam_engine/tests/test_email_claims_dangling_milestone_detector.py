"""Tests for RECIPES/email-claims-dangling-milestone/detector.py's own
detection logic -- the hundred-first real recipe: an inbound email claims
a milestone number that doesn't exist at all. The email-sourced twin of
test_linear_comment_claims_dangling_milestone_detector.py, and the
dangling-milestone twin of test_email_claims_open_milestone_detector.py.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "email-claims-dangling-milestone" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_email_claims_dangling_milestone_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 21, 12, 0, 0, tzinfo=timezone.utc)


def _email(eid: str, body: str, received_at: datetime, sender: str = "some-mortal@orita.gods", subject: str = "status update") -> "detector.Email":
    return detector.Email(id=eid, sender=sender, subject=subject, body=body, received_at=received_at)


def _milestone(number: int, state: str = "open") -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


class TestClaimedMilestoneNumbersReuse:
    """This recipe reuses seam_engine.milestone_claims verbatim -- these
    tests prove the import actually happened, not a second retyped copy."""

    def test_milestone_hash_n(self):
        assert detector._claimed_milestone_numbers("milestone #4701 shipped.") == [4701]

    def test_bare_hash_n_with_no_milestone_word_is_never_extracted(self):
        assert detector._claimed_milestone_numbers("see #4702 for background.") == []


class TestComputeGaps:
    def test_a_claim_naming_a_milestone_that_does_not_exist_is_surfaced(self):
        email = _email("E-1", "milestone #4701 shipped.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([email], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "email-claims-dangling-milestone-E-1-4701"
        assert surfaced[0].confidence == 0.8

    def test_confidence_is_flat_regardless_of_email_age(self):
        fresh = _email("E-2", "milestone #4703 shipped.", _NOW - timedelta(minutes=5))
        stale = _email("E-3", "milestone #4704 shipped.", _NOW - timedelta(days=365))

        surfaced, _excluded = detector.compute_gaps([fresh, stale], [], now=_NOW)

        assert {g.confidence for g in surfaced} == {0.8}

    def test_a_claim_naming_a_real_open_milestone_is_excluded_not_surfaced(self):
        email = _email("E-4", "milestone #4705 shipped.", _NOW - timedelta(hours=1))
        milestone = _milestone(4705, state="open")

        surfaced, excluded = detector.compute_gaps([email], [milestone], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-exists-E-4-4705" in excluded_slugs

    def test_a_claim_naming_a_real_closed_milestone_is_also_excluded(self):
        email = _email("E-5", "milestone #4706 shipped.", _NOW - timedelta(hours=1))
        milestone = _milestone(4706, state="closed")

        surfaced, excluded = detector.compute_gaps([email], [milestone], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-exists-E-5-4706" in excluded_slugs

    def test_an_email_with_no_claim_phrase_produces_no_candidate_at_all(self):
        email = _email("E-6", "housekeeping only, see #4707 for background.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([email], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-E-6"

    def test_an_email_with_no_claim_relevant_text_at_all_produces_the_no_claim_exclusion(self):
        email = _email("E-7", "nothing new to report this week.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([email], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-E-7"

    def test_a_duplicate_claim_in_one_email_produces_one_candidate_not_two(self):
        email = _email("E-8", "milestone #4701 shipped and milestone #4701 confirmed again.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([email], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "email-claims-dangling-milestone-E-8-4701"

    def test_a_bare_hash_mention_alongside_a_real_claim_does_not_produce_a_second_candidate(self):
        email = _email("E-9", "milestone #4701 shipped. see #4999 for background.", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([email], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "email-claims-dangling-milestone-E-9-4701"

    def test_evidence_carries_only_the_gmail_tag_for_a_dangling_claim(self):
        email = _email("E-10", "milestone #4701 shipped.", _NOW - timedelta(hours=1))

        surfaced, _excluded = detector.compute_gaps([email], [], now=_NOW)

        assert surfaced[0].evidence == ["gmail:E-10"]

    def test_excluded_real_milestone_evidence_carries_both_the_gmail_tag_and_the_milestone_url(self):
        email = _email("E-11", "milestone #4705 shipped.", _NOW - timedelta(hours=1))
        milestone = _milestone(4705, state="open")

        _surfaced, excluded = detector.compute_gaps([email], [milestone], now=_NOW)

        assert excluded[0].evidence == ["gmail:E-11", milestone.url]

    def test_no_surfaced_or_excluded_candidates_for_an_empty_email_list(self):
        surfaced, excluded = detector.compute_gaps([], [_milestone(4701)], now=_NOW)
        assert surfaced == []
        assert excluded == []

    def test_headline_and_detail_never_grade_or_blame_the_sender(self):
        # CONTRIBUTING.md's "No grading, ever" law: the text may name the
        # gap, never the sender's own error.
        email = _email("E-12", "milestone #4701 shipped.", _NOW - timedelta(hours=1), sender="some-mortal@orita.gods")

        surfaced, _excluded = detector.compute_gaps([email], [], now=_NOW)

        combined = (surfaced[0].headline + surfaced[0].detail).lower()
        for word in ("mistake", "wrong", "blame", "dropped the ball", "error", "fault"):
            assert word not in combined


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "email-claims-dangling-milestone-EML-D-4601-4601"
        assert result["primary_gap"]["confidence"] == 0.8

    def test_the_shipped_fixture_produces_no_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["tail"] == []

    def test_the_shipped_fixture_excludes_the_real_claims_and_the_no_claim_emails(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claimed-milestone-exists-EML-D-4602-4602" in excluded_slugs
        assert "claimed-milestone-exists-EML-D-4603-4603" in excluded_slugs
        assert "no-claim-phrase-EML-D-4604" in excluded_slugs
        assert "no-claim-phrase-EML-D-4605" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_4601_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("email-claims-dangling-milestone-EML-D-4601-4601") == 1

    def test_source_is_honestly_marked_fixture(self):
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

        manifest_path = FENCEPOST_ROOT / "RECIPES" / "email-claims-dangling-milestone" / "recipe.json"
        manifest = load_recipe_manifest(manifest_path)
        validated = validate_recipe(manifest)
        assert validated.slug == "email-claims-dangling-milestone"
        assert validated.toolkit == "gmail+github"
        assert set(validated.scopes) == {"ListEmails", "ListMilestones"}
