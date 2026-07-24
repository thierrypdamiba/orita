"""The Oracle Desk's twenty-second real cadence: a checkable claim about the
town's own public GitHub Actions RUN count. (ROADMAP #75)

Task 60 read `GET /repos/{owner}/{repo}/actions/workflows`'s `total_count`
-- how many automations the town has DEFINED. That number moves only when
a new `.yml` file lands (rare -- four workflow files exist as of this
cadence's own birth). `GET /repos/{owner}/{repo}/actions/runs` reads a
sibling field off a sibling endpoint: `total_count` there is how many
times those definitions have actually FIRED -- every scheduled tick, every
push-triggered run, every manual dispatch, across every workflow at once.
Same public, unauthenticated GitHub REST API family task 38 already
cleared (no new Arcade tool, no new scope, no per-user account); a
genuinely different claim than task 60's, the same way task 43's tweet
count was a different claim than task 42's follower count even though
both rode the same `X_WhoAmI` read. Definitions describe the machine
room's floor plan; runs describe whether the machines are actually
running.
"""
from __future__ import annotations

import datetime
import json
import os
from types import ModuleType

from oracle_engine import copylint, prediction

_ORACLE_ENGINE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
_ORACLE_ROOT = os.path.join(_ORACLE_ENGINE_ROOT, "..")
DEFAULT_SNAPSHOT_PATH = os.path.normpath(os.path.join(_ORACLE_ROOT, "run_snapshots.jsonl"))

DEFAULT_REPO = "thierrypdamiba/orita"
DEFAULT_HORIZON_HOURS = 24  # runs fire far more often than workflow definitions ship
DEFAULT_CONFIDENCE = 0.5
DEFAULT_ACTOR = "zashiki-warashi"


class RunCadenceError(ValueError):
    """The run-cadence read or the prediction it produced is not
    well-formed."""


class RunCadenceTamperedError(RuntimeError):
    """Raised by run_count_at_or_before/run_count_at_or_after when the
    snapshot log holds a malformed line anywhere in it. Mirrors
    branch_cadence.py's/collaborator_cadence.py's/comment_cadence.py's
    /commit_cadence.py's/commit_comment_cadence.py's/contributor_cadence.py's
    /deployment_cadence.py's/follower_cadence.py's/following_cadence.py's
    /fork_cadence.py's/issue_cadence.py's/issue_comment_cadence.py's
    /label_cadence.py's/listed_cadence.py's/media_cadence.py's
    /milestone_cadence.py's/pr_cadence.py's/release_cadence.py's
    BranchCadenceTamperedError/CollaboratorCadenceTamperedError
    /CommentCadenceTamperedError/CommitCadenceTamperedError
    /CommitCommentCadenceTamperedError/ContributorCadenceTamperedError
    /DeploymentCadenceTamperedError/FollowerCadenceTamperedError
    /FollowingCadenceTamperedError/ForkCadenceTamperedError
    /IssueCadenceTamperedError/IssueCommentCadenceTamperedError
    /LabelCadenceTamperedError/ListedCadenceTamperedError
    /MediaCadenceTamperedError/MilestoneCadenceTamperedError
    /PrCadenceTamperedError/ReleaseCadenceTamperedError (tasks 250-267):
    both lookup functions walk EVERY snapshot looking for the closest one
    before/after `when`, not just the tip, so a malformed line anywhere
    could be hiding the real closest snapshot and silently skipping it
    would misreport the delta/baseline. Refuse rather than guess --
    repair the log before the next real call."""


