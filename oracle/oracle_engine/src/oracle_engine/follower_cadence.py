"""The Oracle Desk's sixth real cadence: a checkable claim about the
town's own public X (`@oritatown`) follower count. (ROADMAP #42)

`star_cadence.py`/`fork_cadence.py`/`issue_cadence.py`/`release_cadence.py`
(tasks 38-41) all read a different field or a different collection off the
same GitHub REST API — five cadences deep and every one of them still a
GitHub object. This module changes the *platform*, not just the field:
`public_metrics.followers_count` off the-hand's `X_WhoAmI` tool, which
reads `@oritatown`'s own public profile — the town's second public mouth,
not a mortal's account. `oracle/SCOPES.md`'s `Get*/List*/Search*/WhoAmI`
allow-list already covers this read; it has simply never been exercised
for a cadence before now. Zero new scope, same as every cadence before it.

Where every prior cadence's default fetch calls GitHub's public,
*unauthenticated* REST endpoint directly (no toolkit needed because a
public repo's counters have no account behind them to gate a read
against), X draws a different line: there is no public, unauthenticated
REST endpoint for a profile's follower count the way GitHub has one for a
repo's stars. The only path is the-hand's own authenticated `X_WhoAmI`
tool. So `fetch_follower_count` keeps the identical dependency-injection
shape `star_cadence.fetch_star_count`'s `http_get` uses, but its default
implementation cannot make that call itself the way `_default_http_get`
can reach `api.github.com` — there is no Python package or bare HTTP
request this module could shell out to that would be the real read.
`_default_whoami_get` documents that plainly and raises rather than
guessing; every real cadence run (this sandbox and live CI alike) always
passes a `getter` wired to the-hand's toolkit. This is the same shape
`cadence.py` (task 36) chose for its own no-HTTP precedent: a pure
function of an already-injected reading, never a network call this module
pretends it can make unassisted.

Every claim this module builds is run through `copylint.enforce_copy`
before it is ever sealed, same as every cadence before it — Ogun's law
does not carve out an exception for predicting the town's own following
either.
"""
from __future__ import annotations

import datetime
import json
import os
from types import ModuleType

from oracle_engine import copylint, prediction

_ORACLE_ENGINE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
_ORACLE_ROOT = os.path.join(_ORACLE_ENGINE_ROOT, "..")
DEFAULT_SNAPSHOT_PATH = os.path.normpath(os.path.join(_ORACLE_ROOT, "follower_snapshots.jsonl"))

DEFAULT_HANDLE = "@oritatown"
DEFAULT_HORIZON_HOURS = 168  # a week — follower growth is slow, same as stars
DEFAULT_CONFIDENCE = 0.55
DEFAULT_ACTOR = "kwaku-ananse"


class FollowerCadenceError(ValueError):
    """The follower-cadence read or the prediction it produced is not
    well-formed."""


class FollowerCadenceTamperedError(RuntimeError):
    """Raised by follower_count_at_or_before/follower_count_at_or_after
    when the snapshot log holds a malformed line anywhere in it. Mirrors
    branch_cadence.py's/collaborator_cadence.py's/comment_cadence.py's
    /commit_cadence.py's/commit_comment_cadence.py's/contributor_cadence.py's
    /deployment_cadence.py's BranchCadenceTamperedError
    /CollaboratorCadenceTamperedError/CommentCadenceTamperedError
    /CommitCadenceTamperedError/CommitCommentCadenceTamperedError
    /ContributorCadenceTamperedError/DeploymentCadenceTamperedError
    (tasks 250-256): both lookup functions walk EVERY snapshot looking for
    the closest one before/after `when`, not just the tip, so a malformed
    line anywhere could be hiding the real closest snapshot and silently
    skipping it would misreport the delta/baseline. Refuse rather than
    guess -- repair the log before the next real call."""


def _default_whoami_get() -> dict:
    """No pluggable default exists for this getter the way
    `star_cadence._default_http_get` reaches a public, unauthenticated
    REST endpoint — X exposes no such endpoint for a profile's follower
    count, authenticated or not. In every real run (live CI included) the
    caller supplies `x_whoami_get=` wired to the-hand's `X_WhoAmI` tool
    (already on `oracle/SCOPES.md`'s `WhoAmI` allow-list). This default
    exists only so an accidental unwired call fails loudly instead of
    silently guessing a count."""
    raise NotImplementedError(
        "follower_cadence has no default X getter — pass x_whoami_get= wired "
        "to the-hand's X_WhoAmI tool (oracle/SCOPES.md's WhoAmI allow-list)"
    )


