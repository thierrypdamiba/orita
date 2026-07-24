"""The Oracle Desk's fourth real cadence: a checkable claim about the
town's own public GitHub open-issue count. (ROADMAP #40)

`star_cadence.py` (task 38) and `fork_cadence.py` (task 39) proved two
cadence sources need no new scope at all when the number is already
public. The same unauthenticated GitHub REST API repo response both of
those already read also carries `open_issues_count` — a different flavor
of signal than adoption (stars) or platform-action (forks): it moves when
a mortal actually crosses the threshold and opens something (the Book of
the Gate), or holds flat when the town's own LAW holds (issue #1 stays
open forever by design, nyx's #2 "we will not close this issue"). Esu-
Elegba keeps the door (the Threshold, per STRATEGY.md's team table), so
this cadence is theirs to seal.

Structurally this mirrors `fork_cadence.py` line for line on purpose —
four independent cadence sources sharing one shape is the point, not a
missed chance to unify them into one module. A future fifth source should
be able to copy this file's shape again without reading any of the other
three first.
"""
from __future__ import annotations

import datetime
import json
import os
from types import ModuleType

from oracle_engine import copylint, prediction

_ORACLE_ENGINE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
_ORACLE_ROOT = os.path.join(_ORACLE_ENGINE_ROOT, "..")
DEFAULT_SNAPSHOT_PATH = os.path.normpath(os.path.join(_ORACLE_ROOT, "issue_snapshots.jsonl"))

DEFAULT_REPO = "thierrypdamiba/orita"
DEFAULT_HORIZON_HOURS = 336  # two weeks — a mortal crossing the threshold is rarer than a star
DEFAULT_CONFIDENCE = 0.5  # the square's own law (issues that never close) makes this the hardest call to call
DEFAULT_ACTOR = "esu-elegba"


class IssueCadenceError(ValueError):
    """The issue-cadence read or the prediction it produced is not
    well-formed."""


class IssueCadenceTamperedError(RuntimeError):
    """Raised by issue_count_at_or_before/issue_count_at_or_after when the
    snapshot log holds a malformed line anywhere in it. Mirrors
    branch_cadence.py's/collaborator_cadence.py's/comment_cadence.py's
    /commit_cadence.py's/commit_comment_cadence.py's/contributor_cadence.py's
    /deployment_cadence.py's/follower_cadence.py's/following_cadence.py's
    /fork_cadence.py's BranchCadenceTamperedError/CollaboratorCadenceTamperedError
    /CommentCadenceTamperedError/CommitCadenceTamperedError
    /CommitCommentCadenceTamperedError/ContributorCadenceTamperedError
    /DeploymentCadenceTamperedError/FollowerCadenceTamperedError
    /FollowingCadenceTamperedError/ForkCadenceTamperedError (tasks 250-259):
    both lookup functions walk EVERY snapshot looking for the closest one
    before/after `when`, not just the tip, so a malformed line anywhere
    could be hiding the real closest snapshot and silently skipping it
    would misreport the delta/baseline. Refuse rather than guess -- repair
    the log before the next real call."""


def _default_http_get(url: str) -> dict:
    import httpx

    from oracle_engine.github_auth import github_headers

    resp = httpx.get(url, headers=github_headers(), timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def fetch_open_issue_count(repo: str = DEFAULT_REPO, http_get=None) -> int:
    """The repo's PUBLIC, unauthenticated open-issue count off the GitHub
    REST API — read-only by nature, no account, no OAuth, no toolkit. Same
    pluggable `http_get` shape `star_cadence.fetch_star_count` and
    `fork_cadence.fetch_fork_count` use, kept off the real network in
    tests."""
    getter = http_get or _default_http_get
    payload = getter(f"https://api.github.com/repos/{repo}")
    if "open_issues_count" not in payload:
        raise IssueCadenceError(f"malformed GitHub API response: {payload!r}")
    return int(payload["open_issues_count"])


def load_snapshots(path: str = DEFAULT_SNAPSHOT_PATH) -> list[dict]:
    """Every snapshot line, in file order. Read-only: never touches the
    file, takes its path and hands back plain dicts. A line that is not
    even valid JSON any more (a bad hand-edit, a stray merge-conflict
    marker, a truncated write) is not allowed to crash the caller with an
    uncaught json.JSONDecodeError -- it comes back marked
    {"_malformed": True, "_error": ...} instead, the same convention
    tools/ledger.py's _entries() established (task 238) and tasks 239-259
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
    """Append one `{"ts", "count"}` snapshot. Append-only, mirrors
    `star_cadence.record_snapshot`/`fork_cadence.record_snapshot` and
    `BUILDLOG.md`'s own discipline — no function in this module rewrites a
    prior line."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise IssueCadenceError("count must be a non-negative integer")
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
    """Raise IssueCadenceTamperedError if any snapshot line came back
    marked _malformed by load_snapshots() -- both callers below walk every
    snapshot, not just the tip, so a malformed line anywhere could be
    hiding the real closest one."""
    for s in snapshots:
        if s.get("_malformed"):
            raise IssueCadenceTamperedError(
                f"{caller}: the snapshot log holds a line that is not "
                f"valid JSON ({s.get('_error')}) -- refusing rather than "
                "silently skipping it."
            )


def issue_count_at_or_before(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet — never guessed at, never interpolated."""
    _reject_malformed(snapshots, "issue_count_at_or_before")
    best = None
    for s in snapshots:
        ts = _parse_ts(s["ts"])
        if ts <= when and (best is None or ts > _parse_ts(best["ts"])):
            best = s
    return best["count"] if best else None


def issue_count_at_or_after(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. The grading-side counterpart to
    `issue_count_at_or_before`: once a call's window closes, the honest
    outcome is the first real observation once the window is actually
    over, not a later one that could quietly wait for a friendlier
    number."""
    _reject_malformed(snapshots, "issue_count_at_or_after")
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
    """One checkable claim about the town's own next window of public open
    issues, plus the confidence sealed alongside it. Pure: reads
    `snapshots`/`now`/`current_count`, writes nothing, decides nothing
    about whether to seal it."""
    if now.tzinfo is None:
        raise IssueCadenceError("now must be timezone-aware")
    now = now.astimezone(datetime.timezone.utc)
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise IssueCadenceError("current_count must be a non-negative integer")
    if horizon_hours <= 0:
        raise IssueCadenceError(
            "horizon_hours must be positive — a target at or before the sealing "
            "moment is not a prediction, it is hindsight"
        )
    baseline_when = now - datetime.timedelta(hours=horizon_hours)
    baseline = issue_count_at_or_before(snapshots, baseline_when)
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
        f"open-issue count will be at least {threshold} "
        f"(currently {current_count}{change_clause})."
    )
    return {"claim": claim, "confidence": float(confidence)}


def seal_issue_prediction(
    now: datetime.datetime,
    ts: str,
    current_count: int,
    actor: str = DEFAULT_ACTOR,
    snapshots: list[dict] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs,
) -> dict:
    """Build one issue-cadence prediction and seal it. `now` and `ts` are
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
    _count = fetch_open_issue_count()
    record_snapshot(_count, _ts)
    _entry = seal_issue_prediction(now=_now, ts=_ts, current_count=_count)
    print(_entry["hash"])
