"""The Oracle Desk's thirteenth real cadence: a checkable claim about the
town's own public GitHub commit count. (ROADMAP #49)

Tasks 38-48 mined two wells dry: the repo object (stars, forks, open
issues) and `X_WhoAmI`'s `public_metrics` (followers, tweets, listed,
media, following), then moved to two further public, unauthenticated
collections (`/releases`, `/contributors`, `/branches`) once the first
well ran out. All twelve measure a REACTION to the town (a star, a
follow) or an ATTEMPT at crossing into it (a branch, a contributor). None
of them measure the town's own base rate of work — the thing `BUILDLOG.md`
already timestamps by hand, every hour, forever. `GET
/repos/{owner}/{repo}/commits` is a third public, unauthenticated
collection endpoint (mirroring `contributor_cadence.py`/`branch_cadence.py`'s
paginated-list shape) that counts exactly that: the town's own accumulated
build volume, sourced with no new Arcade tool, no new scope, no per-user
account.

This is Nyx's first cadence source on the desk, sealed inside her own
00:00-06:00 UTC window (`TOWN-OPERATIONS.md`'s WINDOW rule) rather than
handed to a day-side god — a metric about the town's own accumulated
labor, sealed by the one house that watches the town when no one else is
awake to.

Structurally this mirrors `contributor_cadence.py`/`branch_cadence.py`
line for line on purpose — a future fourteenth source should be able to
copy this file's shape again without reading any of the other twelve
first.
"""
from __future__ import annotations

import datetime
import json
import os
from types import ModuleType

from oracle_engine import copylint, github_auth, prediction, time_utils

_ORACLE_ENGINE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
_ORACLE_ROOT = os.path.join(_ORACLE_ENGINE_ROOT, "..")
DEFAULT_SNAPSHOT_PATH = os.path.normpath(os.path.join(_ORACLE_ROOT, "commit_snapshots.jsonl"))

DEFAULT_REPO = "thierrypdamiba/orita"
DEFAULT_HORIZON_HOURS = 168  # one week — build volume moves fast; a shorter horizon than the slower adoption cadences
DEFAULT_CONFIDENCE = 0.6
DEFAULT_ACTOR = "nyx"
_MAX_PAGES = 500  # 500 * 100 = 50,000 commits, far beyond any plausible count; a hard stop, not a guess


class CommitCadenceError(ValueError):
    """The commit-cadence read or the prediction it produced is not
    well-formed."""


class CommitCadenceTamperedError(RuntimeError):
    """Raised by commit_count_at_or_before/commit_count_at_or_after when
    the snapshot log holds a malformed line anywhere in it. Mirrors
    branch_cadence.py's/collaborator_cadence.py's/comment_cadence.py's
    BranchCadenceTamperedError/CollaboratorCadenceTamperedError
    /CommentCadenceTamperedError (tasks 250-252): both lookup functions
    walk EVERY snapshot looking for the closest one before/after `when`, not
    just the tip, so a malformed line anywhere could be hiding the real
    closest snapshot and silently skipping it would misreport the
    delta/baseline. Refuse rather than guess -- repair the log before the
    next real call."""


_default_http_get = github_auth.default_http_get


def fetch_commit_count(repo: str = DEFAULT_REPO, http_get=None) -> int:
    """The repo's PUBLIC, unauthenticated commit count off the GitHub REST
    API's commits collection (default branch) — read-only by nature, no
    account, no OAuth, no toolkit. Like `release_cadence`/`contributor_cadence`
    /`branch_cadence`, this endpoint returns a paginated LIST, not a single
    count field, so this function pages through it rather than trusting one
    response is everything. Same pluggable `http_get` shape every other
    cadence uses, kept off the real network in tests."""
    getter = http_get or _default_http_get
    total = 0
    for page in range(1, _MAX_PAGES + 1):
        payload = getter(f"https://api.github.com/repos/{repo}/commits?per_page=100&page={page}")
        if not isinstance(payload, list):
            raise CommitCadenceError(f"malformed GitHub API response: {payload!r}")
        total += len(payload)
        if len(payload) < 100:
            return total
    raise CommitCadenceError(f"commit count exceeded the {_MAX_PAGES}-page safety cap")


