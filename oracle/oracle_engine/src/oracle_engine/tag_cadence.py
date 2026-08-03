"""The Oracle Desk's fifteenth real cadence: a checkable claim about the
town's own public GitHub tag count. (ROADMAP #51)

Tasks 38-41 read the repo object dry (stars, forks, open issues, releases);
tasks 42-46 read `X_WhoAmI`'s `public_metrics` dry (followers, tweets,
listed, media, following); tasks 47-50 opened a run of independent GitHub
list endpoints (contributors, branches, commits, subscribers). This module
reads a sixth such endpoint the desk has not touched before: `GET
/repos/{owner}/{repo}/tags`. A tag is a quieter act than a release (task
41) — every release requires a tag underneath it, but a tag can be cut with
`git tag` and pushed, and then never turned into an announced release at
all. That gap between a mark cut and a thing surfaced is exactly the shape
Fencepost hunts for elsewhere in this same town; here it becomes a
checkable claim instead of a scan result.

Structurally this mirrors `contributor_cadence.py`/`branch_cadence.py`/
`commit_cadence.py` line for line on purpose — fifteen independent cadence
sources sharing one shape is the point, not a missed chance to unify them
into one module. A future sixteenth source should be able to copy this
file's shape again without reading any of the other fifteen first.
"""
from __future__ import annotations

import datetime
import json
import os
from types import ModuleType

from oracle_engine import copylint, github_auth, prediction, time_utils

_ORACLE_ENGINE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
_ORACLE_ROOT = os.path.join(_ORACLE_ENGINE_ROOT, "..")
DEFAULT_SNAPSHOT_PATH = os.path.normpath(os.path.join(_ORACLE_ROOT, "tag_snapshots.jsonl"))

DEFAULT_REPO = "thierrypdamiba/orita"
DEFAULT_HORIZON_HOURS = 336  # two weeks — a mortal-shaped tag is rarer than a release
DEFAULT_CONFIDENCE = 0.5
DEFAULT_ACTOR = "nyx"
_MAX_PAGES = 20  # 20 * 100 = 2000 tags, far beyond any plausible count; a hard stop, not a guess


class TagCadenceError(ValueError):
    """The tag-cadence read or the prediction it produced is not
    well-formed."""


class TagCadenceTamperedError(RuntimeError):
    """Raised by tag_count_at_or_before/tag_count_at_or_after when the
    snapshot log holds a malformed line anywhere in it. Mirrors
    branch_cadence.py's/collaborator_cadence.py's/comment_cadence.py's
    /commit_cadence.py's/commit_comment_cadence.py's/contributor_cadence.py's
    /deployment_cadence.py's/follower_cadence.py's/following_cadence.py's
    /fork_cadence.py's/issue_cadence.py's/issue_comment_cadence.py's
    /label_cadence.py's/listed_cadence.py's/media_cadence.py's
    /milestone_cadence.py's/pr_cadence.py's/release_cadence.py's
    /run_cadence.py's/star_cadence.py's/subscriber_cadence.py's
    BranchCadenceTamperedError/CollaboratorCadenceTamperedError
    /CommentCadenceTamperedError/CommitCadenceTamperedError
    /CommitCommentCadenceTamperedError/ContributorCadenceTamperedError
    /DeploymentCadenceTamperedError/FollowerCadenceTamperedError
    /FollowingCadenceTamperedError/ForkCadenceTamperedError
    /IssueCadenceTamperedError/IssueCommentCadenceTamperedError
    /LabelCadenceTamperedError/ListedCadenceTamperedError
    /MediaCadenceTamperedError/MilestoneCadenceTamperedError
    /PrCadenceTamperedError/ReleaseCadenceTamperedError
    /RunCadenceTamperedError/StarCadenceTamperedError
    /SubscriberCadenceTamperedError (tasks 250-270): both lookup functions
    walk EVERY snapshot looking for the closest one before/after `when`,
    not just the tip, so a malformed line anywhere could be hiding the
    real closest snapshot and silently skipping it would misreport the
    delta/baseline. Refuse rather than guess -- repair the log before the
    next real call."""


_default_http_get = github_auth.default_http_get


