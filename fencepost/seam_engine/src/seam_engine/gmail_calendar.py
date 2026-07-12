"""Gmail-vs-Calendar seam-scan (v0.2): the invite still sitting in Gmail

that never made it onto the Calendar.

Read-only, like everything in Fencepost. This module only ever compares two
already-read lists: invite-shaped emails and calendar events. It writes
nothing back to Gmail or Calendar; the only write anywhere near it is the
local candidate-gap dict this module returns, same as `scan.py`.

**WIP, on purpose (ROADMAP.md #16).** the-hand gateway does not yet carry
read-only Gmail (`ListEmails`/`SearchThreads`) or Google Calendar
(`ListEvents`) scopes, and the town has no demo Gmail/Calendar account
connected — extending a live gateway's scopes is an act on the Mortal World
ground, and only the Hand may cross it (docs/architecture/reference.md, the
Road-Law: "The gods argue. The Hand decides. Arcade acts."). Off-By-One can
argue for the scopes; Off-By-One cannot grant them.

So this module runs entirely against a FIXTURE —
`fencepost/fixtures/gmail_calendar/{gmail.json,calendar.json}` — shaped
exactly like what those two read-only Arcade toolkits would return (see
SCOPES.md's v0.2 row). The moment the Hand runs `Arcade_ModifyGateway` to
add those scopes and connects a dedicated demo account, `load_gmail_fixture`
and `load_calendar_fixture` below are swapped for real `ListEmails`/
`ListEvents` calls. `compute_gaps` itself does not change one line — it is a
pure function of two already-typed lists, the same shape as
`compute_candidates` in `scan.py` is a pure function of GitHub events and X
posts. That is the whole point of keeping detection logic separate from
retrieval.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from seam_engine.scan import GapCandidate, _keywords

# fencepost/  (…/fencepost/seam_engine/src/seam_engine/gmail_calendar.py → parents[3])
_FENCEPOST_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GMAIL_FIXTURE = _FENCEPOST_ROOT / "fixtures" / "gmail_calendar" / "gmail.json"
DEFAULT_CALENDAR_FIXTURE = _FENCEPOST_ROOT / "fixtures" / "gmail_calendar" / "calendar.json"

# An invite and a calendar event count as "the same thing" if their starts
# land within this window of each other. Real invites and their calendar
# entries are not always minute-identical (a human nudges a meeting 15
# minutes without re-sending the invite), so an exact-timestamp match would
# under-count matches and over-count gaps — the opposite of Ogun's law.
TIME_TOLERANCE = timedelta(hours=2)


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class GmailInvite:
    id: str
    thread_id: str
    subject: str
    sender: str
    received_at: datetime
    has_ics: bool
    event_title: str | None
    event_start: datetime | None
    rsvp: str  # "none" | "accepted" | "declined" | "tentative"


@dataclass
class CalendarEvent:
    id: str
    title: str
    start: datetime
    organizer: str
    source: str


def load_gmail_fixture(path: Path | None = None) -> list[GmailInvite]:
    """Read-only: load invite-shaped emails from the fixture (or a real dump
    of the same shape, once ListEmails/SearchThreads is live)."""
    p = path or DEFAULT_GMAIL_FIXTURE
    rows = json.loads(Path(p).read_text())
    out: list[GmailInvite] = []
    for r in rows:
        out.append(GmailInvite(
            id=r["id"],
            thread_id=r.get("thread_id", r["id"]),
            subject=r["subject"],
            sender=r["sender"],
            received_at=_parse_ts(r["received_at"]),
            has_ics=bool(r.get("has_ics", False)),
            event_title=r.get("event_title"),
            event_start=_parse_ts(r["event_start"]) if r.get("event_start") else None,
            rsvp=r.get("rsvp", "none"),
        ))
    return out


def load_calendar_fixture(path: Path | None = None) -> list[CalendarEvent]:
    """Read-only: load calendar events from the fixture (or a real dump of
    the same shape, once ListEvents is live)."""
    p = path or DEFAULT_CALENDAR_FIXTURE
    rows = json.loads(Path(p).read_text())
    out: list[CalendarEvent] = []
    for r in rows:
        out.append(CalendarEvent(
            id=r["id"],
            title=r["title"],
            start=_parse_ts(r["start"]),
            organizer=r.get("organizer", "unknown"),
            source=r.get("source", "manual"),
        ))
    return out


def _is_invite(msg: GmailInvite) -> bool:
    """A message counts as a calendar invite only with real signal: an ICS
    attachment plus a parsed event title and start. A forwarded "maybe a
    time for X?" email with no ICS is a conversation, not an invite — flagging
    it would be exactly the false positive Ogun's law forbids."""
    return msg.has_ics and msg.event_title is not None and msg.event_start is not None


