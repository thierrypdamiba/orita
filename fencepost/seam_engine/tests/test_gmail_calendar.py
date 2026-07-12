"""Tests for the Gmail-vs-Calendar detector (v0.2, WIP) — ROADMAP.md #16.

Runs entirely against the fixture in fencepost/fixtures/gmail_calendar/
(no live Arcade Gmail/Calendar session exists yet — see the module
docstring). Every rule `compute_gaps` claims has a test that goes red if the
rule breaks, same discipline as test_ranking.py.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from seam_engine.gmail_calendar import (
    DEFAULT_CALENDAR_FIXTURE,
    DEFAULT_GMAIL_FIXTURE,
    CalendarEvent,
    GmailInvite,
    compute_gaps,
    load_calendar_fixture,
    load_gmail_fixture,
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
