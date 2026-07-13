"""The Oracle Desk's fifth real cadence: a checkable claim about the
town's own public GitHub release count. (ROADMAP #41)

`star_cadence.py` (task 38), `fork_cadence.py` (task 39), and
`issue_cadence.py` (task 40) proved three cadence sources need no new
scope at all when the number is already public, all three drawing from
the same repo-object REST response. That response is now exhausted —
its remaining unused fields either duplicate an existing cadence
(`watchers_count` mirrors `stargazers_count` byte-for-byte on GitHub's
API) or aren't checkable growth claims (`language`, `size`). This module
reads a different public, unauthenticated endpoint instead:
`GET /repos/{owner}/{repo}/releases` — still no account, no OAuth, no
toolkit, just a second free public collection. It counts the town's own
weekly EPISODE releases (`chronicle/`, Cluster Day), which is
kwaku-ananse's own beat per STRATEGY.md's team table: the chronicler
sealing a checkable claim about their own cadence, not someone else's.

Structurally this mirrors `fork_cadence.py`/`issue_cadence.py` line for
line on purpose — five independent cadence sources sharing one shape is
the point, not a missed chance to unify them into one module. A future
sixth source should be able to copy this file's shape again without
reading any of the other four first.
"""
from __future__ import annotations

import datetime
import json
import os
from types import ModuleType

from oracle_engine import copylint, prediction

_ORACLE_ENGINE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
_ORACLE_ROOT = os.path.join(_ORACLE_ENGINE_ROOT, "..")
DEFAULT_SNAPSHOT_PATH = os.path.normpath(os.path.join(_ORACLE_ROOT, "release_snapshots.jsonl"))

DEFAULT_REPO = "thierrypdamiba/orita"
DEFAULT_HORIZON_HOURS = 336  # two weeks — spans at least one Cluster Day (Monday) with margin
DEFAULT_CONFIDENCE = 0.55
DEFAULT_ACTOR = "kwaku-ananse"
_MAX_PAGES = 20  # 20 * 100 = 2000 releases, far beyond any plausible count; a hard stop, not a guess


class ReleaseCadenceError(ValueError):
    """The release-cadence read or the prediction it produced is not
    well-formed."""


def _default_http_get(url: str) -> list:
    import httpx

    resp = httpx.get(url, headers={"Accept": "application/vnd.github+json"}, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def fetch_release_count(repo: str = DEFAULT_REPO, http_get=None) -> int:
    """The repo's PUBLIC, unauthenticated release count off the GitHub
    REST API's releases collection — read-only by nature, no account, no
    OAuth, no toolkit. Unlike `star_cadence`/`fork_cadence`/`issue_cadence`,
    this endpoint returns a paginated LIST, not a single count field, so
    this function pages through it rather than trusting one response is
    everything. Same pluggable `http_get` shape the other cadences use,
    kept off the real network in tests."""
    getter = http_get or _default_http_get
    total = 0
    for page in range(1, _MAX_PAGES + 1):
        payload = getter(f"https://api.github.com/repos/{repo}/releases?per_page=100&page={page}")
        if not isinstance(payload, list):
            raise ReleaseCadenceError(f"malformed GitHub API response: {payload!r}")
        total += len(payload)
        if len(payload) < 100:
            return total
    raise ReleaseCadenceError(f"release count exceeded the {_MAX_PAGES}-page safety cap")


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
    """Append one `{"ts", "count"}` snapshot. Append-only, mirrors
    `fork_cadence.record_snapshot`/`issue_cadence.record_snapshot` and
    `BUILDLOG.md`'s own discipline — no function in this module rewrites a
    prior line."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ReleaseCadenceError("count must be a non-negative integer")
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


def release_count_at_or_before(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet — never guessed at, never interpolated."""
    best = None
    for s in snapshots:
        ts = _parse_ts(s["ts"])
        if ts <= when and (best is None or ts > _parse_ts(best["ts"])):
            best = s
    return best["count"] if best else None


def release_count_at_or_after(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. The grading-side counterpart to
    `release_count_at_or_before`: once a call's window closes, the honest
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
    """One checkable claim about the town's own next window of public
    releases, plus the confidence sealed alongside it. Pure: reads
    `snapshots`/`now`/`current_count`, writes nothing, decides nothing
    about whether to seal it."""
    if now.tzinfo is None:
        raise ReleaseCadenceError("now must be timezone-aware")
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise ReleaseCadenceError("current_count must be a non-negative integer")
    baseline_when = now - datetime.timedelta(hours=horizon_hours)
    baseline = release_count_at_or_before(snapshots, baseline_when)
    delta = None if baseline is None else current_count - baseline
    target = now + datetime.timedelta(hours=horizon_hours)
    threshold = current_count + 1
    change_clause = (
        f", net change over the past {horizon_hours}h: {delta:+d}"
        if delta is not None
        else ", no earlier snapshot yet to compare against"
    )
    claim = (
        f"By {target.strftime('%Y-%m-%dT%H:%M:%SZ')}, {DEFAULT_REPO}'s public GitHub "
        f"release count will be at least {threshold} "
        f"(currently {current_count}{change_clause})."
    )
    return {"claim": claim, "confidence": float(confidence)}


def seal_release_prediction(
    now: datetime.datetime,
    ts: str,
    current_count: int,
    actor: str = DEFAULT_ACTOR,
    snapshots: list[dict] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs,
) -> dict:
    """Build one release-cadence prediction and seal it. `now` and `ts` are
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
    _count = fetch_release_count()
    record_snapshot(_count, _ts)
    _entry = seal_release_prediction(now=_now, ts=_ts, current_count=_count)
    print(_entry["hash"])
