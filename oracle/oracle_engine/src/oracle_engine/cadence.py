"""The Oracle Desk's first real cadence. (ROADMAP #36)

`oracle/INTENT.md` (task 35) states the Desk's first live cadence reads no
per-user account — only the town's own, already-live data. `docs/oracle-desk.md`
promises the Desk does not need Tavily to start: it needs one thing sealed
before the outcome exists to grade against. This module is that one thing,
sourced the way Fencepost's first dogfood run was sourced: off data
the-hand already reads, nothing new connected, nothing borrowed from a
mortal.

The claim is self-referential on purpose. The town already keeps an
honest, append-only record of its own shipping cadence — `BUILDLOG.md`,
one line per shipped task. `recent_task_velocity` reads that record the
same way `seam_engine.streak` reads the Gap Ledger: a pure function of
what is already sealed, no new state to keep honest. `build_prediction`
turns one velocity reading into one forecast about the town's own next
window, checkable the same way Fencepost's gaps are checkable — against a
public, timestamped, append-only record nobody (including the town) can
quietly edit after the fact.

Every claim this module builds is run through `copylint.enforce_copy`
before it is ever sealed — the non-advice-shaped bar applies to a claim
about the town's own velocity exactly as it applies to a claim about
anything else; Ogun's law does not carve out an exception for predicting
ourselves.

Live Tavily search — the second public primitive `docs/oracle-desk.md`
names — is not wired here. `oracle/SCOPES.md` records that as an explicit
PENDING step, the same discipline Fencepost's tasks 16 and 17 held their
own pending live steps to, rather than blocking this module on a
connection that does not exist yet.
"""
from __future__ import annotations

import datetime
import os
import re
from types import ModuleType

from oracle_engine import copylint, prediction

_ORACLE_ENGINE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
_ORACLE_ROOT = os.path.join(_ORACLE_ENGINE_ROOT, "..")
_ORITA_ROOT = os.path.join(_ORACLE_ROOT, "..")
DEFAULT_BUILDLOG_PATH = os.path.normpath(os.path.join(_ORITA_ROOT, "BUILDLOG.md"))

DEFAULT_THRESHOLD = 3
DEFAULT_HORIZON_HOURS = 24
DEFAULT_CONFIDENCE = 0.7

_LOG_LINE_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2}) (?P<time>\d{2}:\d[\dx]) UTC \| (?P<god>[^|]+) \| (?P<task>[^|]+) \| "
)


class CadenceError(ValueError):
    """The cadence read or the prediction it produced is not well-formed."""


def parse_buildlog(text: str) -> list[dict]:
    """Every well-formed `BUILDLOG.md` line, parsed. Read-only: never
    touches the file, takes its text and hands back plain dicts."""
    entries = []
    for line in text.splitlines():
        m = _LOG_LINE_RE.match(line)
        if m:
            entries.append(m.groupdict())
    return entries


def _minute_floor(time_str: str) -> str:
    """Normalize a BUILDLOG.md `HH:MM` field into something `strptime` can
    parse.

    The town's own convention -- visible throughout the real
    `BUILDLOG.md` (e.g. "19:2x UTC", "03:0x UTC") -- obscures a line's
    exact minute by replacing its ones digit with a literal 'x'; the real
    minute is only known to within a ten-minute window. `%H:%M` cannot
    parse 'x' as a digit, so this floors the ambiguous digit to '0' -- the
    earliest minute consistent with what was actually recorded, never a
    guessed-at specific one. The resulting imprecision is at most nine
    minutes, negligible against every window this module is ever called
    with (hours, not minutes), and it is a documented approximation, not
    the silent drop this function replaces."""
    return time_str.replace("x", "0")


def load_buildlog_entries(path: str = DEFAULT_BUILDLOG_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return parse_buildlog(f.read())


def recent_task_velocity(
    entries: list[dict],
    now: datetime.datetime,
    window_hours: int | float = DEFAULT_HORIZON_HOURS,
) -> int:
    """How many DISTINCT numbered ROADMAP tasks got a BUILDLOG line inside
    the `window_hours` immediately before `now`. Distinct because a task can
    log more than one line (a shipped-line, an x-post-line); the velocity
    this predicts against is tasks moving, not lines written."""
    if now.tzinfo is None:
        raise CadenceError("now must be timezone-aware")
    cutoff = now - datetime.timedelta(hours=window_hours)
    seen: set[str] = set()
    for e in entries:
        task = e["task"].strip()
        if not task.isdigit():
            continue
        ts = datetime.datetime.strptime(
            f"{e['date']} {_minute_floor(e['time'])}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=datetime.timezone.utc)
        if cutoff <= ts <= now:
            seen.add(task)
    return len(seen)


def build_prediction(
    now: datetime.datetime,
    entries: list[dict],
    threshold: int = DEFAULT_THRESHOLD,
    horizon_hours: int = DEFAULT_HORIZON_HOURS,
    confidence: float = DEFAULT_CONFIDENCE,
) -> dict:
    """One self-referential, checkable claim about the town's own next
    window, plus the confidence sealed alongside it. Pure: reads `entries`
    and `now`, writes nothing, decides nothing about whether to seal it."""
    if now.tzinfo is None:
        raise CadenceError("now must be timezone-aware")
    if threshold < 1:
        raise CadenceError("threshold must be at least 1 — a call that always passes is not a call")
    if horizon_hours <= 0:
        raise CadenceError(
            "horizon_hours must be positive — a target at or before the sealing "
            "moment is not a prediction, it is hindsight"
        )
    velocity = recent_task_velocity(entries, now, window_hours=horizon_hours)
    target = now + datetime.timedelta(hours=horizon_hours)
    claim = (
        f"By {target.strftime('%Y-%m-%dT%H:%M:%SZ')}, BUILDLOG.md will record at least "
        f"{threshold} distinct numbered ROADMAP task(s) newly shipped between now and then "
        f"(the {horizon_hours}h window just past logged {velocity})."
    )
    return {"claim": claim, "confidence": float(confidence)}


def seal_cadence_prediction(
    now: datetime.datetime,
    ts: str,
    actor: str = "off-by-one",
    entries: list[dict] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs,
) -> dict:
    """Build one cadence prediction and seal it. `now` and `ts` are always
    passed in by the caller — a cadence read, like every other sealed act
    in this town, is timestamped at the moment it's taken, never defaulted
    silently (`oracle_engine.prediction.seal_prediction` holds the same
    line for `ts`)."""
    if entries is None:
        entries = load_buildlog_entries()
    payload = build_prediction(now=now, entries=entries, **build_kwargs)
    copylint.enforce_copy(payload["claim"], payload["confidence"])
    return prediction.seal_prediction(
        actor=actor,
        claim=payload["claim"],
        confidence=payload["confidence"],
        ts=ts,
        ledger_module=ledger_module,
    )


if __name__ == "__main__":
    _now = datetime.datetime.now(datetime.timezone.utc)
    _ts = _now.isoformat(timespec="seconds")
    _entry = seal_cadence_prediction(now=_now, ts=_ts)
    print(_entry["hash"])
