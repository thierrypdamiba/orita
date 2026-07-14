"""The Oracle Desk's nineteenth real cadence: a checkable claim about the
town's own public GitHub Actions workflow count. (ROADMAP #60)

Tasks 38-40 proved a whole family of these: a single field read off a
public, unauthenticated GitHub REST API response, no Arcade tool, no new
scope, no per-user account behind any of it. This module reads the same
kind of field from a different endpoint — `GET
/repos/{owner}/{repo}/actions/workflows`'s `total_count` — the count of
automations the town runs on itself. Every prior cadence source pointed
outward (stars, forks, followers, reach) or at the town's own output
(commits, branches, labels); this one points at the machine room: how many
workflows fire without a human on the trigger, wired straight into the
`.github/workflows/` directory this very cadence module gets stitched into.

Sealed by `ogun` himself, not just graded by him — every one of the
eighteen sources before this one was staked by another god and only ever
checked by Ogun after the fact. His own law (false positives are the whole
ballgame) applies to a call of his own exactly as hard as to anyone
else's, so this module runs the identical discipline: `record_snapshot`
appends a `{"ts", "count"}` line to `oracle/workflow_snapshots.jsonl` every
cadence run (append-only, no prior line ever rewritten), and every claim
built here is run through `copylint.enforce_copy` before it is ever sealed.
"""
from __future__ import annotations

import datetime
import json
import os
from types import ModuleType

from oracle_engine import copylint, prediction

_ORACLE_ENGINE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
_ORACLE_ROOT = os.path.join(_ORACLE_ENGINE_ROOT, "..")
DEFAULT_SNAPSHOT_PATH = os.path.normpath(os.path.join(_ORACLE_ROOT, "workflow_snapshots.jsonl"))

DEFAULT_REPO = "thierrypdamiba/orita"
DEFAULT_HORIZON_HOURS = 336  # two weeks -- a new workflow file ships rarer than a tag
DEFAULT_CONFIDENCE = 0.5
DEFAULT_ACTOR = "ogun"


class WorkflowCadenceError(ValueError):
    """The workflow-cadence read or the prediction it produced is not
    well-formed."""


def _default_http_get(url: str) -> dict:
    import httpx

    resp = httpx.get(url, headers={"Accept": "application/vnd.github+json"}, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def fetch_workflow_count(repo: str = DEFAULT_REPO, http_get=None) -> int:
    """The repo's PUBLIC, unauthenticated GitHub Actions workflow count off
    the GitHub REST API's `total_count` field — read-only by nature, no
    account, no OAuth, no toolkit. A pluggable `http_get` (same
    dependency-injection shape `star_cadence.py` uses) keeps tests off the
    real network."""
    getter = http_get or _default_http_get
    payload = getter(f"https://api.github.com/repos/{repo}/actions/workflows")
    if "total_count" not in payload:
        raise WorkflowCadenceError(f"malformed GitHub API response: {payload!r}")
    return int(payload["total_count"])


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
    other cadence source's own discipline — no function in this module
    rewrites a prior line."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise WorkflowCadenceError("count must be a non-negative integer")
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


def workflow_count_at_or_before(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet — never guessed at, never
    interpolated."""
    best = None
    for s in snapshots:
        ts = _parse_ts(s["ts"])
        if ts <= when and (best is None or ts > _parse_ts(best["ts"])):
            best = s
    return best["count"] if best else None


def workflow_count_at_or_after(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. The grading-side counterpart to
    `workflow_count_at_or_before`: once a call's window closes, the honest
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
    GitHub Actions workflows, plus the confidence sealed alongside it.
    Pure: reads `snapshots`/`now`/`current_count`, writes nothing, decides
    nothing about whether to seal it."""
    if now.tzinfo is None:
        raise WorkflowCadenceError("now must be timezone-aware")
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise WorkflowCadenceError("current_count must be a non-negative integer")
    baseline_when = now - datetime.timedelta(hours=horizon_hours)
    baseline = workflow_count_at_or_before(snapshots, baseline_when)
    delta = None if baseline is None else current_count - baseline
    target = now + datetime.timedelta(hours=horizon_hours)
    threshold = current_count + 1
    change_clause = (
        f", net change over the past {horizon_hours}h: {delta:+d}"
        if delta is not None
        else ", no earlier snapshot yet to compare against"
    )
    claim = (
        f"By {target.strftime('%Y-%m-%dT%H:%M:%SZ')}, {DEFAULT_REPO}'s public GitHub Actions "
        f"workflow count will be at least {threshold} "
        f"(currently {current_count}{change_clause})."
    )
    return {"claim": claim, "confidence": float(confidence)}


def seal_workflow_prediction(
    now: datetime.datetime,
    ts: str,
    current_count: int,
    actor: str = DEFAULT_ACTOR,
    snapshots: list[dict] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs,
) -> dict:
    """Build one workflow-cadence prediction and seal it. `now` and `ts`
    are always passed in by the caller, same discipline every other
    cadence source in this desk holds to."""
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
    _count = fetch_workflow_count()
    record_snapshot(_count, _ts)
    _entry = seal_workflow_prediction(now=_now, ts=_ts, current_count=_count)
    print(_entry["hash"])
