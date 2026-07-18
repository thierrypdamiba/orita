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

ROADMAP.md #132: `scan.py` grew a live-data override door twice
(`load_x_posts_from_live`, task 94; `load_github_events_from_live`, task
128) for the identical reason — this sandbox's own proxy wall can block a
direct call while an already-authorized MCP channel answers the same
question. This module never got the matching door, so `load_gmail_from_live`
and `load_calendar_from_live` below close it, and `run_gmail_calendar_scan`
takes optional `gmail_events`/`calendar_events` overrides the same way
`run_scan` takes `x_posts`/`github_events`. This does **not** graduate the
detector off the fixture — task 122 already confirmed zero Gmail/Calendar
tools are reachable through the-hand today, so the override path has
nothing live to call yet. It only means the fixture stops being the only
door the moment one opens. Unlike `load_x_posts_from_live`/
`load_github_events_from_live`, the new loaders do NOT refuse an empty
list: that refusal was reasoned from a known non-zero base rate (the
account has posted before; this repo commits most days) that has no
equivalent here — a real inbox or calendar can honestly hold zero matching
items in a given scan window.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from seam_engine.scan import GapCandidate, _keywords

if TYPE_CHECKING:
    from seam_engine.consent import ConsentRecord

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


_REQUIRED_LIVE_INVITE_KEYS = ("id", "subject", "sender", "received_at")


def load_gmail_from_live(data: list[dict[str, Any]]) -> list[GmailInvite]:
    """Parse a caller-normalized live Gmail read into the same `GmailInvite`
    shape `load_gmail_fixture` already produces (ROADMAP.md #132).

    The caller (whoever holds an already-authorized read channel, once one
    exists) normalizes each message to the same fields `load_gmail_fixture`
    parses before handing it in, mirroring `load_x_posts_from_live`'s
    "pre-fetched live data, already shaped" convention. `id`/`subject`/
    `sender`/`received_at` are required on every entry, same as the fixture
    rows; `thread_id`/`has_ics`/`event_title`/`event_start`/`rsvp` stay
    optional with the identical defaults `load_gmail_fixture` already uses.

    A malformed entry (missing one of the four required keys) raises
    `ValueError` naming the missing key and the entry's index — never
    silently dropped, per Ogun's precision-over-recall law. An EMPTY list is
    accepted, not refused: unlike `load_x_posts_from_live`/
    `load_github_events_from_live`, there is no known non-zero base rate to
    reason an empty read as "probably failed" from — a real inbox can
    honestly hold zero qualifying messages in a given scan window.
    """
    out: list[GmailInvite] = []
    for i, entry in enumerate(data):
        missing = [k for k in _REQUIRED_LIVE_INVITE_KEYS if k not in entry]
        if missing:
            raise ValueError(
                f"load_gmail_from_live(): entry {i} is missing required key(s) "
                f"{missing} (expected id/subject/sender/received_at on every "
                f"normalized message): {entry!r}"
            )
        out.append(GmailInvite(
            id=str(entry["id"]),
            thread_id=str(entry.get("thread_id", entry["id"])),
            subject=str(entry["subject"]),
            sender=str(entry["sender"]),
            received_at=_parse_ts(entry["received_at"]) if isinstance(entry["received_at"], str) else entry["received_at"],
            has_ics=bool(entry.get("has_ics", False)),
            event_title=entry.get("event_title"),
            event_start=(
                _parse_ts(entry["event_start"]) if isinstance(entry.get("event_start"), str)
                else entry.get("event_start")
            ),
            rsvp=entry.get("rsvp", "none"),
        ))
    return out


_REQUIRED_LIVE_CALENDAR_KEYS = ("id", "title", "start")