def fetch_follower_count(x_whoami_get=None) -> int:
    """`@oritatown`'s own `public_metrics.followers_count`, off the-hand's
    `X_WhoAmI` read — the town's own account, no per-user scope, nothing
    beyond what `oracle/SCOPES.md` already clears. A pluggable
    `x_whoami_get` (same dependency-injection shape every other cadence's
    getter uses) keeps tests off the real network/toolkit."""
    getter = x_whoami_get or _default_whoami_get
    payload = getter()
    metrics = payload.get("public_metrics") if isinstance(payload, dict) else None
    if not isinstance(metrics, dict) or "followers_count" not in metrics:
        raise FollowerCadenceError(f"malformed X WhoAmI response: {payload!r}")
    return int(metrics["followers_count"])


def load_snapshots(path: str = DEFAULT_SNAPSHOT_PATH) -> list[dict]:
    """Every snapshot line, in file order. Read-only: never touches the
    file, takes its path and hands back plain dicts. A line that is not
    even valid JSON any more (a bad hand-edit, a stray merge-conflict
    marker, a truncated write) is not allowed to crash the caller with an
    uncaught json.JSONDecodeError -- it comes back marked
    {"_malformed": True, "_error": ...} instead, the same convention
    tools/ledger.py's _entries() established (task 238) and tasks 239-256
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
    other cadence's own snapshot discipline — no function in this module
    rewrites a prior line."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise FollowerCadenceError("count must be a non-negative integer")
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
    """Raise FollowerCadenceTamperedError if any snapshot line came back
    marked _malformed by load_snapshots() -- both callers below walk every
    snapshot, not just the tip, so a malformed line anywhere could be
    hiding the real closest one."""
    for s in snapshots:
        if s.get("_malformed"):
            raise FollowerCadenceTamperedError(
                f"{caller}: the snapshot log holds a line that is not "
                f"valid JSON ({s.get('_error')}) -- refusing rather than "
                "silently skipping it."
            )


def follower_count_at_or_before(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet — never guessed at, never interpolated."""
    _reject_malformed(snapshots, "follower_count_at_or_before")
    best = None
    for s in snapshots:
        ts = _parse_ts(s["ts"])
        if ts <= when and (best is None or ts > _parse_ts(best["ts"])):
            best = s
    return best["count"] if best else None


def follower_count_at_or_after(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. The grading-side counterpart to
    `follower_count_at_or_before`: once a call's window closes, the honest
    outcome is the first real observation once the window is actually
    over, not a later one that could quietly wait for a friendlier
    number."""
    _reject_malformed(snapshots, "follower_count_at_or_after")
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
    followers, plus the confidence sealed alongside it. Pure: reads
    `snapshots`/`now`/`current_count`, writes nothing, decides nothing
    about whether to seal it."""
    if now.tzinfo is None:
        raise FollowerCadenceError("now must be timezone-aware")
    now = now.astimezone(datetime.timezone.utc)
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise FollowerCadenceError("current_count must be a non-negative integer")
    if horizon_hours <= 0:
        raise FollowerCadenceError(
            "horizon_hours must be positive — a target at or before the sealing "
            "moment is not a prediction, it is hindsight"
        )
    baseline_when = now - datetime.timedelta(hours=horizon_hours)
    baseline = follower_count_at_or_before(snapshots, baseline_when)
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
        f"follower count will be at least {threshold} "
        f"(currently {current_count}{change_clause})."
    )
    return {"claim": claim, "confidence": float(confidence)}


def seal_follower_prediction(
    now: datetime.datetime,
    ts: str,
    current_count: int,
    actor: str = DEFAULT_ACTOR,
    snapshots: list[dict] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs,
) -> dict:
    """Build one follower-cadence prediction and seal it. `now` and `ts`
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
    _count = fetch_follower_count()
    record_snapshot(_count, _ts)
    _entry = seal_follower_prediction(now=_now, ts=_ts, current_count=_count)
    print(_entry["hash"])
