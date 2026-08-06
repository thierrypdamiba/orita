"""The Oracle Desk's sixteenth real cadence: a checkable claim about the
town's own public GitHub repository label count. (ROADMAP #52)

Tasks 38-41 read the repo object dry (stars, forks, open issues, releases);
tasks 42-46 read `X_WhoAmI`'s `public_metrics` dry (followers, tweets,
listed, media, following); tasks 47-51 opened a run of independent GitHub
list endpoints (contributors, branches, commits, subscribers, tags) — every
one of which measured something a MORTAL did to the town, or a mark the
town cut and pushed outward toward the world (a commit, a tag). This
module reads a seventh such endpoint the desk has not touched before: `GET
/repos/{owner}/{repo}/labels`. Unlike every list endpoint before it, a
label is not a trace left by activity — it is the town's own internal
taxonomy, the vocabulary it built for itself to sort the square before any
mortal ever needed it explained (`esu-elegba`'s intent-forcing issue
templates, task 9, and the `house:<slug>` label naming each god's own gate
both live here). This is the first cadence to bet on whether the town
keeps organizing itself, not on whether anyone out there reacts to it.

Structurally this mirrors `contributor_cadence.py`/`branch_cadence.py`/
`commit_cadence.py`/`subscriber_cadence.py`/`tag_cadence.py` line for line
on purpose — sixteen independent cadence sources sharing one shape is the
point, not a missed chance to unify them into one module. A future
seventeenth source should be able to copy this file's shape again without
reading any of the other sixteen first.
"""
from __future__ import annotations

import datetime
import os
from types import ModuleType

from oracle_engine import copylint, github_auth, prediction, time_utils

_ORACLE_ENGINE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
_ORACLE_ROOT = os.path.join(_ORACLE_ENGINE_ROOT, "..")
DEFAULT_SNAPSHOT_PATH = os.path.normpath(os.path.join(_ORACLE_ROOT, "label_snapshots.jsonl"))

DEFAULT_REPO = "thierrypdamiba/orita"
DEFAULT_HORIZON_HOURS = 336  # two weeks — a taxonomy changes rarer than a tag
DEFAULT_CONFIDENCE = 0.5
DEFAULT_ACTOR = "nyx"
_MAX_PAGES = 20  # 20 * 100 = 2000 labels, far beyond any plausible count; a hard stop, not a guess


class LabelCadenceError(ValueError):
    """The label-cadence read or the prediction it produced is not
    well-formed."""


class LabelCadenceTamperedError(RuntimeError):
    """Raised by label_count_at_or_before/label_count_at_or_after when the
    snapshot log holds a malformed line anywhere in it. Mirrors
    branch_cadence.py's/collaborator_cadence.py's/comment_cadence.py's
    /commit_cadence.py's/commit_comment_cadence.py's/contributor_cadence.py's
    /deployment_cadence.py's/follower_cadence.py's/following_cadence.py's
    /fork_cadence.py's/issue_cadence.py's/issue_comment_cadence.py's
    BranchCadenceTamperedError/CollaboratorCadenceTamperedError
    /CommentCadenceTamperedError/CommitCadenceTamperedError
    /CommitCommentCadenceTamperedError/ContributorCadenceTamperedError
    /DeploymentCadenceTamperedError/FollowerCadenceTamperedError
    /FollowingCadenceTamperedError/ForkCadenceTamperedError
    /IssueCadenceTamperedError/IssueCommentCadenceTamperedError (tasks
    250-261): both lookup functions walk EVERY snapshot looking for the
    closest one before/after `when`, not just the tip, so a malformed line
    anywhere could be hiding the real closest snapshot and silently
    skipping it would misreport the delta/baseline. Refuse rather than
    guess -- repair the log before the next real call."""


_default_http_get = github_auth.default_http_get


