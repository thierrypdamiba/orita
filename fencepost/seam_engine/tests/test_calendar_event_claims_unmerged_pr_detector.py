"""Tests for RECIPES/calendar-event-claims-unmerged-pr/detector.py's own
detection logic -- the hundred-third real recipe: a Google Calendar
event's own title/description invokes a real ships/includes/merges/via
PR claim, but the named PR never actually merged. The Calendar-side twin
of test_slack_message_claims_unmerged_pr_detector.py.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "calendar-event-claims-unmerged-pr" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_calendar_event_claims_unmerged_pr_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)


def _event(eid: str, title: str, description: str, start: datetime, organizer: str = "some-mortal@orita.gods") -> "detector.CalendarEvent":
    return detector.CalendarEvent(
        id=eid, title=title, description=description, organizer=organizer, start=start,
    )


def _pr(number: int, state: str = "open", merged: bool = False) -> "detector.PullRequest":
    return detector.PullRequest(
        number=number, title=f"PR {number}", state=state, merged=merged,
        url=f"https://github.com/example/example-repo/pull/{number}",
    )


class TestClaimedPrNumbers:
    def test_ships_hash_n(self):
        assert detector._claimed_pr_numbers("Ships #601.") == [601]

    def test_includes_hash_n(self):
        assert detector._claimed_pr_numbers("Includes #602 this time.") == [602]

    def test_merges_hash_n(self):
        assert detector._claimed_pr_numbers("Merges #603.") == [603]

    def test_via_hash_n(self):
        assert detector._claimed_pr_numbers("Landed via #604.") == [604]

    def test_case_insensitive(self):
        assert detector._claimed_pr_numbers("SHIPS #605.") == [605]

    def test_bare_hash_n_with_no_claim_verb_is_never_extracted(self):
        # This is a future calendar-side dangling-reference recipe's own
        # broader regex; a bare "see #N" mention in prose is not a
        # shipped-it claim.
        assert detector._claimed_pr_numbers("See #606 for background.") == []

    def test_multiple_claims_in_one_event(self):
        assert detector._claimed_pr_numbers("Ships #601. Merges #602.") == [601, 602]

    def test_duplicate_claim_in_one_event_is_not_deduplicated_at_extraction(self):
        # De-duplication happens in compute_gaps, not here -- this function
        # is a pure extraction, faithfully reporting every match.
        assert detector._claimed_pr_numbers("Ships #601 and via #601 again.") == [601, 601]

    def test_negated_claim_is_not_extracted(self):
        assert detector._claimed_pr_numbers("This does not ship #607, deferred.") == []


class TestComputeGaps:
    def test_a_stale_unmerged_claim_is_surfaced_at_high_confidence(self):
        event = _event("E-1", "sync", "Ships #601.", _NOW - timedelta(hours=50))
        pr = _pr(601, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([event], [pr], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "calendar-event-claims-unmerged-pr-E-1-601"
        assert surfaced[0].confidence == 0.85

    def test_a_fresh_unmerged_claim_is_surfaced_at_low_confidence(self):
        event = _event("E-2", "sync", "Merges #603.", _NOW - timedelta(hours=4))
        pr = _pr(603, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([event], [pr], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_merged_claimed_pr_is_excluded_not_surfaced(self):
        event = _event("E-3", "sync", "Includes #602.", _NOW - timedelta(hours=50))
        pr = _pr(602, state="closed", merged=True)

        surfaced, excluded = detector.compute_gaps([event], [pr], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claim-true-E-3-602" in excluded_slugs

    def test_a_closed_not_merged_claimed_pr_is_still_surfaced(self):
        # merged=False and state="closed" (closed-without-merging) is
        # still a real overclaim -- the claim was that it shipped, and a
        # closed-not-merged PR never did.
        event = _event("E-3b", "sync", "Includes #608.", _NOW - timedelta(hours=50))
        pr = _pr(608, state="closed", merged=False)

        surfaced, excluded = detector.compute_gaps([event], [pr], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "calendar-event-claims-unmerged-pr-E-3b-608"

    def test_a_claim_naming_a_pr_that_does_not_exist_is_excluded_not_surfaced(self):
        event = _event("E-4", "sync", "Ships #999 today.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([event], [], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-pr-not-found-E-4-999" in excluded_slugs

    def test_an_event_with_no_claim_phrase_produces_no_candidate_at_all(self):
        event = _event("E-5", "sync", "Housekeeping only, see #605 for background.", _NOW - timedelta(hours=50))

        surfaced, excluded = detector.compute_gaps([event], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-E-5"

    def test_a_claim_in_the_title_alone_is_extracted(self):
        event = _event("E-5b", "Ships #601 review", "", _NOW - timedelta(hours=50))
        pr = _pr(601, state="open", merged=False)

        surfaced, _excluded = detector.compute_gaps([event], [pr], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "calendar-event-claims-unmerged-pr-E-5b-601"

    def test_a_duplicate_claim_in_one_event_produces_one_candidate_not_two(self):
        event = _event("E-6", "sync", "Ships #601 and via #601 again.", _NOW - timedelta(hours=50))
        pr = _pr(601, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([event], [pr], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "calendar-event-claims-unmerged-pr-E-6-601"

    def test_confidence_boundary_exactly_24_hours_is_stale_not_fresh(self):
        event = _event("E-7", "sync", "Ships #601.", _NOW - timedelta(hours=24))
        pr = _pr(601, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([event], [pr], now=_NOW)

        assert surfaced[0].confidence == 0.85

    def test_confidence_boundary_just_under_24_hours_is_fresh(self):
        event = _event("E-8", "sync", "Ships #601.", _NOW - timedelta(hours=23, minutes=59))
        pr = _pr(601, state="open", merged=False)

        surfaced, excluded = detector.compute_gaps([event], [pr], now=_NOW)

        assert surfaced[0].confidence == 0.5

    def test_evidence_carries_both_the_event_marker_and_the_pr_url(self):
        event = _event("E-9", "sync", "Ships #601.", _NOW - timedelta(hours=50))
        pr = _pr(601, state="open", merged=False)

        surfaced, _excluded = detector.compute_gaps([event], [pr], now=_NOW)

        assert surfaced[0].evidence == ["calendar:E-9", pr.url]

    def test_excluded_not_found_evidence_carries_only_the_event_marker(self):
        event = _event("E-10", "sync", "Ships #999 today.", _NOW - timedelta(hours=50))

        _surfaced, excluded = detector.compute_gaps([event], [], now=_NOW)

        assert excluded[0].evidence == ["calendar:E-10"]

    def test_no_surfaced_or_excluded_candidates_for_an_empty_event_list(self):
        surfaced, excluded = detector.compute_gaps([], [_pr(601)], now=_NOW)
        assert surfaced == []
        assert excluded == []

    def test_surfaced_candidates_are_sorted_by_confidence_descending(self):
        stale = _event("E-11", "sync", "Ships #601.", _NOW - timedelta(hours=50))
        fresh = _event("E-12", "sync", "Ships #603.", _NOW - timedelta(hours=4))
        pulls = [_pr(601, state="open", merged=False), _pr(603, state="open", merged=False)]

        surfaced, _excluded = detector.compute_gaps([fresh, stale], pulls, now=_NOW)

        assert [g.confidence for g in surfaced] == [0.85, 0.5]

    def test_headline_and_detail_never_grade_or_blame_the_organizer(self):
        # CONTRIBUTING.md's "No grading, ever" law: the text may name the
        # gap, never the organizer's own error.
        event = _event("E-13", "sync", "Ships #601.", _NOW - timedelta(hours=50), organizer="some-mortal@orita.gods")
        pr = _pr(601, state="open", merged=False)

        surfaced, _excluded = detector.compute_gaps([event], [pr], now=_NOW)

        combined = (surfaced[0].headline + surfaced[0].detail).lower()
        for word in ("mistake", "wrong", "blame", "dropped the ball", "error", "fault"):
            assert word not in combined


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "calendar-event-claims-unmerged-pr-EVT-4201-601"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_fresh_claim_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "calendar-event-claims-unmerged-pr-EVT-4202-603" in tail_slugs

    def test_the_shipped_fixture_excludes_the_true_claim_and_the_not_found_and_no_claim_events(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claim-true-EVT-4203-602" in excluded_slugs
        assert "claimed-pr-not-found-EVT-4204-999" in excluded_slugs
        assert "no-claim-phrase-EVT-4205" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_601_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("calendar-event-claims-unmerged-pr-EVT-4201-601") == 1

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
    """load_events/load_pulls -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_events_parses_the_real_fixture(self):
        events = detector.load_events()
        assert len(events) > 0
        assert all(isinstance(e, detector.CalendarEvent) for e in events)

    def test_load_pulls_parses_the_real_fixture(self):
        pulls = detector.load_pulls()
        assert len(pulls) > 0
        assert all(isinstance(p, detector.PullRequest) for p in pulls)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_events_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_events(bad_file)

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

        manifest_path = FENCEPOST_ROOT / "RECIPES" / "calendar-event-claims-unmerged-pr" / "recipe.json"
        manifest = load_recipe_manifest(manifest_path)
        validated = validate_recipe(manifest)
        assert validated.slug == "calendar-event-claims-unmerged-pr"
        assert validated.toolkit == "google_calendar+github"
        assert set(validated.scopes) == {"ListEvents", "ListPullRequests"}
