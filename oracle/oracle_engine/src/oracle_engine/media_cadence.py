"""The Oracle Desk's ninth real cadence: a checkable claim about the
town's own public X (`@oritatown`) media count. (ROADMAP #45)

Tasks 42-44 each read a fresh field off the same already-cleared
`X_WhoAmI` payload without adding scope: followers (who is watching),
tweet count (the town's own output), listed count (whether a stranger
curated the town on purpose). That payload carries a fourth field this
desk has never sealed a claim about: `public_metrics.media_count` — how
many of the town's own tweets carried an image. `TOWN-OPERATIONS.md`'s
"card trick" (kiln an image, build a card page, tweet the card URL) is the
town's one documented path to a picture ever rendering on X at all; every
cadence before this one bet on text-shaped activity. This is the first
cadence to bet on whether the town ever shows anything, not just says
something. Same platform, same already-cleared `WhoAmI` allow-list entry,
zero new scope.

This module is `listed_cadence.py` with one field swapped, on purpose —
the same dependency-injection getter shape (no bare-HTTP default exists
for a profile's media count either, so `_default_whoami_get` raises loudly
the same way `follower_cadence`'s/`tweet_cadence`'s/`listed_cadence`'s do),
the same snapshot discipline, the same horizon and confidence defaults,
the same `copylint.enforce_copy` gate before every seal. Divergence only
where the signal itself diverges: the claim text names "public media
count," not "follower count," "tweet count," or "listed count."
"""
from __future__ import annotations

import datetime
import json
import os
from types import ModuleType

from oracle_engine import copylint, prediction

_ORACLE_ENGINE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
_ORACLE_ROOT = os.path.join(_ORACLE_ENGINE_ROOT, "..")
DEFAULT_SNAPSHOT_PATH = os.path.normpath(os.path.join(_ORACLE_ROOT, "media_snapshots.jsonl"))

DEFAULT_HANDLE = "@oritatown"
DEFAULT_HORIZON_HOURS = 168  # a week -- the card trick is rare by design, same cadence as listed
DEFAULT_CONFIDENCE = 0.55
DEFAULT_ACTOR = "kwaku-ananse"


class MediaCadenceError(ValueError):
    """The media-cadence read or the prediction it produced is not
    well-formed."""


def _default_whoami_get() -> dict:
    """No pluggable default exists for this getter the way
    `star_cadence._default_http_get` reaches a public, unauthenticated
    REST endpoint -- X exposes no such endpoint for a profile's media
    count either, same gap `follower_cadence.py`/`tweet_cadence.py`/
    `listed_cadence.py` document for their own fields. In every real run
    (live CI included) the caller supplies `x_whoami_get=` wired to
    the-hand's `X_WhoAmI` tool (already on `oracle/SCOPES.md`'s `WhoAmI`
    allow-list). This default exists only so an accidental unwired call
    fails loudly instead of silently guessing a count."""
    raise NotImplementedError(
        "media_cadence has no default X getter -- pass x_whoami_get= wired "
        "to the-hand's X_WhoAmI tool (oracle/SCOPES.md's WhoAmI allow-list)"
    )


def fetch_media_count(x_whoami_get=None) -> int:
    """`@oritatown`'s own `public_metrics.media_count`, off the-hand's
    `X_WhoAmI` read -- the town's own account, no per-user scope, nothing
    beyond what `oracle/SCOPES.md` already clears. A pluggable
    `x_whoami_get` (same dependency-injection shape every other cadence's
    getter uses) keeps tests off the real network/toolkit."""
    getter = x_whoami_get or _default_whoami_get
    payload = getter()
    metrics = payload.get("public_metrics") if isinstance(payload, dict) else None
    if not isinstance(metrics, dict) or "media_count" not in metrics:
        raise MediaCadenceError(f"malformed X WhoAmI response: {payload!r}")
    return int(metrics["media_count"])


def load_snapshots(path: str = DEFAULT_SNAPSHOT_PATH) -> list[dict]:
    """Every well-formed snapshot line, in file order. Read-only: never
    touches the file, takes its path and hands back plain dicts."""
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def record_snapshot(count: int, ts: str, path: str = DEFAULT_SNAPSHOT_PATH) -> dict:
    """Append one `{"ts", "count"}` snapshot. Append-only, mirrors every
    other cadence's own snapshot discipline -- no function in this module
    rewrites a prior line."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise MediaCadenceError("count must be a non-negative integer")
    entry = {"ts": ts, "count": int(count)}
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def _parse_ts(ts: str) -> datetime.datetime:
    dt = datetime.datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def media_count_at_or_before(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet -- never guessed at, never interpolated."""
    best = None
    for s in snapshots:
        ts = _parse_ts(s["ts"])
        if ts <= when and (best is None or ts > _parse_ts(best["ts"])):
            best = s
    return best["count"] if best else None


def media_count_at_or_after(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. The grading-side counterpart to
    `media_count_at_or_before`: once a call's window closes, the honest
    outcome is the first real observation once the window is actually
    over, not a later one that could quietly wait for a friendlier
    number."""
    best = None
    for s in snapshots:
        ts = _parse_ts(s["ts"])
        if ts >= when and (best is None or ts < _parse_ts(best["ts"])):
            best = s
    return best["count"] if best else None


def build_prediction(
    now: datetime.datetime,
    snapshots: list[dict],
    current_count: int,
    horizon_hours: int = DEFAULT_HORIZON_HOURS,
    confidence: float = DEFAULT_CONFIDENCE,
) -> dict:
    """One checkable claim about the town's own next window of public X
    media posted, plus the confidence sealed alongside it. Pure: reads
    `snapshots`/`now`/`current_count`, writes nothing, decides nothing
    about whether to seal it."""
    if now.tzinfo is None:
        raise MediaCadenceError("now must be timezone-aware")
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise MediaCadenceError("current_count must be a non-negative integer")
    baseline_when = now - datetime.timedelta(hours=horizon_hours)
    baseline = media_count_at_or_before(snapshots, baseline_when)
    delta = None if baseline is None else current_count - baseline
    target = now + datetime.timedelta(hours=horizon_hours)
    threshold = current_count + 1
    change_clause = (
        f", net change over the past {horizon_hours}h: {delta:+d}"
        if delta is not None
        else ", no earlier snapshot yet to compare against"
    )
    claim = (
        f"By {target.strftime('%Y-%m-%dT%H:%M:%SZ')}, {DEFAULT_HANDLE}'s public X "
        f"media count will be at least {threshold} "
        f"(currently {current_count}{change_clause})."
    )
    return {"claim": claim, "confidence": float(confidence)}


def seal_media_prediction(
    now: datetime.datetime,
    ts: str,
    current_count: int,
    actor: str = DEFAULT_ACTOR,
    snapshots: list[dict] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs,
) -> dict:
    """Build one media-cadence prediction and seal it. `now` and `ts` are
    always passed in by the caller, same discipline every other module on
    this desk holds everywhere else."""
    if snapshots is None:
        snapshots = load_snapshots()
    payload = build_prediction(now=now, snapshots=snapshots, current_count=current_count, **build_kwargs)
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
    _count = fetch_media_count()
    record_snapshot(_count, _ts)
    _entry = seal_media_prediction(now=_now, ts=_ts, current_count=_count)
    print(_entry["hash"])