def _default_http_get(url: str) -> dict:
    import httpx

    from oracle_engine.github_auth import github_headers

    resp = httpx.get(url, headers=github_headers(), timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def fetch_run_count(repo: str = DEFAULT_REPO, http_get=None) -> int:
    """The repo's PUBLIC, unauthenticated GitHub Actions total workflow-run
    count off the GitHub REST API's `total_count` field -- read-only by
    nature, no account, no OAuth, no toolkit. A pluggable `http_get` (same
    dependency-injection shape `star_cadence.py`/`workflow_cadence.py`
    use) keeps tests off the real network."""
    getter = http_get or _default_http_get
    payload = getter(f"https://api.github.com/repos/{repo}/actions/runs")
    if "total_count" not in payload:
        raise RunCadenceError(f"malformed GitHub API response: {payload!r}")
    return int(payload["total_count"])


def load_snapshots(path: str = DEFAULT_SNAPSHOT_PATH) -> list[dict]:
    """Every snapshot line, in file order. Read-only: never touches the
    file, takes its path and hands back plain dicts. A line that is not
    even valid JSON any more (a bad hand-edit, a stray merge-conflict
    marker, a truncated write) is not allowed to crash the caller with an
    uncaught json.JSONDecodeError -- it comes back marked
    {"_malformed": True, "_error": ...} instead, the same convention
    tools/ledger.py's _entries() established (task 238) and tasks 239-267
    mirrored across every sibling."""
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                out.append({"_malformed": True, "_error": str(exc)})
    return out


def record_snapshot(count: int, ts: str, path: str = DEFAULT_SNAPSHOT_PATH) -> dict:
    """Append one `{"ts", "count"}` snapshot. Append-only, mirrors every
    other cadence source's own discipline -- no function in this module
    rewrites a prior line."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise RunCadenceError("count must be a non-negative integer")
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


def _reject_malformed(snapshots: list[dict], caller: str) -> None:
    """Raise RunCadenceTamperedError if any snapshot line came back
    marked _malformed by load_snapshots() -- both callers below walk
    every snapshot, not just the tip, so a malformed line anywhere could
    be hiding the real closest one."""
    for s in snapshots:
        if s.get("_malformed"):
            raise RunCadenceTamperedError(
                f"{caller}: the snapshot log holds a line that is not "
                f"valid JSON ({s.get('_error')}) -- refusing rather than "
                "silently skipping it."
            )


def run_count_at_or_before(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet -- never guessed at, never
    interpolated."""
    _reject_malformed(snapshots, "run_count_at_or_before")
    best = None
    for s in snapshots:
        ts = _parse_ts(s["ts"])
        if ts <= when and (best is None or ts > _parse_ts(best["ts"])):
            best = s
    return best["count"] if best else None


def run_count_at_or_after(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. The grading-side counterpart to
    `run_count_at_or_before`: once a call's window closes, the honest
    outcome is the first real observation once the window is actually
    over, not a later one that could quietly wait for a friendlier
    number."""
    _reject_malformed(snapshots, "run_count_at_or_after")
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
    GitHub Actions total runs, plus the confidence sealed alongside it.
    Pure: reads `snapshots`/`now`/`current_count`, writes nothing, decides
    nothing about whether to seal it."""
    if now.tzinfo is None:
        raise RunCadenceError("now must be timezone-aware")
    now = now.astimezone(datetime.timezone.utc)
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise RunCadenceError("current_count must be a non-negative integer")
    if horizon_hours <= 0:
        raise RunCadenceError(
            "horizon_hours must be positive — a target at or before the sealing "
            "moment is not a prediction, it is hindsight"
        )
    baseline_when = now - datetime.timedelta(hours=horizon_hours)
    baseline = run_count_at_or_before(snapshots, baseline_when)
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
        f"total workflow-run count will be at least {threshold} "
        f"(currently {current_count}{change_clause})."
    )
    return {"claim": claim, "confidence": float(confidence)}


def seal_run_prediction(
    now: datetime.datetime,
    ts: str,
    current_count: int,
    actor: str = DEFAULT_ACTOR,
    snapshots: list[dict] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs,
) -> dict:
    """Build one run-cadence prediction and seal it. `now` and `ts` are
    always passed in by the caller, same discipline every other cadence
    source in this desk holds to."""
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
    _count = fetch_run_count()
    record_snapshot(_count, _ts)
    _entry = seal_run_prediction(now=_now, ts=_ts, current_count=_count)
    print(_entry["hash"])
