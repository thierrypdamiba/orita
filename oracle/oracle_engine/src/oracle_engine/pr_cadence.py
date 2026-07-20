"""The Oracle Desk's eighteenth real cadence: a checkable claim about the
town's own public GitHub open pull-request count. (ROADMAP #54)

Task 40 reads the repo object's own `open_issues_count` field, but that
field is a documented GitHub API quirk: it counts issues AND pull requests
together, so it has never actually isolated a PR-only signal. Task 48
reads `/branches`, a cumulative count that only grows — a branch pushed
once and abandoned still counts forever. `GET
/repos/{owner}/{repo}/pulls?state=open` is a public, unauthenticated
GitHub REST endpoint the desk has not touched before (the repo object
confirmed dry at task 41; `X_WhoAmI`'s `public_metrics` payload fully read
after task 46; `/contributors` at task 47; `/branches` at task 48;
`/commits` at task 49; `/subscribers` at task 50; `/tags` at task 51;
`/labels` at task 52; `topics` at task 53). It counts something none of
the first seventeen cadences do — not a conflated total, not a cumulative
ever-count, but the CURRENT live number of proposals still awaiting a
decision right now, a number that can go up and back down again.

Structurally this mirrors `contributor_cadence.py`/`branch_cadence.py`
line for line on purpose — eighteen independent cadence sources sharing
one shape is the point, not a missed chance to unify them into one
module. A future nineteenth source should be able to copy this file's
shape again without reading any of the other seventeen first.
"""
from __future__ import annotations

import datetime
import json
import os
from types import ModuleType

from oracle_engine import copylint, prediction

_ORACLE_ENGINE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
_ORACLE_ROOT = os.path.join(_ORACLE_ENGINE_ROOT, "..")
DEFAULT_SNAPSHOT_PATH = os.path.normpath(os.path.join(_ORACLE_ROOT, "pr_snapshots.jsonl"))

DEFAULT_REPO = "thierrypdamiba/orita"
DEFAULT_HORIZON_HOURS = 336  # two weeks — same horizon every list-endpoint cadence holds
DEFAULT_CONFIDENCE = 0.5
DEFAULT_ACTOR = "nyx"
_MAX_PAGES = 20  # 20 * 100 = 2000 open PRs, far beyond any plausible count; a hard stop, not a guess


class PrCadenceError(ValueError):
    """The open-PR-cadence read or the prediction it produced is not
    well-formed."""


def _default_http_get(url: str) -> list:
    import httpx

    from oracle_engine.github_auth import github_headers

    resp = httpx.get(url, headers=github_headers(), timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def fetch_open_pr_count(repo: str = DEFAULT_REPO, http_get=None) -> int:
    """The repo's PUBLIC, unauthenticated open pull-request count off the
    GitHub REST API's pulls collection, filtered `state=open` — read-only
    by nature, no account, no OAuth, no toolkit. Like
    `contributor_cadence.fetch_contributor_count` and
    `branch_cadence.fetch_branch_count`, this endpoint returns a paginated
    LIST, not a single count field, so this function pages through it
    rather than trusting one response is everything. Same pluggable
    `http_get` shape every other cadence uses, kept off the real network
    in tests."""
    getter = http_get or _default_http_get
    total = 0
    for page in range(1, _MAX_PAGES + 1):
        payload = getter(
            f"https://api.github.com/repos/{repo}/pulls?state=open&per_page=100&page={page}"
        )
        if not isinstance(payload, list):
            raise PrCadenceError(f"malformed GitHub API response: {payload!r}")
        total += len(payload)
        if len(payload) < 100:
            return total
    raise PrCadenceError(f"open PR count exceeded the {_MAX_PAGES}-page safety cap")


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
        raise PrCadenceError("count must be a non-negative integer")
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


def pr_count_at_or_before(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet — never guessed at, never interpolated."""
    best = None
    for s in snapshots:
        ts = _parse_ts(s["ts"])
        if ts <= when and (best is None or ts > _parse_ts(best["ts"])):
            best = s
    return best["count"] if best else None


def pr_count_at_or_after(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. The grading-side counterpart to
    `pr_count_at_or_before`: once a call's window closes, the honest
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
    """One checkable claim about the town's own next window of open pull
    requests, plus the confidence sealed alongside it. Pure: reads
    `snapshots`/`now`/`current_count`, writes nothing, decides nothing
    about whether to seal it."""
    if now.tzinfo is None:
        raise PrCadenceError("now must be timezone-aware")
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise PrCadenceError("current_count must be a non-negative integer")
    if horizon_hours <= 0:
        raise PrCadenceError(
            "horizon_hours must be positive — a target at or before the sealing "
            "moment is not a prediction, it is hindsight"
        )
    baseline_when = now - datetime.timedelta(hours=horizon_hours)
    baseline = pr_count_at_or_before(snapshots, baseline_when)
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
        f"open pull-request count will be at least {threshold} "
        f"(currently {current_count}{change_clause})."
    )
    return {"claim": claim, "confidence": float(confidence)}


def seal_pr_prediction(
    now: datetime.datetime,
    ts: str,
    current_count: int,
    actor: str = DEFAULT_ACTOR,
    snapshots: list[dict] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs,
) -> dict:
    """Build one open-PR-cadence prediction and seal it. `now` and `ts`
    are always passed in by the caller, same discipline every other
    module on this desk holds everywhere else."""
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
    _count = fetch_open_pr_count()
    record_snapshot(_count, _ts)
    _entry = seal_pr_prediction(now=_now, ts=_ts, current_count=_count)
    print(_entry["hash"])
