"""Tests for RECIPES/milestone-deadline-no-calendar-event/detector.py's own
detection logic (ROADMAP.md #666) -- the seventy-ninth real recipe: a
GitHub milestone has a due date, but no Google Calendar event was ever
created to track it.

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this test
exercises the exact module a live scan would import, not a copy.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
RECIPE_DIR = FENCEPOST_ROOT / "RECIPES" / "milestone-deadline-no-calendar-event"
DETECTOR_PATH = RECIPE_DIR / "detector.py"
MANIFEST_PATH = RECIPE_DIR / "recipe.json"

_spec = importlib.util.spec_from_file_location(
    "seam_engine._recipe_milestone_deadline_no_calendar_event_test", DETECTOR_PATH
)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc)


def _milestone(
    number: int,
    title: str,
    due_on: datetime | None,
    *,
    state: str = "open",
    open_issues: int = 0,
    closed_issues: int = 0,
) -> "detector.Milestone":
    return detector.Milestone(
        number=number, title=title, state=state, due_on=due_on,
        open_issues=open_issues, closed_issues=closed_issues,
        url=f"https://github.com/example/example-repo/milestone/{number}",
    )


def _event(
    event_id: str, title: str, start: datetime, *, organizer: str = "someone@example.com"
) -> "detector.CalendarEvent":
    return detector.CalendarEvent(
        id=event_id, title=title, start=start, organizer=organizer, source="calendar",
    )


class TestComputeGaps:
    def test_an_open_milestone_due_soon_with_no_matching_event_is_surfaced_at_high_confidence(self):
        m = _milestone(1, "v2.0 launch", datetime(2026, 8, 13, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([m], [], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-deadline-no-calendar-event-1"
        assert surfaced[0].confidence == 0.85
        assert surfaced[0].evidence == [m.url]

    def test_an_open_milestone_due_far_in_the_future_with_no_matching_event_is_surfaced_at_low_confidence(self):
        m = _milestone(2, "Q4 roadmap review", datetime(2026, 9, 20, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([m], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_milestone_recently_past_due_with_no_matching_event_is_urgent_too(self):
        # Urgency is symmetric around due_on -- a deadline that JUST passed
        # with nothing ever having tracked it is exactly as real a miss as
        # one about to hit.
        m = _milestone(6, "Recently missed", datetime(2026, 8, 9, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([m], [], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.85

    def test_a_milestone_with_a_keyword_and_window_matching_event_is_excluded_not_surfaced(self):
        m = _milestone(3, "Security audit", datetime(2026, 8, 10, tzinfo=timezone.utc))
        ev = _event("evt_1", "Security audit review", datetime(2026, 8, 9, 15, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([m], [ev], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "calendar-matched-3"
        assert excluded[0].confidence == 0.0
        assert excluded[0].evidence == [m.url, "calendar:evt_1"]

    def test_an_event_in_window_but_with_no_shared_keyword_does_not_match(self):
        # Proves the matcher needs BOTH signals, not just the date window --
        # a same-week event about something else entirely must not silence
        # a real gap.
        m = _milestone(1, "v2.0 launch", datetime(2026, 8, 13, tzinfo=timezone.utc))
        unrelated = _event("evt_2", "Team offsite planning", datetime(2026, 8, 12, 10, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([m], [unrelated], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-deadline-no-calendar-event-1"

    def test_an_event_with_a_shared_keyword_but_outside_the_window_does_not_match(self):
        # Proves the matcher needs BOTH signals the other direction -- a
        # same-topic event a month away must not silence a real gap either.
        m = _milestone(1, "v2.0 launch", datetime(2026, 8, 13, tzinfo=timezone.utc))
        far_event = _event("evt_3", "Product launch retro", datetime(2026, 10, 1, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([m], [far_event], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "milestone-deadline-no-calendar-event-1"

    def test_a_closed_milestone_past_its_due_date_is_excluded_not_surfaced(self):
        m = _milestone(4, "Beta freeze", datetime(2026, 7, 1, tzinfo=timezone.utc), state="closed")

        surfaced, excluded = detector.compute_gaps([m], [], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "not-open-4"

    def test_a_milestone_with_no_due_date_is_excluded_not_surfaced(self):
        m = _milestone(5, "Docs refresh", None)

        surfaced, excluded = detector.compute_gaps([m], [], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        assert excluded[0].slug == "no-due-date-5"

    def test_multiple_gaps_are_ranked_highest_confidence_first(self):
        soon = _milestone(1, "v2.0 launch", datetime(2026, 8, 13, tzinfo=timezone.utc))
        far = _milestone(2, "Q4 roadmap review", datetime(2026, 9, 20, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([far, soon], [], now=_NOW)

        assert excluded == []
        assert [g.slug for g in surfaced] == [
            "milestone-deadline-no-calendar-event-1",
            "milestone-deadline-no-calendar-event-2",
        ]

    def test_find_match_raises_on_a_milestone_with_no_due_date(self):
        m = _milestone(5, "Docs refresh", None)
        with pytest.raises(ValueError, match="due_on=None"):
            detector._find_match(m, [])


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "milestone-deadline-no-calendar-event-1"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_distant_milestone_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "milestone-deadline-no-calendar-event-2" in tail_slugs

    def test_the_shipped_fixture_excludes_matched_closed_and_no_due_date(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "calendar-matched-3" in excluded_slugs
        assert "not-open-4" in excluded_slugs
        assert "no-due-date-5" in excluded_slugs

    def test_the_shipped_fixture_output_carries_the_promised_top_level_keys(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert set(result.keys()) == {
            "generated_at", "source", "confidence_bar", "separation_margin",
            "primary_gap", "tail", "excluded",
        }
        assert result["source"] == "fixture"

    def test_run_recipe_scan_defaults_now_to_the_real_clock_when_omitted(self):
        result = detector.run_recipe_scan()
        assert result["generated_at"] is not None


class TestLoaders:
    """load_milestones/load_events -- mirrors every prior recipe's own
    _load_rows guard against syntactically valid but non-list JSON."""

    def test_load_milestones_parses_the_real_fixture(self):
        milestones = detector.load_milestones()
        assert len(milestones) == 5
        assert all(isinstance(m, detector.Milestone) for m in milestones)

    def test_load_milestones_leaves_due_on_none_when_absent_or_null(self):
        milestones = detector.load_milestones()
        by_number = {m.number: m for m in milestones}
        assert by_number[5].due_on is None

    def test_load_events_parses_the_real_fixture(self):
        events = detector.load_events()
        assert len(events) == 2
        assert all(isinstance(e, detector.CalendarEvent) for e in events)
        assert {e.id for e in events} == {"evt_1", "evt_2"}

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_milestones_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_milestones(bad_file)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_events_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_events(bad_file)


class TestManifestValidation:
    """Proves the shipped recipe.json actually clears the same oath and
    schema `seam_engine.recipes.discover_recipes()` holds every recipe to
    -- the same "prove it, don't just claim it" discipline every prior
    recipe's own test file holds itself to."""

    def test_manifest_loads_and_validates_cleanly(self):
        from seam_engine.recipes import load_recipe_manifest

        manifest = load_recipe_manifest(MANIFEST_PATH)
        assert manifest.slug == "milestone-deadline-no-calendar-event"
        assert manifest.toolkit == "github+google_calendar"
        assert manifest.scopes == ("ListMilestones", "ListEvents")

    def test_manifest_fixture_path_lives_under_fixtures(self):
        from seam_engine.recipes import load_recipe_manifest

        manifest = load_recipe_manifest(MANIFEST_PATH)
        assert manifest.fixture.startswith("fixtures/")
        assert manifest.fixture == "fixtures/milestone_deadline_no_calendar_event"

    def test_manifest_appears_in_discover_recipes(self):
        from seam_engine.recipes import discover_recipes

        slugs = {m.slug for m in discover_recipes(FENCEPOST_ROOT)}
        assert "milestone-deadline-no-calendar-event" in slugs

    def test_load_detector_finds_the_real_entrypoint(self):
        from seam_engine.recipes import load_detector, load_recipe_manifest

        manifest = load_recipe_manifest(MANIFEST_PATH)
        fn = load_detector(manifest)
        result = fn(now=_NOW)
        assert result["primary_gap"]["slug"] == "milestone-deadline-no-calendar-event-1"
