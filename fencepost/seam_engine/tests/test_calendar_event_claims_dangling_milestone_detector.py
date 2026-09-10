"""Tests for RECIPES/calendar-event-claims-dangling-milestone/detector.py's
own detection logic -- the hundred-fourth real recipe: a Google Calendar
event's own title/description invokes a real 'milestone #N' claim
phrase, but no milestone with that number exists at all. The Calendar-side
twin of test_email_claims_dangling_milestone_detector.py.

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
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "calendar-event-claims-dangling-milestone" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_calendar_event_claims_dangling_milestone_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)


def _event(eid: str, title: str, description: str, start: datetime, organizer: str = "some-mortal@orita.gods") -> "detector.CalendarEvent":
    return detector.CalendarEvent(
        id=eid, title=title, description=description, organizer=organizer, start=start,
    )


def _milestone(number: int, state: str = "open") -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=f"Milestone {number}", state=state,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


class TestComputeGaps:
    def test_a_dangling_milestone_claim_is_surfaced_at_flat_confidence(self):
        event = _event("E-1", "sync", "milestone #4701 wrapped", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([event], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "calendar-event-claims-dangling-milestone-E-1-4701"
        assert surfaced[0].confidence == 0.8

    def test_confidence_is_not_age_gated(self):
        # Unlike the *-claims-unfixed-issue/*-claims-unmerged-pr siblings,
        # this family's confidence never depends on event age -- a fresh
        # event and a stale one naming the same dangling number both get
        # the identical flat 0.8.
        fresh = _event("E-fresh", "sync", "milestone #4701 wrapped", _NOW - timedelta(minutes=1))
        stale = _event("E-stale", "sync", "milestone #4701 wrapped", _NOW - timedelta(days=90))

        surfaced_fresh, _ = detector.compute_gaps([fresh], [], now=_NOW)
        surfaced_stale, _ = detector.compute_gaps([stale], [], now=_NOW)

        assert surfaced_fresh[0].confidence == surfaced_stale[0].confidence == 0.8

    def test_a_claim_naming_a_real_open_milestone_is_excluded_not_surfaced(self):
        event = _event("E-2", "sync", "milestone #4702 shipped", _NOW - timedelta(hours=1))
        milestone = _milestone(4702, state="open")

        surfaced, excluded = detector.compute_gaps([event], [milestone], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-exists-E-2-4702" in excluded_slugs

    def test_a_claim_naming_a_real_closed_milestone_is_excluded_not_surfaced(self):
        event = _event("E-3", "sync", "milestone #4703 wrapped", _NOW - timedelta(hours=1))
        milestone = _milestone(4703, state="closed")

        surfaced, excluded = detector.compute_gaps([event], [milestone], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "claimed-milestone-exists-E-3-4703" in excluded_slugs

    def test_an_event_with_no_claim_phrase_produces_no_candidate_at_all(self):
        event = _event("E-4", "sync", "see #4704 for background, nothing shipped", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([event], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-E-4"

    def test_a_claim_in_the_title_alone_is_extracted(self):
        event = _event("E-5", "milestone #4701 wrapped", "", _NOW - timedelta(hours=1))

        surfaced, _excluded = detector.compute_gaps([event], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "calendar-event-claims-dangling-milestone-E-5-4701"

    def test_a_duplicate_claim_in_one_event_produces_one_candidate_not_two(self):
        event = _event("E-6", "sync", "milestone #4701 wrapped, milestone #4701 confirmed", _NOW - timedelta(hours=1))

        surfaced, _excluded = detector.compute_gaps([event], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].slug == "calendar-event-claims-dangling-milestone-E-6-4701"

    def test_evidence_carries_only_the_event_marker(self):
        event = _event("E-7", "sync", "milestone #4701 wrapped", _NOW - timedelta(hours=1))

        surfaced, _excluded = detector.compute_gaps([event], [], now=_NOW)

        assert surfaced[0].evidence == ["calendar:E-7"]

    def test_excluded_exists_evidence_carries_the_event_marker_and_milestone_url(self):
        event = _event("E-8", "sync", "milestone #4702 shipped", _NOW - timedelta(hours=1))
        milestone = _milestone(4702, state="open")

        _surfaced, excluded = detector.compute_gaps([event], [milestone], now=_NOW)

        assert excluded[0].evidence == ["calendar:E-8", milestone.url]

    def test_no_surfaced_or_excluded_candidates_for_an_empty_event_list(self):
        surfaced, excluded = detector.compute_gaps([], [_milestone(4701)], now=_NOW)
        assert surfaced == []
        assert excluded == []

    def test_headline_and_detail_never_grade_or_blame_the_organizer(self):
        # CONTRIBUTING.md's "No grading, ever" law: the text may name the
        # gap, never the organizer's own error.
        event = _event("E-9", "sync", "milestone #4701 wrapped", _NOW - timedelta(hours=1), organizer="some-mortal@orita.gods")

        surfaced, _excluded = detector.compute_gaps([event], [], now=_NOW)

        combined = (surfaced[0].headline + surfaced[0].detail).lower()
        for word in ("mistake", "wrong", "blame", "dropped the ball", "error", "fault"):
            assert word not in combined

    def test_bare_hash_n_with_no_milestone_word_is_never_extracted_as_a_claim(self):
        event = _event("E-10", "sync", "see #4704 for background", _NOW - timedelta(hours=1))

        surfaced, excluded = detector.compute_gaps([event], [], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-claim-phrase-E-10"


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "calendar-event-claims-dangling-milestone-EVT-D-4701-4701"
        assert result["primary_gap"]["confidence"] == 0.8

    def test_the_shipped_fixture_excludes_the_real_milestones_and_no_claim_events(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "claimed-milestone-exists-EVT-D-4702-4702" in excluded_slugs
        assert "claimed-milestone-exists-EVT-D-4703-4703" in excluded_slugs
        assert "no-claim-phrase-EVT-D-4704" in excluded_slugs
        assert "no-claim-phrase-EVT-D-4705" in excluded_slugs

    def test_the_shipped_fixture_deduplicates_the_repeated_4701_claim(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = [result["primary_gap"]["slug"]] if result["primary_gap"] else []
        all_slugs += [g["slug"] for g in result["tail"]]
        assert all_slugs.count("calendar-event-claims-dangling-milestone-EVT-D-4701-4701") == 1

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
    """load_events/load_milestones -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_events_parses_the_real_fixture(self):
        events = detector.load_events()
        assert len(events) > 0
        assert all(isinstance(e, detector.CalendarEvent) for e in events)

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) > 0
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_events_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_events(bad_file)

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

        manifest_path = FENCEPOST_ROOT / "RECIPES" / "calendar-event-claims-dangling-milestone" / "recipe.json"
        manifest = load_recipe_manifest(manifest_path)
        validated = validate_recipe(manifest)
        assert validated.slug == "calendar-event-claims-dangling-milestone"
        assert validated.toolkit == "google_calendar+github"
        assert set(validated.scopes) == {"ListEvents", "ListMilestones"}
