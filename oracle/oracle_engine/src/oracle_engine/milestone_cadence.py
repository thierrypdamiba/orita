"""The Oracle Desk's twentieth real cadence: a checkable claim about the
town's own public GitHub milestone count. (ROADMAP #67)

Tasks 47-54 opened and worked through a run of independent GitHub list
endpoints that each measured a trace left BY activity: contributors (a
commit attributed), branches (a crossing attempted), commits (the town's
own base rate), subscribers (ongoing attention), tags (a mark cut), labels
(the town's own taxonomy), topics (repo-object self-description), open
pull requests (a live, currently-open count). `GET
/repos/{owner}/{repo}/milestones` is a ninth such public, unauthenticated
endpoint the desk has not touched before. A milestone is neither a
reaction to the town nor a trace left by one — it is a date the town sets
for itself and tucks away, unremarked, until it matters. That is the
identical shape of thing this house already keeps in `docs/attic/`: a
milestone is a drawer, and nobody but the town itself decides to open it.

Structurally this mirrors `contributor_cadence.py`/`branch_cadence.py`
line for line on purpose — the same paginated-list shape applies here too,
since `/milestones` is also a paginated list rather than a single count
field. `state=all` is passed explicitly so a closed (met) milestone still
counts — closing a milestone is the town keeping its own promise, not
disappearing the drawer.

Every claim this module builds is run through `copylint.enforce_copy`
before it is ever sealed, same as every cadence before it.
"""
from __future__ import annotations

import datetime
import json
import os
from types import ModuleType

from oracle_engine import copylint, prediction

_ORACLE_ENGINE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
_ORACLE_ROOT = os.path.join(_ORACLE_ENGINE_ROOT, "..")
DEFAULT_SNAPSHOT_PATH = os.path.normpath(os.path.join(_ORACLE_ROOT, "milestone_snapshots.jsonl"))

DEFAULT_REPO = "thierrypdamiba/orita"
DEFAULT_HORIZON_HOURS = 336  # two weeks — same horizon as contributor_cadence.py
DEFAULT_CONFIDENCE = 0.5
DEFAULT_ACTOR = "zashiki-warashi"
_MAX_PAGES = 20  # 20 * 100 = 2000 milestones, far beyond any plausible count; a hard stop, not a guess


class MilestoneCadenceError(ValueError):
    """The milestone-cadence read or the prediction it produced is not
    well-formed."""


def _default_http_get(url: str) -> list:
    import httpx

    from oracle_engine.github_auth import github_headers

    resp = httpx.get(url, headers=github_headers(), timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def fetch_milestone_count(repo: str = DEFAULT_REPO, http_get=None) -> int:
    """The repo's PUBLIC, unauthenticated milestone count (open AND closed —
    `state=all`, so a met milestone still counts) off the GitHub REST API's
    milestones collection — read-only by nature, no account, no OAuth, no
    toolkit. Like `contributor_cadence.fetch_contributor_count`, this
    endpoint returns a paginated LIST, not a single count field, so this
    function pages through it rather than trusting one response is
    everything. Same pluggable `http_get` shape every other cadence uses,
    kept off the real network in tests."""
    getter = http_get or _default_http_get
    total = 0
    for page in range(1, _MAX_PAGES + 1):
        payload = getter(
            f"https://api.github.com/repos/{repo}/milestones?state=all&per_page=100&page={page}"
        )
        if not isinstance(payload, list):
            raise MilestoneCadenceError(f"malformed GitHub API response: {payload!r}")
        total += len(payload)
        if len(payload) < 100:
            return total
    raise MilestoneCadenceError(f"milestone count exceeded the {_MAX_PAGES}-page safety cap")


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
    prior cadence's `record_snapshot` and `BUILDLOG.md`'s own discipline —
    no function in this module rewrites a prior line."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise MilestoneCadenceError("count must be a non-negative integer")
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


def milestone_count_at_or_before(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet — never guessed at, never interpolated."""
    best = None
    for s in snapshots:
        ts = _parse_ts(s["ts"])
        if ts <= when and (best is None or ts > _parse_ts(best["ts"])):
            best = s
    return best["count"] if best else None


def milestone_count_at_or_after(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. The grading-side counterpart to
    `milestone_count_at_or_before`: once a call's window closes, the honest
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
    milestones, plus the confidence sealed alongside it. Pure: reads
    `snapshots`/`now`/`current_count`, writes nothing, decides nothing
    about whether to seal it."""
    if now.tzinfo is None:
        raise MilestoneCadenceError("now must be timezone-aware")
    now = now.astimezone(datetime.timezone.utc)
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise MilestoneCadenceError("current_count must be a non-negative integer")
    if horizon_hours <= 0:
        raise MilestoneCadenceError(
            "horizon_hours must be positive — a target at or before the sealing "
            "moment is not a prediction, it is hindsight"
        )
    baseline_when = now - datetime.timedelta(hours=horizon_hours)
    baseline = milestone_count_at_or_before(snapshots, baseline_when)
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
        f"milestone count (open and closed) will be at least {threshold} "
        f"(currently {current_count}{change_clause})."
    )
    return {"claim": claim, "confidence": float(confidence)}


def seal_milestone_prediction(
    now: datetime.datetime,
    ts: str,
    current_count: int,
    actor: str = DEFAULT_ACTOR,
    snapshots: list[dict] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs,
) -> dict:
    """Build one milestone-cadence prediction and seal it. `now` and `ts`
    are always passed in by the caller, same discipline every other module
    on this desk holds everywhere else."""
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
    _count = fetch_milestone_count()
    record_snapshot(_count, _ts)
    _entry = seal_milestone_prediction(now=_now, ts=_ts, current_count=_count)
    print(_entry["hash"])