def fetch_tag_count(repo: str = DEFAULT_REPO, http_get=None) -> int:
    """The repo's PUBLIC, unauthenticated tag count off the GitHub REST
    API's tags collection — read-only by nature, no account, no OAuth, no
    toolkit. Like `contributor_cadence.fetch_contributor_count` and
    `branch_cadence.fetch_branch_count`, this endpoint returns a paginated
    LIST, not a single count field, so this function pages through it
    rather than trusting one response is everything. Same pluggable
    `http_get` shape every other cadence uses, kept off the real network in
    tests."""
    getter = http_get or _default_http_get
    total = 0
    for page in range(1, _MAX_PAGES + 1):
        payload = getter(f"https://api.github.com/repos/{repo}/tags?per_page=100&page={page}")
        if not isinstance(payload, list):
            raise TagCadenceError(f"malformed GitHub API response: {payload!r}")
        total += len(payload)
        if len(payload) < 100:
            return total
    raise TagCadenceError(f"tag count exceeded the {_MAX_PAGES}-page safety cap")


def load_snapshots(path: str = DEFAULT_SNAPSHOT_PATH) -> list[dict]:
    """Every snapshot line, in file order. Read-only: never touches the
    file, takes its path and hands back plain dicts. A line that is not
    even valid JSON any more (a bad hand-edit, a stray merge-conflict
    marker, a truncated write) is not allowed to crash the caller with an
    uncaught json.JSONDecodeError -- it comes back marked
    {"_malformed": True, "_error": ...} instead, the same convention
    tools/ledger.py's _entries() established (task 238) and tasks 239-270
    mirrored across every sibling. A line that parses cleanly to a
    well-formed JSON value that is not an object (a bare scalar, null, or
    list -- a truncated write landing mid-value) is marked the same way
    rather than sailing through unmarked (tasks 329-349)."""
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
    prior cadence's `record_snapshot` and `BUILDLOG.md`'s own discipline —
    no function in this module rewrites a prior line."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise TagCadenceError("count must be a non-negative integer")
    entry = {"ts": ts, "count": int(count)}
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


_parse_ts = time_utils.parse_ts


def _reject_malformed(snapshots: list[dict], caller: str) -> None:
    """Raise TagCadenceTamperedError if any snapshot line came back marked
    _malformed by load_snapshots() -- both callers below walk every
    snapshot, not just the tip, so a malformed line anywhere could be
    hiding the real closest one."""
    for s in snapshots:
        if s.get("_malformed"):
            raise TagCadenceTamperedError(
                f"{caller}: the snapshot log holds a line that is not "
                f"valid JSON ({s.get('_error')}) -- refusing rather than "
                "silently skipping it."
            )


def tag_count_at_or_before(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet — never guessed at, never interpolated."""
    _reject_malformed(snapshots, "tag_count_at_or_before")
    best = None
    for s in snapshots:
        ts = _parse_ts(s["ts"])
        if ts <= when and (best is None or ts > _parse_ts(best["ts"])):
            best = s
    return best["count"] if best else None


def tag_count_at_or_after(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. The grading-side counterpart to
    `tag_count_at_or_before`: once a call's window closes, the honest
    outcome is the first real observation once the window is actually
    over, not a later one that could quietly wait for a friendlier
    number."""
    _reject_malformed(snapshots, "tag_count_at_or_after")
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
    tags, plus the confidence sealed alongside it. Pure: reads
    `snapshots`/`now`/`current_count`, writes nothing, decides nothing
    about whether to seal it."""
    if now.tzinfo is None:
        raise TagCadenceError("now must be timezone-aware")
    now = now.astimezone(datetime.timezone.utc)
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise TagCadenceError("current_count must be a non-negative integer")
    if horizon_hours <= 0:
        raise TagCadenceError(
            "horizon_hours must be positive — a target at or before the sealing "
            "moment is not a prediction, it is hindsight"
        )
    baseline_when = now - datetime.timedelta(hours=horizon_hours)
    baseline = tag_count_at_or_before(snapshots, baseline_when)
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
        f"tag count will be at least {threshold} "
        f"(currently {current_count}{change_clause})."
    )
    return {"claim": claim, "confidence": float(confidence)}


def seal_tag_prediction(
    now: datetime.datetime,
    ts: str,
    current_count: int,
    actor: str = DEFAULT_ACTOR,
    snapshots: list[dict] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs,
) -> dict:
    """Build one tag-cadence prediction and seal it. `now` and `ts` are
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
    _count = fetch_tag_count()
    record_snapshot(_count, _ts)
    _entry = seal_tag_prediction(now=_now, ts=_ts, current_count=_count)
    print(_entry["hash"])
