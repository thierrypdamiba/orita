"""The Oracle Desk's seventh real cadence: a checkable claim about the
town's own public X (`@oritatown`) tweet count. (ROADMAP #43)

Tasks 38-42 read six fields off two platforms — five off GitHub's public
REST object (stars, forks, open issues, releases counted two ways) and
one off X's `X_WhoAmI` (followers, task 42). `X_WhoAmI`'s own
`public_metrics` payload carries a second field this desk has never
sealed a claim about: `tweet_count`. Where `followers_count` (task 42)
measures who is watching the town, `tweet_count` measures the town's own
output — how often @oritatown actually speaks. That is a genuinely
different claim: STRATEGY.md's Growth notes make X posting explicit
CHANGE-GATED (no hourly spam; the owner god posts only when an hour
produced something materially new to say), so this cadence is a checkable
bet on the town's own restraint holding, not on anyone else's adoption of
it. Same platform as task 42, same `WhoAmI` allow-list entry, zero new
scope.

This module is `follower_cadence.py` with one field swapped, on purpose —
the same dependency-injection getter shape (no bare-HTTP default exists
for a profile's tweet count either, so `_default_whoami_get` raises
loudly the same way `follower_cadence`'s does), the same snapshot
discipline, the same horizon and confidence defaults, the same
`copylint.enforce_copy` gate before every seal. Divergence only where the
signal itself diverges: the claim text names "public tweet count," not
"follower count."
"""
from __future__ import annotations

import datetime
import json
import os
from types import ModuleType

from oracle_engine import copylint, prediction

_ORACLE_ENGINE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
_ORACLE_ROOT = os.path.join(_ORACLE_ENGINE_ROOT, "..")
DEFAULT_SNAPSHOT_PATH = os.path.normpath(os.path.join(_ORACLE_ROOT, "tweet_snapshots.jsonl"))

DEFAULT_HANDLE = "@oritatown"
DEFAULT_HORIZON_HOURS = 168  # a week — posting is change-gated, not daily, same cadence as followers
DEFAULT_CONFIDENCE = 0.55
DEFAULT_ACTOR = "kwaku-ananse"


class TweetCadenceError(ValueError):
    """The tweet-cadence read or the prediction it produced is not
    well-formed."""


def _default_whoami_get() -> dict:
    """No pluggable default exists for this getter the way
    `star_cadence._default_http_get` reaches a public, unauthenticated
    REST endpoint — X exposes no such endpoint for a profile's tweet
    count, authenticated or not, same gap `follower_cadence.py` documents
    for follower count. In every real run (live CI included) the caller
    supplies `x_whoami_get=` wired to the-hand's `X_WhoAmI` tool (already
    on `oracle/SCOPES.md`'s `WhoAmI` allow-list). This default exists only
    so an accidental unwired call fails loudly instead of silently
    guessing a count."""
    raise NotImplementedError(
        "tweet_cadence has no default X getter — pass x_whoami_get= wired "
        "to the-hand's X_WhoAmI tool (oracle/SCOPES.md's WhoAmI allow-list)"
    )


def fetch_tweet_count(x_whoami_get=None) -> int:
    """`@oritatown`'s own `public_metrics.tweet_count`, off the-hand's
    `X_WhoAmI` read — the town's own account, no per-user scope, nothing
    beyond what `oracle/SCOPES.md` already clears. A pluggable
    `x_whoami_get` (same dependency-injection shape every other cadence's
    getter uses) keeps tests off the real network/toolkit."""
    getter = x_whoami_get or _default_whoami_get
    payload = getter()
    metrics = payload.get("public_metrics") if isinstance(payload, dict) else None
    if not isinstance(metrics, dict) or "tweet_count" not in metrics:
        raise TweetCadenceError(f"malformed X WhoAmI response: {payload!r}")
    return int(metrics["tweet_count"])


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
    other cadence's own snapshot discipline — no function in this module
    rewrites a prior line."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise TweetCadenceError("count must be a non-negative integer")
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


def tweet_count_at_or_before(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet — never guessed at, never interpolated."""
    best = None
    for s in snapshots:
        ts = _parse_ts(s["ts"])
        if ts <= when and (best is None or ts > _parse_ts(best["ts"])):
            best = s
    return best["count"] if best else None


def tweet_count_at_or_after(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. The grading-side counterpart to
    `tweet_count_at_or_before`: once a call's window closes, the honest
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
    tweets, plus the confidence sealed alongside it. Pure: reads
    `snapshots`/`now`/`current_count`, writes nothing, decides nothing
    about whether to seal it."""
    if now.tzinfo is None:
        raise TweetCadenceError("now must be timezone-aware")
    now = now.astimezone(datetime.timezone.utc)
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise TweetCadenceError("current_count must be a non-negative integer")
    if horizon_hours <= 0:
        raise TweetCadenceError(
            "horizon_hours must be positive — a target at or before the sealing "
            "moment is not a prediction, it is hindsight"
        )
    baseline_when = now - datetime.timedelta(hours=horizon_hours)
    baseline = tweet_count_at_or_before(snapshots, baseline_when)
    delta = None if baseline is None else current_count - baseline
    target = now + datetime.timedelta(hours=horizon_hours)
    threshold = current_count + 1
    change_clause = (
        f", net change over the past {horizon_hours}h: {delta:+d}"
        if delta is not None
        else ", no earlier snapshot yet to compare against"
    )
    claim = (
        f"By {target.strftime('%Y-%m-%dT%H:%M:%SZ')}, {DEFAULT_HANDLE}'s public tweet "
        f"count will be at least {threshold} "
        f"(currently {current_count}{change_clause})."
    )
    return {"claim": claim, "confidence": float(confidence)}


def seal_tweet_prediction(
    now: datetime.datetime,
    ts: str,
    current_count: int,
    actor: str = DEFAULT_ACTOR,
    snapshots: list[dict] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs,
) -> dict:
    """Build one tweet-cadence prediction and seal it. `now` and `ts` are
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
    _count = fetch_tweet_count()
    record_snapshot(_count, _ts)
    _entry = seal_tweet_prediction(now=_now, ts=_ts, current_count=_count)
    print(_entry["hash"])
