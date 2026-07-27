"""The Oracle Desk's tenth real cadence: a checkable claim about the
town's own public X (`@oritatown`) following count. (ROADMAP #46)

`follower_cadence.py`/`tweet_cadence.py`/`listed_cadence.py`/
`media_cadence.py` (tasks 42-45) each read a different field off the same
`X_WhoAmI` payload, and each one measured some way the world sees or hears
the town: reach, output, curation-in, whether it ever shows a picture.
This module inverts the question. `public_metrics.following_count` is not
who watches the town — it is who the town itself chooses to watch.
`@oritatown` follows nobody by design: the Star Covenant already forbids
begging for a follow, and the town has never had a reason to reach
outward either. This cadence bets on that restraint continuing to hold,
in a direction none of the first nine cadences checked. Zero new scope,
same as every cadence before it — `oracle/SCOPES.md`'s `WhoAmI` allow-list
already covers this read.

Same unwired-default-raises-loudly shape as `follower_cadence.py`: X
exposes no public, unauthenticated REST endpoint for a profile's
following count any more than it does for followers/tweets/listed/media,
so `fetch_following_count`'s default getter documents that and raises
rather than guessing. Every real run always passes a `getter` wired to
the-hand's toolkit.

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
DEFAULT_SNAPSHOT_PATH = os.path.normpath(os.path.join(_ORACLE_ROOT, "following_snapshots.jsonl"))

DEFAULT_HANDLE = "@oritatown"
DEFAULT_HORIZON_HOURS = 168  # a week -- same slow-signal horizon as follower/tweet/listed/media
DEFAULT_CONFIDENCE = 0.6  # the town follows nobody by design; a low-count claim is the safer bet
DEFAULT_ACTOR = "retrya"


class FollowingCadenceError(ValueError):
    """The following-cadence read or the prediction it produced is not
    well-formed."""


class FollowingCadenceTamperedError(RuntimeError):
    """Raised by following_count_at_or_before/following_count_at_or_after
    when the snapshot log holds a malformed line anywhere in it. Mirrors
    branch_cadence.py's/collaborator_cadence.py's/comment_cadence.py's
    /commit_cadence.py's/commit_comment_cadence.py's/contributor_cadence.py's
    /deployment_cadence.py's/follower_cadence.py's BranchCadenceTamperedError
    /CollaboratorCadenceTamperedError/CommentCadenceTamperedError
    /CommitCadenceTamperedError/CommitCommentCadenceTamperedError
    /ContributorCadenceTamperedError/DeploymentCadenceTamperedError
    /FollowerCadenceTamperedError (tasks 250-258): both lookup functions
    walk EVERY snapshot looking for the closest one before/after `when`,
    not just the tip, so a malformed line anywhere could be hiding the
    real closest snapshot and silently skipping it would misreport the
    delta/baseline. Refuse rather than guess -- repair the log before the
    next real call."""


def _default_whoami_get() -> dict:
    """No pluggable default exists for this getter the way GitHub-sourced
    cadences reach a public, unauthenticated REST endpoint -- X exposes no
    such endpoint for a profile's following count, authenticated or not.
    In every real run (live CI included) the caller supplies
    `x_whoami_get=` wired to the-hand's `X_WhoAmI` tool (already on
    `oracle/SCOPES.md`'s `WhoAmI` allow-list). This default exists only so
    an accidental unwired call fails loudly instead of silently guessing a
    count."""
    raise NotImplementedError(
        "following_cadence has no default X getter — pass x_whoami_get= wired "
        "to the-hand's X_WhoAmI tool (oracle/SCOPES.md's WhoAmI allow-list)"
    )


def fetch_following_count(x_whoami_get=None) -> int:
    """`@oritatown`'s own `public_metrics.following_count`, off the-hand's
    `X_WhoAmI` read -- the town's own account, no per-user scope, nothing
    beyond what `oracle/SCOPES.md` already clears. A pluggable
    `x_whoami_get` (same dependency-injection shape every other cadence's
    getter uses) keeps tests off the real network/toolkit."""
    getter = x_whoami_get or _default_whoami_get
    payload = getter()
    metrics = payload.get("public_metrics") if isinstance(payload, dict) else None
    if not isinstance(metrics, dict) or "following_count" not in metrics:
        raise FollowingCadenceError(f"malformed X WhoAmI response: {payload!r}")
    return int(metrics["following_count"])


def load_snapshots(path: str = DEFAULT_SNAPSHOT_PATH) -> list[dict]:
    """Every snapshot line, in file order. Read-only: never touches the
    file, takes its path and hands back plain dicts. A line that is not
    even valid JSON any more (a bad hand-edit, a stray merge-conflict
    marker, a truncated write) is not allowed to crash the caller with an
    uncaught json.JSONDecodeError -- it comes back marked
    {"_malformed": True, "_error": ...} instead, the same convention
    tools/ledger.py's _entries() established (task 238) and tasks 239-258
    mirrored across every sibling. A line that parses cleanly but is not a
    JSON object (a bare scalar/null/list) is marked the same way -- it is
    valid JSON but not a snapshot, and every caller below assumes dict
    access."""
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                out.append({"_malformed": True, "_error": str(exc)})
                continue
            if not isinstance(value, dict):
                out.append({"_malformed": True, "_error": "not a JSON object"})
                continue
            out.append(value)
    return out


def record_snapshot(count: int, ts: str, path: str = DEFAULT_SNAPSHOT_PATH) -> dict:
    """Append one `{"ts", "count"}` snapshot. Append-only, mirrors every
    other cadence's own snapshot discipline -- no function in this module
    rewrites a prior line."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise FollowingCadenceError("count must be a non-negative integer")
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
    """Raise FollowingCadenceTamperedError if any snapshot line came back
    marked _malformed by load_snapshots() -- both callers below walk every
    snapshot, not just the tip, so a malformed line anywhere could be
    hiding the real closest one."""
    for s in snapshots:
        if s.get("_malformed"):
            raise FollowingCadenceTamperedError(
                f"{caller}: the snapshot log holds a line that is not "
                f"valid JSON ({s.get('_error')}) -- refusing rather than "
                "silently skipping it."
            )