def load_calendar_from_live(data: list[dict[str, Any]]) -> list[CalendarEvent]:
    """Parse a caller-normalized live Calendar read into the same
    `CalendarEvent` shape `load_calendar_fixture` already produces
    (ROADMAP.md #132). Same discipline as `load_gmail_from_live`: required
    keys missing on an entry raise `ValueError` naming the key and index; an
    empty list is accepted, not refused, for the identical reason (a real
    calendar can honestly hold zero events in a given scan window).
    `organizer` defaults to `"unknown"`, same as the fixture loader;
    `source` defaults to `"live"` (not the fixture loader's `"manual"`) so a
    caller can always tell which door an event came through.
    """
    out: list[CalendarEvent] = []
    for i, entry in enumerate(data):
        missing = [k for k in _REQUIRED_LIVE_CALENDAR_KEYS if k not in entry]
        if missing:
            raise ValueError(
                f"load_calendar_from_live(): entry {i} is missing required key(s) "
                f"{missing} (expected id/title/start on every normalized event): {entry!r}"
            )
        out.append(CalendarEvent(
            id=str(entry["id"]),
            title=str(entry["title"]),
            start=_parse_ts(entry["start"]) if isinstance(entry["start"], str) else entry["start"],
            organizer=str(entry.get("organizer", "unknown")),
            source=str(entry.get("source", "live")),
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
    gmail_events: list[dict[str, Any]] | None = None,
    calendar_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """The v0.2 scan entrypoint — same output shape as `scan.run_scan`, so it
    can feed the same ledger/report pipeline once it graduates off the
    fixture.

    `gmail_events`/`calendar_events` (ROADMAP.md #132) mirror `run_scan`'s
    `x_posts`/`github_events`: `None` (the default) keeps reading the
    fixture, completely unchanged; a supplied list routes through
    `load_gmail_from_live`/`load_calendar_from_live` instead, with no
    change to `gmail_path`/`calendar_path` handling on that side. Each side
    gets its own `gmail_source`/`calendar_source` ("fixture" or "override").
    The legacy `source` key stays backward-compatible: `"fixture"` only
    when BOTH sides are still on the fixture, `"override"` the moment
    either side is not — so it flips to "live" (a caller-supplied "live"
    source string) only once real ListEmails/ListEvents calls actually feed
    an override in, and existing callers reading a bare `source` still get
    an honest fixture/not-fixture signal.
    """
    from seam_engine.ranking import rank

    now = now or datetime.now(timezone.utc)
    invites = load_gmail_fixture(gmail_path) if gmail_events is None else load_gmail_from_live(gmail_events)
    events = load_calendar_fixture(calendar_path) if calendar_events is None else load_calendar_from_live(calendar_events)
    surfaced, excluded = compute_gaps(invites, events, now=now)
    ranking = rank(surfaced)
    primary = ranking.primary

    gmail_source = "fixture" if gmail_events is None else "override"
    calendar_source = "fixture" if calendar_events is None else "override"

    return {
        "generated_at": now.isoformat(),
        "source": "fixture" if gmail_source == "fixture" and calendar_source == "fixture" else "override",
        "gmail_source": gmail_source,
        "calendar_source": calendar_source,
        "gmail_path": str(gmail_path or DEFAULT_GMAIL_FIXTURE),
        "calendar_path": str(calendar_path or DEFAULT_CALENDAR_FIXTURE),
        "confidence_bar": ranking.confidence_bar,
        "separation_margin": ranking.separation_margin,
        "primary_gap": asdict(primary) if primary else None,
        "tail": [asdict(g) for g in ranking.tail],
        "excluded": [asdict(g) for g in excluded],
    }


def run_consented_gmail_calendar_scan(
    consent: dict[str, ConsentRecord | None],
    gmail_path: Path | None = None,
    calendar_path: Path | None = None,
    *,
    now: datetime | None = None,
    gmail_events: list[dict[str, Any]] | None = None,
    calendar_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """The gated door onto a REAL human's own Gmail + Calendar (ROADMAP #20).

    `run_gmail_calendar_scan` above reads a fixture — nobody's account, so it
    needs nobody's consent, and stays exactly as it was for task 16's
    fixture-driven dogfood. This function is the one meant to wrap a live
    read, the moment `gmail_path`/`calendar_path` (or their loaders) point at
    a real connected human's inbox instead of a fixture file: it calls
    `consent.enforce_consent_for_toolkits` for BOTH "gmail" and
    "google_calendar" **before** `run_gmail_calendar_scan` — and therefore
    before either loader — is ever invoked. Either toolkit's consent missing
    or mismatched raises `ConsentRequiredError` immediately; the read never
    starts. `run_gmail_calendar_scan` is only called after both locks turn.

    `consent` maps toolkit name -> that toolkit's `ConsentRecord` (or `None`
    if the human never confirmed it) — see `seam_engine.consent`.
    """
    from seam_engine.consent import enforce_consent_for_toolkits

    enforce_consent_for_toolkits(consent, toolkits=("gmail", "google_calendar"))
    return run_gmail_calendar_scan(
        gmail_path, calendar_path, now=now,
        gmail_events=gmail_events, calendar_events=calendar_events,
    )


if __name__ == "__main__":
    import sys

    result = run_gmail_calendar_scan()
    out = sys.argv[1] if len(sys.argv) > 1 else None
    text = json.dumps(result, indent=2, default=str)
    if out:
        Path(out).write_text(text + "\n")
    else:
        print(text)