def fetch_label_count(repo: str = DEFAULT_REPO, http_get=None) -> int:
    """The repo's PUBLIC, unauthenticated label count off the GitHub REST
    API's labels collection — read-only by nature, no account, no OAuth, no
    toolkit. Like `contributor_cadence.fetch_contributor_count` and
    `tag_cadence.fetch_tag_count`, this endpoint returns a paginated LIST,
    not a single count field, so this function pages through it rather than
    trusting one response is everything. Same pluggable `http_get` shape
    every other cadence uses, kept off the real network in tests."""
    getter = http_get or _default_http_get
    total = 0
    for page in range(1, _MAX_PAGES + 1):
        payload = getter(f"https://api.github.com/repos/{repo}/labels?per_page=100&page={page}")
        if not isinstance(payload, list):
            raise LabelCadenceError(f"malformed GitHub API response: {payload!r}")
        total += len(payload)
        if len(payload) < 100:
            return total
    raise LabelCadenceError(f"label count exceeded the {_MAX_PAGES}-page safety cap")


def load_snapshots(path: str = DEFAULT_SNAPSHOT_PATH) -> list[dict]:
    """This module's own default-path wrapper around the shared
    time_utils.load_snapshots (task 523). Kept here rather than a bare name
    rebinding (unlike _parse_ts = time_utils.parse_ts) because every
    sibling's DEFAULT_SNAPSHOT_PATH differs and this module's own
    load_snapshots() call sites below rely on that default -- but the
    actual read-and-mark-malformed logic lives in exactly one place now,
    not twenty-five."""
    return time_utils.load_snapshots(path)


def record_snapshot(count: int, ts: str, path: str = DEFAULT_SNAPSHOT_PATH) -> dict:
    """Append one `{"ts", "count"}` snapshot. Thin wrapper around
    `time_utils.record_snapshot` (task 559) — keeps this module's own
    default path and `LabelCadenceError`, delegates the actual
    validate-and-write to the one shared implementation."""
    return time_utils.record_snapshot(count, ts, path, error_cls=LabelCadenceError)


_parse_ts = time_utils.parse_ts


def _reject_malformed(snapshots: list[dict], caller: str) -> None:
    """Raise LabelCadenceTamperedError if any snapshot line came back marked
    _malformed by load_snapshots(). Thin wrapper around
    time_utils.reject_malformed (task 563) -- keeps this module's own
    error class, delegates the actual walk-and-raise logic to the one
    shared implementation."""
    time_utils.reject_malformed(snapshots, caller, error_cls=LabelCadenceTamperedError)


def label_count_at_or_before(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet — never guessed at, never interpolated."""
    _reject_malformed(snapshots, "label_count_at_or_before")
    best = None
    for s in snapshots:
        ts = _parse_ts(s["ts"])
        if ts <= when and (best is None or ts > _parse_ts(best["ts"])):
            best = s
    return best["count"] if best else None


def label_count_at_or_after(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. The grading-side counterpart to
    `label_count_at_or_before`: once a call's window closes, the honest
    outcome is the first real observation once the window is actually
    over, not a later one that could quietly wait for a friendlier
    number."""
    _reject_malformed(snapshots, "label_count_at_or_after")
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
    repository labels, plus the confidence sealed alongside it. Pure: reads
    `snapshots`/`now`/`current_count`, writes nothing, decides nothing
    about whether to seal it."""
    if now.tzinfo is None:
        raise LabelCadenceError("now must be timezone-aware")
    now = now.astimezone(datetime.timezone.utc)
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise LabelCadenceError("current_count must be a non-negative integer")
    if horizon_hours <= 0:
        raise LabelCadenceError(
            "horizon_hours must be positive — a target at or before the sealing "
            "moment is not a prediction, it is hindsight"
        )
    baseline_when = now - datetime.timedelta(hours=horizon_hours)
    baseline = label_count_at_or_before(snapshots, baseline_when)
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
        f"repository label count will be at least {threshold} "
        f"(currently {current_count}{change_clause})."
    )
    return {"claim": claim, "confidence": float(confidence)}


def seal_label_prediction(
    now: datetime.datetime,
    ts: str,
    current_count: int,
    actor: str = DEFAULT_ACTOR,
    snapshots: list[dict] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs,
) -> dict:
    """Build one label-cadence prediction and seal it. `now` and `ts` are
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
    _count = fetch_label_count()
    record_snapshot(_count, _ts)
    _entry = seal_label_prediction(now=_now, ts=_ts, current_count=_count)
    print(_entry["hash"])