def load_snapshots(path: str = DEFAULT_SNAPSHOT_PATH) -> list[dict]:
    """Every snapshot line, in file order. Read-only: never touches the
    file, takes its path and hands back plain dicts. A line that is not
    even valid JSON any more (a bad hand-edit, a stray merge-conflict
    marker, a truncated write) is not allowed to crash the caller with an
    uncaught json.JSONDecodeError -- it comes back marked
    {"_malformed": True, "_error": ...} instead, the same convention
    tools/ledger.py's _entries() established (task 238) and tasks 239-252
    mirrored across every sibling. A line that parses cleanly as JSON but
    is not itself an object (a bare int/float/bool/null/list/string -- a
    truncated write landing mid-value) is marked the same way instead of
    sailing through unmarked, mirroring tasks 328-331's identical guard."""
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
    other cadence's `record_snapshot` and `BUILDLOG.md`'s own discipline —
    no function in this module rewrites a prior line."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise CommitCadenceError("count must be a non-negative integer")
    entry = {"ts": ts, "count": int(count)}
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


_parse_ts = time_utils.parse_ts


def _reject_malformed(snapshots: list[dict], caller: str) -> None:
    """Raise CommitCadenceTamperedError if any snapshot line came back
    marked _malformed by load_snapshots() -- both callers below walk every
    snapshot, not just the tip, so a malformed line anywhere could be
    hiding the real closest one."""
    for s in snapshots:
        if s.get("_malformed"):
            raise CommitCadenceTamperedError(
                f"{caller}: the snapshot log holds a line that is not "
                f"valid JSON ({s.get('_error')}) -- refusing rather than "
                "silently skipping it."
            )


def commit_count_at_or_before(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet — never guessed at, never interpolated."""
    _reject_malformed(snapshots, "commit_count_at_or_before")
    best = None
    for s in snapshots:
        ts = _parse_ts(s["ts"])
        if ts <= when and (best is None or ts > _parse_ts(best["ts"])):
            best = s
    return best["count"] if best else None


def commit_count_at_or_after(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. The grading-side counterpart to
    `commit_count_at_or_before`: once a call's window closes, the honest
    outcome is the first real observation once the window is actually
    over, not a later one that could quietly wait for a friendlier
    number."""
    _reject_malformed(snapshots, "commit_count_at_or_after")
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
    commits, plus the confidence sealed alongside it. Pure: reads
    `snapshots`/`now`/`current_count`, writes nothing, decides nothing
    about whether to seal it."""
    if now.tzinfo is None:
        raise CommitCadenceError("now must be timezone-aware")
    now = now.astimezone(datetime.timezone.utc)
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise CommitCadenceError("current_count must be a non-negative integer")
    if horizon_hours <= 0:
        raise CommitCadenceError(
            "horizon_hours must be positive — a target at or before the sealing "
            "moment is not a prediction, it is hindsight"
        )
    baseline_when = now - datetime.timedelta(hours=horizon_hours)
    baseline = commit_count_at_or_before(snapshots, baseline_when)
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
        f"commit count will be at least {threshold} "
        f"(currently {current_count}{change_clause})."
    )
    return {"claim": claim, "confidence": float(confidence)}


def seal_commit_prediction(
    now: datetime.datetime,
    ts: str,
    current_count: int,
    actor: str = DEFAULT_ACTOR,
    snapshots: list[dict] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs,
) -> dict:
    """Build one commit-cadence prediction and seal it. `now` and `ts` are
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
    _count = fetch_commit_count()
    record_snapshot(_count, _ts)
    _entry = seal_commit_prediction(now=_now, ts=_ts, current_count=_count)
    print(_entry["hash"])
