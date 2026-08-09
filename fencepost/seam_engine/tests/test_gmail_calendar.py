"""Tests for the Gmail-vs-Calendar detector (v0.2, WIP) — ROADMAP.md #16.

Runs entirely against the fixture in fencepost/fixtures/gmail_calendar/
(no live Arcade Gmail/Calendar session exists yet — see the module
docstring). Every rule `compute_gaps` claims has a test that goes red if the
rule breaks, same discipline as test_ranking.py.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from seam_engine.gmail_calendar import (
    DEFAULT_CALENDAR_FIXTURE,
    DEFAULT_GMAIL_FIXTURE,
    CalendarEvent,
    GmailInvite,
    compute_gaps,
    load_calendar_fixture,
    load_calendar_from_live,
    load_gmail_fixture,
    load_gmail_from_live,
    run_gmail_calendar_scan,
)
from seam_engine.ranking import CONFIDENCE_BAR, Label, rank

# The fixture's "present": after msg-105 (2026-07-06) and msg-102's synced
# event (2026-07-11), before msg-101's design review (2026-07-16).
FIXTURE_NOW = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)


def _invite(
    id_: str = "m1",
    *,
    subject: str = "Invitation: Test meeting",
    has_ics: bool = True,
    event_title: str | None = "Test meeting",
    event_start: datetime | None = None,
    rsvp: str = "none",
    received_at: datetime | None = None,
) -> GmailInvite:
    return GmailInvite(
        id=id_,
        thread_id=f"thread-{id_}",
        subject=subject,
        sender="someone@orita.gods",
        received_at=received_at or FIXTURE_NOW - timedelta(days=1),
        has_ics=has_ics,
        event_title=event_title,
        event_start=event_start,
        rsvp=rsvp,
    )


def _event(id_: str = "e1", title: str = "Test meeting", start: datetime | None = None) -> CalendarEvent:
    return CalendarEvent(
        id=id_, title=title, start=start or FIXTURE_NOW, organizer="someone@orita.gods", source="manual",
    )


# --- the fixture itself --------------------------------------------------------


def test_fixture_files_exist_and_load():
    invites = load_gmail_fixture()
    events = load_calendar_fixture()
    assert DEFAULT_GMAIL_FIXTURE.exists()
    assert DEFAULT_CALENDAR_FIXTURE.exists()
    assert len(invites) == 6
    assert len(events) == 1


@pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
def test_load_gmail_fixture_raises_named_error_not_typeerror_when_json_is_not_a_list(
    tmp_path: Path, bad_value: object
) -> None:
    """task 359: the same non-list guard the RECIPES/*/detector.py campaign
    (task 358) closed, on the two loaders that scan didn't reach."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps(bad_value))
    with pytest.raises(ValueError, match="expected a JSON list"):
        load_gmail_fixture(bad_file)


@pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
def test_load_calendar_fixture_raises_named_error_not_typeerror_when_json_is_not_a_list(
    tmp_path: Path, bad_value: object
) -> None:
    """task 359: mirrors test_load_gmail_fixture_raises_named_error_not_typeerror_when_json_is_not_a_list."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps(bad_value))
    with pytest.raises(ValueError, match="expected a JSON list"):
        load_calendar_fixture(bad_file)


def test_fixture_produces_exactly_one_primary_gap():
    """DONE WHEN: a Gmail-vs-Calendar gap is detected in a (fixture) run."""
    result = run_gmail_calendar_scan(now=FIXTURE_NOW)
    assert result["primary_gap"] is not None
    assert result["primary_gap"]["slug"] == "gmail-vs-calendar-msg-101"
    assert result["primary_gap"]["confidence"] >= CONFIDENCE_BAR
    assert result["source"] == "fixture", "must stay honest that this is not a live read yet"


def test_fixture_matched_invite_is_excluded_not_surfaced():
    # msg-102 ("Weekly pantheon sync") matches evt-1 in calendar.json.
    result = run_gmail_calendar_scan(now=FIXTURE_NOW)
    surfaced_slugs = {result["primary_gap"]["slug"]} | {t["slug"] for t in result["tail"]}
    assert "gmail-vs-calendar-msg-102" not in surfaced_slugs
    excluded_slugs = {e["slug"] for e in result["excluded"]}
    assert "gmail-matched-msg-102" in excluded_slugs


def test_fixture_declined_invite_is_excluded_not_surfaced():
    result = run_gmail_calendar_scan(now=FIXTURE_NOW)
    surfaced_slugs = {result["primary_gap"]["slug"]} | {t["slug"] for t in result["tail"]}
    assert "gmail-vs-calendar-msg-103" not in surfaced_slugs
    excluded_slugs = {e["slug"] for e in result["excluded"]}
    assert "gmail-declined-msg-103" in excluded_slugs


def test_fixture_second_gap_is_a_real_contender_not_the_primary():
    # msg-105 ("Gauntlet kickoff") is also an unmatched, non-declined invite,
    # but it is stale (event already passed relative to FIXTURE_NOW), so it
    # scores lower and stays a contender, proving the ranker had a real
    # choice to make and still elected exactly one.
    result = run_gmail_calendar_scan(now=FIXTURE_NOW)
    tail_slugs = {t["slug"]: t for t in result["tail"]}
    assert "gmail-vs-calendar-msg-105" in tail_slugs
    assert tail_slugs["gmail-vs-calendar-msg-105"]["confidence"] < result["primary_gap"]["confidence"]


def test_fixture_non_invite_emails_never_enter_either_list():
    # msg-104 and msg-106 have no ICS — a forwarded "maybe a time?" note is
    # a conversation, not an invite. Flagging it would be crying wolf.
    result = run_gmail_calendar_scan(now=FIXTURE_NOW)
    all_slugs = (
        {result["primary_gap"]["slug"]}
        | {t["slug"] for t in result["tail"]}
        | {e["slug"] for e in result["excluded"]}
    )
    assert not any("msg-104" in s or "msg-106" in s for s in all_slugs)


# --- compute_gaps unit behavior -------------------------------------------------


def test_non_invite_without_ics_is_ignored():
    invites = [_invite(has_ics=False, event_title=None, event_start=None)]
    surfaced, excluded = compute_gaps(invites, [], now=FIXTURE_NOW)
    assert surfaced == []
    assert excluded == []


def test_declined_invite_is_excluded():
    invites = [_invite(rsvp="declined", event_start=FIXTURE_NOW + timedelta(days=1))]
    surfaced, excluded = compute_gaps(invites, [], now=FIXTURE_NOW)
    assert surfaced == []
    assert len(excluded) == 1
    assert excluded[0].confidence == 0.0


def test_matched_invite_within_tolerance_is_excluded_not_a_gap():
    start = FIXTURE_NOW + timedelta(days=2)
    invites = [_invite(event_title="Design review", event_start=start, subject="Invitation: Design review")]
    events = [_event(title="Design review sync", start=start + timedelta(minutes=30))]
    surfaced, excluded = compute_gaps(invites, events, now=FIXTURE_NOW)
    assert surfaced == []
    assert len(excluded) == 1
    assert "matched" in excluded[0].slug


def test_matching_title_but_outside_time_tolerance_is_still_a_gap():
    # Same title, but the calendar event is on a totally different day —
    # that is not "the same meeting," so it must NOT suppress the gap.
    start = FIXTURE_NOW + timedelta(days=2)
    invites = [_invite(event_title="Design review", event_start=start)]
    events = [_event(title="Design review", start=start + timedelta(days=10))]
    surfaced, excluded = compute_gaps(invites, events, now=FIXTURE_NOW)
    assert len(surfaced) == 1
    assert excluded == []


def test_matching_time_but_no_shared_keyword_is_still_a_gap():
    # Two unrelated meetings happening to land in the same window are not
    # "the same thing" either — title overlap is required, not just time.
    start = FIXTURE_NOW + timedelta(days=2)
    invites = [_invite(event_title="Design review", event_start=start)]
    events = [_event(title="Unrelated lunch", start=start)]
    surfaced, excluded = compute_gaps(invites, events, now=FIXTURE_NOW)
    assert len(surfaced) == 1
    assert excluded == []


def test_future_invite_scores_higher_than_a_stale_one():
    future = _invite("f1", event_title="Future thing", event_start=FIXTURE_NOW + timedelta(days=3))
    past = _invite("p1", event_title="Past thing", event_start=FIXTURE_NOW - timedelta(days=3))
    surfaced, _ = compute_gaps([future, past], [], now=FIXTURE_NOW)
    by_id = {g.slug: g for g in surfaced}
    assert by_id["gmail-vs-calendar-f1"].confidence > by_id["gmail-vs-calendar-p1"].confidence


def test_gap_confidence_never_exceeds_the_cap():
    invites = [_invite(
        subject="Invitation: Definitely a real thing",
        event_title="Definitely a real thing",
        event_start=FIXTURE_NOW + timedelta(days=1),
    )]
    surfaced, _ = compute_gaps(invites, [], now=FIXTURE_NOW)
    assert surfaced[0].confidence <= 0.95


def test_no_gap_when_every_invite_is_matched_or_declined():
    start = FIXTURE_NOW + timedelta(days=1)
    invites = [
        _invite("a", event_title="Synced thing", event_start=start),
        _invite("b", event_title="Declined thing", event_start=start, rsvp="declined"),
    ]
    events = [_event(title="Synced thing", start=start)]
    surfaced, excluded = compute_gaps(invites, events, now=FIXTURE_NOW)
    assert surfaced == []
    assert len(excluded) == 2


# --- feeds the shared ranker, same as scan.py's candidates ---------------------


def test_surfaced_gaps_feed_the_shared_ranking_law():
    invites = [
        _invite("hi", event_title="Big milestone thing", event_start=FIXTURE_NOW + timedelta(days=1),
                subject="Invitation: Big milestone thing"),
        _invite("lo", event_title="Quiet other thing", event_start=FIXTURE_NOW - timedelta(days=10)),
    ]
    surfaced, _ = compute_gaps(invites, [], now=FIXTURE_NOW)
    r = rank(surfaced)
    assert r.primary is not None
    assert r.primary.slug == "gmail-vs-calendar-hi"
    assert r.tail and r.tail[0].label == Label.CONTENDER.value


# --- live-override loaders, ROADMAP.md #132 -------------------------------------


def test_load_gmail_from_live_parses_a_normalized_entry():
    invites = load_gmail_from_live([{
        "id": "live-1",
        "subject": "Invitation: Real thing",
        "sender": "someone@example.com",
        "received_at": "2026-07-18T10:00:00Z",
        "has_ics": True,
        "event_title": "Real thing",
        "event_start": "2026-07-19T10:00:00Z",
        "rsvp": "none",
    }])
    assert len(invites) == 1
    inv = invites[0]
    assert inv.id == "live-1"
    assert inv.thread_id == "live-1"  # defaults to id, same as the fixture loader
    assert inv.event_title == "Real thing"
    assert inv.event_start == datetime(2026, 7, 19, 10, 0, tzinfo=timezone.utc)


def test_load_gmail_from_live_applies_the_same_optional_defaults_as_the_fixture_loader():
    invites = load_gmail_from_live([{
        "id": "live-2",
        "subject": "Just a note",
        "sender": "someone@example.com",
        "received_at": "2026-07-18T10:00:00Z",
    }])
    inv = invites[0]
    assert inv.has_ics is False
    assert inv.event_title is None
    assert inv.event_start is None
    assert inv.rsvp == "none"


def test_load_gmail_from_live_rejects_entry_missing_one_required_key():
    with pytest.raises(ValueError, match=r"entry 0.*sender"):
        load_gmail_from_live([{"id": "x", "subject": "s", "received_at": "2026-07-18T10:00:00Z"}])


def test_load_gmail_from_live_rejects_entry_missing_multiple_required_keys():
    with pytest.raises(ValueError, match=r"\['sender', 'received_at'\]"):
        load_gmail_from_live([{"id": "x", "subject": "s"}])


def test_load_gmail_from_live_accepts_an_empty_list():
    # Unlike load_x_posts_from_live/load_github_events_from_live, an empty
    # inbox read has no known non-zero base rate to reason "probably failed"
    # from — a real inbox can honestly hold zero qualifying messages.
    assert load_gmail_from_live([]) == []


def test_load_calendar_from_live_parses_a_normalized_entry():
    events = load_calendar_from_live([{
        "id": "evt-live-1",
        "title": "Real thing",
        "start": "2026-07-19T10:00:00Z",
        "organizer": "someone@example.com",
    }])
    assert len(events) == 1
    ev = events[0]
    assert ev.id == "evt-live-1"
    assert ev.start == datetime(2026, 7, 19, 10, 0, tzinfo=timezone.utc)
    assert ev.organizer == "someone@example.com"
    assert ev.source == "live"  # distinguishes it from the fixture loader's "manual" default


def test_load_calendar_from_live_applies_defaults():
    events = load_calendar_from_live([{"id": "e", "title": "t", "start": "2026-07-19T10:00:00Z"}])
    assert events[0].organizer == "unknown"
    assert events[0].source == "live"


def test_load_calendar_from_live_rejects_entry_missing_one_required_key():
    with pytest.raises(ValueError, match=r"entry 0.*start"):
        load_calendar_from_live([{"id": "x", "title": "t"}])


def test_load_calendar_from_live_rejects_entry_missing_multiple_required_keys():
    with pytest.raises(ValueError, match=r"\['title', 'start'\]"):
        load_calendar_from_live([{"id": "x"}])


def test_load_calendar_from_live_accepts_an_empty_list():
    assert load_calendar_from_live([]) == []


# --- run_gmail_calendar_scan override wiring, ROADMAP.md #132 -------------------


def _live_gmail_row(id_="live-hi", event_start="2026-07-19T10:00:00Z"):
    return {
        "id": id_,
        "subject": "Invitation: Big milestone thing",
        "sender": "someone@example.com",
        "received_at": "2026-07-17T10:00:00Z",
        "has_ics": True,
        "event_title": "Big milestone thing",
        "event_start": event_start,
        "rsvp": "none",
    }


def test_run_scan_default_stays_on_the_fixture_for_both_sides():
    result = run_gmail_calendar_scan(now=FIXTURE_NOW)
    assert result["gmail_source"] == "fixture"
    assert result["calendar_source"] == "fixture"
    assert result["source"] == "fixture"


def test_run_scan_gmail_override_never_touches_the_gmail_fixture_and_calendar_stays_fixture():
    result = run_gmail_calendar_scan(now=FIXTURE_NOW, gmail_events=[_live_gmail_row()])
    assert result["gmail_source"] == "override"
    assert result["calendar_source"] == "fixture"
    assert result["source"] == "override"
    # msg-101..106 from the fixture never appear when gmail_events overrides it
    all_slugs = (
        {result["primary_gap"]["slug"]} if result["primary_gap"] else set()
    ) | {t["slug"] for t in result["tail"]} | {e["slug"] for e in result["excluded"]}
    assert not any("msg-" in s for s in all_slugs)


def test_run_scan_calendar_override_never_touches_the_calendar_fixture_and_gmail_stays_fixture():
    result = run_gmail_calendar_scan(now=FIXTURE_NOW, calendar_events=[])
    assert result["gmail_source"] == "fixture"
    assert result["calendar_source"] == "override"
    assert result["source"] == "override"


def test_run_scan_both_overridden_reports_override_on_both_sides():
    result = run_gmail_calendar_scan(
        now=FIXTURE_NOW, gmail_events=[_live_gmail_row()], calendar_events=[],
    )
    assert result["gmail_source"] == "override"
    assert result["calendar_source"] == "override"
    assert result["source"] == "override"


def test_run_scan_override_path_still_finds_the_same_class_of_primary_gap():
    result = run_gmail_calendar_scan(
        now=FIXTURE_NOW,
        gmail_events=[_live_gmail_row(event_start="2026-07-19T10:00:00Z")],
        calendar_events=[],
    )
    assert result["primary_gap"] is not None
    assert result["primary_gap"]["slug"] == "gmail-vs-calendar-live-hi"
    assert result["primary_gap"]["confidence"] >= CONFIDENCE_BAR


# --- read-only doctrine, same shape as test_gateway.py --------------------------


FORBIDDEN_SUBSTRINGS = (
    "SendEmail",
    "CreateDraft",
    "Trash",
    "CreateEvent",
    "UpdateEvent",
    "DeleteEvent",
    "InsertEvent",
)


def test_module_never_names_a_write_capable_tool():
    from seam_engine import gmail_calendar as mod
    text = Path(mod.__file__).read_text(encoding="utf-8")
    for bad in FORBIDDEN_SUBSTRINGS:
        assert bad not in text, f"{bad} appears in gmail_calendar.py — a write-capable tool name in a read-only module"


def test_module_marks_itself_as_fixture_backed_wip():
    from seam_engine import gmail_calendar as mod
    text = mod.__doc__ or ""
    assert "WIP" in text
    assert "fixture" in text.lower()


# --- shared-helper identity, same shape as _keywords ------------------------


def test_parse_ts_is_the_same_object_as_scans():
    """gmail_calendar._parse_ts used to be a byte-identical private copy of
    scan.py's own _parse_ts (both `datetime.fromisoformat(s.replace("Z",
    "+00:00"))`). Consolidated onto scan.py's definition the same way this
    module already imports scan._keywords rather than redefining it --
    identity (`is`), not source equality, so a future edit to one is
    structurally an edit to both."""
    from seam_engine import gmail_calendar, scan
    assert gmail_calendar._parse_ts is scan._parse_ts


# --- internal invariant guards (task 618: assert -> raise, ruff S101) ----------


def test_find_match_raises_named_error_when_invariant_is_violated():
    """`_find_match` is only ever reached (via `compute_gaps`) after
    `_is_invite` has already confirmed event_start/event_title are set --
    the caller invariant used to be spelled `assert`, which `python -O`
    strips from the running program, silently deleting the guard rather
    than the caller of a broken invariant hitting the same clear error a
    test does now. Called directly (module-private, same access pattern
    `test_parse_ts_is_the_same_object_as_scans` already uses) to exercise
    the violated-invariant path `compute_gaps`'s own control flow can never
    reach for real."""
    from seam_engine import gmail_calendar as mod
    invite = _invite(event_title=None, event_start=None)
    with pytest.raises(ValueError, match="_find_match"):
        mod._find_match(invite, [_event()])


def test_compute_gaps_raises_named_error_when_invariant_is_violated(monkeypatch):
    """Same invariant, the second call site (`compute_gaps`'s own surfaced-
    gap branch) -- unreachable at runtime given `_find_match`'s own guard
    fires first on the identical condition, kept only as a mypy narrowing
    (see the comment at its call site). Monkeypatches BOTH `_is_invite`
    (the entry guard) and `_find_match` (the guard that would otherwise
    raise first) to prove this second raise is correctly worded and really
    is reachable code, not that it is reachable in real use -- it never is,
    by construction, which is exactly why two independent patches are
    needed to reach it at all."""
    from seam_engine import gmail_calendar as mod
    monkeypatch.setattr(mod, "_is_invite", lambda _msg: True)
    monkeypatch.setattr(mod, "_find_match", lambda _msg, _events: None)
    invite = _invite(event_title=None, event_start=None)
    with pytest.raises(ValueError, match="compute_gaps"):
        mod.compute_gaps([invite], [], now=FIXTURE_NOW)