def following_count_at_or_before(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet -- never guessed at, never
    interpolated."""
    _reject_malformed(snapshots, "following_count_at_or_before")
    best = None
    for s in snapshots:
        ts = _parse_ts(s["ts"])
        if ts <= when and (best is None or ts > _parse_ts(best["ts"])):
            best = s
    return best["count"] if best else None


def following_count_at_or_after(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. The grading-side counterpart to
    `following_count_at_or_before`: once a call's window closes, the
    honest outcome is the first real observation once the window is
    actually over, not a later one that could quietly wait for a
    friendlier number."""
    _reject_malformed(snapshots, "following_count_at_or_after")
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
    following, plus the confidence sealed alongside it. Pure: reads
    `snapshots`/`now`/`current_count`, writes nothing, decides nothing
    about whether to seal it."""
    if now.tzinfo is None:
        raise FollowingCadenceError("now must be timezone-aware")
    now = now.astimezone(datetime.timezone.utc)
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise FollowingCadenceError("current_count must be a non-negative integer")
    if horizon_hours <= 0:
        raise FollowingCadenceError(
            "horizon_hours must be positive — a target at or before the sealing "
            "moment is not a prediction, it is hindsight"
        )
    baseline_when = now - datetime.timedelta(hours=horizon_hours)
    baseline = following_count_at_or_before(snapshots, baseline_when)
    delta = None if baseline is None else current_count - baseline
    target = now + datetime.timedelta(hours=horizon_hours)
    threshold = current_count
    change_clause = (
        f", net change over the past {horizon_hours}h: {delta:+d}"
        if delta is not None
        else ", no earlier snapshot yet to compare against"
    )
    claim = (
        f"By {target.strftime('%Y-%m-%dT%H:%M:%SZ')}, {DEFAULT_HANDLE}'s public X "
        f"following count will be no more than {threshold} "
        f"(currently {current_count}{change_clause})."
    )
    return {"claim": claim, "confidence": float(confidence)}


def seal_following_prediction(
    now: datetime.datetime,
    ts: str,
    current_count: int,
    actor: str = DEFAULT_ACTOR,
    snapshots: list[dict] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs,
) -> dict:
    """Build one following-cadence prediction and seal it. `now` and `ts`
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
    _count = fetch_following_count()
    record_snapshot(_count, _ts)
    _entry = seal_following_prediction(now=_now, ts=_ts, current_count=_count)
    print(_entry["hash"])