def _find_match(invite: GmailInvite, events: list[CalendarEvent]) -> CalendarEvent | None:
    """A calendar event matches an invite if their starts are within
    TIME_TOLERANCE AND their titles share a real keyword — either signal
    alone is too weak (two meetings an hour apart, or two same-named
    meetings on different days, are not necessarily the same thing)."""
    assert invite.event_start is not None and invite.event_title is not None
    invite_kw = _keywords(invite.event_title)
    for ev in events:
        if abs((ev.start - invite.event_start).total_seconds()) > TIME_TOLERANCE.total_seconds():
            continue
        if _keywords(ev.title) & invite_kw:
            return ev
    return None


def compute_gaps(
    invites: list[GmailInvite],
    events: list[CalendarEvent],
    *,
    now: datetime,
) -> tuple[list[GapCandidate], list[GapCandidate]]:
    """Return (surfaced gaps, excluded non-gaps).

    Mirrors `scan.compute_candidates`'s shape: surfaced is what clears the
    door into ranking; excluded is named, not hidden, so the ledger can show
    its work. Three things never become a gap, and each is excluded with its
    own reason:
      1. Not an invite at all (no ICS + parsed event) — never enters either
         list; a plain email is not the seam this detector watches.
      2. Declined — the human already acted on it; nothing fell through.
      3. Matched to a calendar event within tolerance — it DID reach the
         Calendar; there is no seam here.
    Everything left is an invite that reached Gmail and never reached
    Calendar — the exact v0.2 gap this module exists to name. Confidence
    rewards the strongest signal: a still-future event scores higher than a
    stale, already-past one, since a past invite is less likely to still be
    an actionable gap for the human reading the report today.
    """
    surfaced: list[GapCandidate] = []
    excluded: list[GapCandidate] = []

    for m in invites:
        if not _is_invite(m):
            continue

        if m.rsvp == "declined":
            excluded.append(GapCandidate(
                slug=f"gmail-declined-{m.id}",
                headline=f"'{m.event_title}' was declined — not a gap",
                detail=f"Invite {m.id} carries rsvp=declined; the human already acted on it.",
                confidence=0.0,
                evidence=[f"gmail:{m.id}"],
            ))
            continue

        match = _find_match(m, events)
        if match is not None:
            excluded.append(GapCandidate(
                slug=f"gmail-matched-{m.id}",
                headline=f"'{m.event_title}' already reached Calendar",
                detail=f"Invite {m.id} matches calendar event {match.id} within "
                       f"{TIME_TOLERANCE}. No seam here.",
                confidence=0.0,
                evidence=[f"gmail:{m.id}", f"calendar:{match.id}"],
            ))
            continue

        assert m.event_start is not None
        confidence = 0.6
        confidence += 0.2 if m.event_start >= now else 0.05
        if m.subject.lower().startswith("invitation:"):
            confidence += 0.1
        confidence = round(min(confidence, 0.95), 2)

        when = "still upcoming" if m.event_start >= now else "already passed"
        surfaced.append(GapCandidate(
            slug=f"gmail-vs-calendar-{m.id}",
            headline=f"Invite '{m.event_title}' sits in Gmail, never reached Calendar",
            detail=f"Received {m.received_at.isoformat()} from {m.sender}, event "
                   f"{m.event_start.isoformat()} ({when}). No calendar event within "
                   f"{TIME_TOLERANCE} shares a keyword with its title.",
            confidence=confidence,
            evidence=[f"gmail:{m.id}", f"thread:{m.thread_id}"],
        ))

    surfaced.sort(key=lambda g: g.confidence, reverse=True)
    return surfaced, excluded


def run_gmail_calendar_scan(
    gmail_path: Path | None = None,
    calendar_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The v0.2 scan entrypoint — same output shape as `scan.run_scan`, so it
    can feed the same ledger/report pipeline once it graduates off the
    fixture. `source: "fixture"` is the honest WIP marker; it flips to
    "live" only once real ListEmails/ListEvents calls replace the loaders.
    """
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    invites = load_gmail_fixture(gmail_path)
    events = load_calendar_fixture(calendar_path)
    surfaced, excluded = compute_gaps(invites, events, now=now)
    ranking = rank(surfaced)
    primary = ranking.primary

    return {
        "generated_at": now.isoformat(),
        "source": "fixture",
        "gmail_path": str(gmail_path or DEFAULT_GMAIL_FIXTURE),
        "calendar_path": str(calendar_path or DEFAULT_CALENDAR_FIXTURE),
        "confidence_bar": ranking.confidence_bar,
        "separation_margin": ranking.separation_margin,
        "primary_gap": asdict(primary) if primary else None,
        "tail": [asdict(g) for g in ranking.tail],
        "excluded": [asdict(g) for g in excluded],
    }


if __name__ == "__main__":
    import sys

    result = run_gmail_calendar_scan()
    out = sys.argv[1] if len(sys.argv) > 1 else None
    text = json.dumps(result, indent=2, default=str)
    if out:
        Path(out).write_text(text + "\n")
    else:
        print(text)
