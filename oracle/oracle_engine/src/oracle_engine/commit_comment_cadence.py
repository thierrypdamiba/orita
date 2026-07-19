"""The Oracle Desk's twenty-fifth real cadence: a checkable claim about
the town's own public GitHub COMMIT comment count. (ROADMAP #93)

Task 76 read `GET /repos/{owner}/{repo}/pulls/comments` (every line-anchored
PR REVIEW comment) and named the endpoint it deliberately left standing:
`/issues/comments`. Task 77 closed that one (every issue-and-PR-THREAD
comment). GitHub's REST API actually exposes a THIRD, structurally distinct
repo-wide comments collection neither task touched:
`GET /repos/{owner}/{repo}/comments` -- a comment left directly on a
COMMIT itself (the "Add comment" button on a commit's own page), never
tied to a pull request or an issue thread at all, sometimes landing on a
commit that never became either. This module reads that third and last
member of the family, closing it the same way task 89 closed a stale
PENDING note -- not because a countdown ran out, but because someone
finally checked what was left standing. Same public, unauthenticated
GitHub REST API family task 38 already cleared: no credential, no OAuth,
no toolkit, no per-user account, no new scope of any kind.

Structurally this mirrors `comment_cadence.py`/`issue_comment_cadence.py`
line for line on purpose -- one shape reused a twenty-fifth time is the
point, not a missed chance to unify. Sealed by Off-By-One, who has staked
no Oracle Desk claim of his own until now despite being the Warden who
counts everything else in this town -- a comment landing on a specific
commit and nowhere else is the most "off by one" reaction shape GitHub
exposes: attached to one exact point in history, not a thread, not a
diff line, just one commit, one remark. This run lands outside Nyx's and
the child's 00:00-06:00 UTC window (`TOWN-OPERATIONS.md`'s WINDOW rule),
so it is sealed and committed by a house free to act in daylight, same as
`workflow_cadence.py` (task 60, Ogun) and `deployment_cadence.py` (task
68, Retrya) before it.

`GET /repos/{owner}/{repo}/comments` has never run in this desk's
production CI before -- `oracle/SCOPES.md`'s tasks 64/78 already learned,
the hard way, that an untested endpoint's real-world behavior (rate limit,
permission wall, pagination shape) is not provable from a sandbox that
cannot reach `api.github.com` directly at all (confirmed again this hour:
`GitHub access is not enabled for this session` at the proxy layer, the
identical wall tasks 60/75/89 already hit). This module is fully built and
tested against a mocked `http_get`; its first live call is honestly
PENDING the next scheduled `oracle-cadence.yml` run, wired with the same
precautionary `continue-on-error: true` tasks 67/68/77 used for their own
untested endpoints.
"""
from __future__ import annotations

import datetime
import json
import os
from types import ModuleType

from oracle_engine import copylint, prediction

_ORACLE_ENGINE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
_ORACLE_ROOT = os.path.join(_ORACLE_ENGINE_ROOT, "..")
DEFAULT_SNAPSHOT_PATH = os.path.normpath(
    os.path.join(_ORACLE_ROOT, "commit_comment_snapshots.jsonl")
)

DEFAULT_REPO = "thierrypdamiba/orita"
DEFAULT_HORIZON_HOURS = 336  # two weeks -- same rarity assumption as comment_cadence.py
DEFAULT_CONFIDENCE = 0.5
DEFAULT_ACTOR = "off-by-one"
_MAX_PAGES = 20  # 20 * 100 = 2000 comments, far beyond any plausible count; a hard stop, not a guess


class CommitCommentCadenceError(ValueError):
    """The commit-comment-cadence read or the prediction it produced is
    not well-formed."""


def _default_http_get(url: str) -> list:
    import httpx

    from oracle_engine.github_auth import github_headers

    resp = httpx.get(url, headers=github_headers(), timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def fetch_commit_comment_count(repo: str = DEFAULT_REPO, http_get=None) -> int:
    """The repo's PUBLIC, unauthenticated commit-comment count off the
    GitHub REST API's `/comments` collection -- read-only by nature, no
    account, no OAuth, no toolkit. Like `branch_cadence.fetch_branch_count`
    and `comment_cadence.fetch_comment_count`, this endpoint returns a
    paginated LIST, not a single count field, so this function pages
    through it rather than trusting one response is everything. Same
    pluggable `http_get` shape every other cadence uses, kept off the
    real network in tests."""
    getter = http_get or _default_http_get
    total = 0
    for page in range(1, _MAX_PAGES + 1):
        payload = getter(f"https://api.github.com/repos/{repo}/comments?per_page=100&page={page}")
        if not isinstance(payload, list):
            raise CommitCommentCadenceError(f"malformed GitHub API response: {payload!r}")
        total += len(payload)
        if len(payload) < 100:
            return total
    raise CommitCommentCadenceError(f"commit comment count exceeded the {_MAX_PAGES}-page safety cap")


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
    prior cadence's `record_snapshot` and `BUILDLOG.md`'s own discipline --
    no function in this module rewrites a prior line."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise CommitCommentCadenceError("count must be a non-negative integer")
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


def commit_comment_count_at_or_before(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet -- never guessed at, never
    interpolated."""
    best = None
    for s in snapshots:
        ts = _parse_ts(s["ts"])
        if ts <= when and (best is None or ts > _parse_ts(best["ts"])):
            best = s
    return best["count"] if best else None


def commit_comment_count_at_or_after(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. The grading-side counterpart to
    `commit_comment_count_at_or_before`: once a call's window closes, the
    honest outcome is the first real observation once the window is
    actually over, not a later one that could quietly wait for a
    friendlier number."""
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
    commit comments, plus the confidence sealed alongside it. Pure: reads
    `snapshots`/`now`/`current_count`, writes nothing, decides nothing
    about whether to seal it."""
    if now.tzinfo is None:
        raise CommitCommentCadenceError("now must be timezone-aware")
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise CommitCommentCadenceError("current_count must be a non-negative integer")
    baseline_when = now - datetime.timedelta(hours=horizon_hours)
    baseline = commit_comment_count_at_or_before(snapshots, baseline_when)
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
        f"commit comment count will be at least {threshold} "
        f"(currently {current_count}{change_clause})."
    )
    return {"claim": claim, "confidence": float(confidence)}


def seal_commit_comment_prediction(
    now: datetime.datetime,
    ts: str,
    current_count: int,
    actor: str = DEFAULT_ACTOR,
    snapshots: list[dict] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs,
) -> dict:
    """Build one commit-comment-cadence prediction and seal it. `now` and
    `ts` are always passed in by the caller, same discipline every other
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
    _count = fetch_commit_comment_count()
    record_snapshot(_count, _ts)
    _entry = seal_commit_comment_prediction(now=_now, ts=_ts, current_count=_count)
    print(_entry["hash"])
