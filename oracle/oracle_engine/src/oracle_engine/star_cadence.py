"""The Oracle Desk's second real cadence: a checkable claim about the
town's own public GitHub stargazer count. (ROADMAP #38)

`cadence.py` (task 36) proved the desk could say one true, self-referential
thing without waiting on Tavily. It reads `BUILDLOG.md`, a record the town
already keeps honest. This module reads a second record the town already
has for free, in an even stronger sense: `thierrypdamiba/orita`'s public
stargazer count needs no toolkit, no Arcade scope, not even the-hand — the
GitHub REST API serves it to anyone, unauthenticated, because it is public
by definition. `oracle/SCOPES.md`'s `Count*` allow-list already covers the
shape of this read; this module doesn't even need the allow-listed tool to
exercise it, since there is no account behind a public repo's star count to
gate a read against.

Where `cadence.py` has one durable record to read (`BUILDLOG.md` already
exists, line per shipped task), a star count is a single live number with
no history of its own — so this module keeps one: `record_snapshot` appends
a `{"ts", "count"}` line to `oracle/star_snapshots.jsonl` every cadence run,
the same append-only discipline `BUILDLOG.md` and `tools/ledger.py` already
hold themselves to. No function here rewrites a prior snapshot.

Every claim this module builds is run through `copylint.enforce_copy`
before it is ever sealed, same as `cadence.py` — Ogun's law does not carve
out an exception for predicting the town's own popularity either.

`DEFAULT_ACTOR` (task 147): every cadence module written after this one
(`fork_cadence.py` onward, tasks 39-63) parameterizes `seal_*_prediction`'s
actor default via a module-level `DEFAULT_ACTOR` constant rather than a
hardcoded literal — several of them citing this file by name as the shape
they mirror line for line. This file did not hold its own claimed shape
until task 147 backported the constant, unchanged in value ("off-by-one").
"""
from __future__ import annotations

import datetime
import os
from types import ModuleType

from oracle_engine import copylint, github_auth, prediction, time_utils

_ORACLE_ENGINE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
_ORACLE_ROOT = os.path.join(_ORACLE_ENGINE_ROOT, "..")
DEFAULT_SNAPSHOT_PATH = os.path.normpath(os.path.join(_ORACLE_ROOT, "star_snapshots.jsonl"))

DEFAULT_REPO = "thierrypdamiba/orita"
DEFAULT_HORIZON_HOURS = 168  # a week — star growth is slower than task velocity
DEFAULT_CONFIDENCE = 0.6
DEFAULT_ACTOR = "off-by-one"


class StarCadenceError(ValueError):
    """The star-cadence read or the prediction it produced is not
    well-formed."""


class StarCadenceTamperedError(RuntimeError):
    """Raised by star_count_at_or_before/star_count_at_or_after when the
    snapshot log holds a malformed line anywhere in it. Mirrors
    branch_cadence.py's/collaborator_cadence.py's/comment_cadence.py's
    /commit_cadence.py's/commit_comment_cadence.py's/contributor_cadence.py's
    /deployment_cadence.py's/follower_cadence.py's/following_cadence.py's
    /fork_cadence.py's/issue_cadence.py's/issue_comment_cadence.py's
    /label_cadence.py's/listed_cadence.py's/media_cadence.py's
    /milestone_cadence.py's/pr_cadence.py's/release_cadence.py's
    /run_cadence.py's BranchCadenceTamperedError/CollaboratorCadenceTamperedError
    /CommentCadenceTamperedError/CommitCadenceTamperedError
    /CommitCommentCadenceTamperedError/ContributorCadenceTamperedError
    /DeploymentCadenceTamperedError/FollowerCadenceTamperedError
    /FollowingCadenceTamperedError/ForkCadenceTamperedError
    /IssueCadenceTamperedError/IssueCommentCadenceTamperedError
    /LabelCadenceTamperedError/ListedCadenceTamperedError
    /MediaCadenceTamperedError/MilestoneCadenceTamperedError
    /PrCadenceTamperedError/ReleaseCadenceTamperedError/RunCadenceTamperedError
    (tasks 250-268): both lookup functions walk EVERY snapshot looking for
    the closest one before/after `when`, not just the tip, so a malformed
    line anywhere could be hiding the real closest snapshot and silently
    skipping it would misreport the delta/baseline. Refuse rather than
    guess -- repair the log before the next real call."""


_default_http_get = github_auth.default_http_get


def fetch_star_count(repo: str = DEFAULT_REPO, http_get=None) -> int:
    """The repo's PUBLIC, unauthenticated stargazer count off the GitHub
    REST API — read-only by nature, no account, no OAuth, no toolkit. A
    pluggable `http_get` (same dependency-injection shape `draftback.py`
    uses for `create_fn`) keeps tests off the real network."""
    getter = http_get or _default_http_get
    payload = getter(f"https://api.github.com/repos/{repo}")
    if "stargazers_count" not in payload:
        raise StarCadenceError(f"malformed GitHub API response: {payload!r}")
    return int(payload["stargazers_count"])


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
    default path and `StarCadenceError`, delegates the actual
    validate-and-write to the one shared implementation."""
    return time_utils.record_snapshot(count, ts, path, error_cls=StarCadenceError)


_parse_ts = time_utils.parse_ts


def _reject_malformed(snapshots: list[dict], caller: str) -> None:
    """Raise StarCadenceTamperedError if any snapshot line came back marked
    _malformed by load_snapshots(). Thin wrapper around
    time_utils.reject_malformed (task 563) -- keeps this module's own
    error class, delegates the actual walk-and-raise logic to the one
    shared implementation."""
    time_utils.reject_malformed(snapshots, caller, error_cls=StarCadenceTamperedError)


def star_count_at_or_before(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet — never guessed at, never interpolated."""
    _reject_malformed(snapshots, "star_count_at_or_before")
    best = None
    for s in snapshots:
        ts = _parse_ts(s["ts"])
        if ts <= when and (best is None or ts > _parse_ts(best["ts"])):
            best = s
    return best["count"] if best else None


def star_count_at_or_after(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. This is the grading-side counterpart
    to `star_count_at_or_before`: once a call's window closes, the honest
    outcome is the first real observation once the window is actually
    over, not a later one that could quietly wait for a friendlier
    number."""
    _reject_malformed(snapshots, "star_count_at_or_after")
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
    stargazers, plus the confidence sealed alongside it. Pure: reads
    `snapshots`/`now`/`current_count`, writes nothing, decides nothing
    about whether to seal it."""
    if now.tzinfo is None:
        raise StarCadenceError("now must be timezone-aware")
    # The claim's own target is rendered with a literal "Z" (UTC) suffix,
    # so `now` must actually be normalized to UTC first -- accepting any
    # aware timezone but never converting it silently mislabels the target
    # instant by the caller's UTC offset (a non-UTC `now` is a legal aware
    # datetime, but its wall-clock hour is not the UTC hour this claim
    # swears the target is). Mirrors `cadence.py`'s task-210 fix.
    now = now.astimezone(datetime.timezone.utc)
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise StarCadenceError("current_count must be a non-negative integer")
    if horizon_hours <= 0:
        raise StarCadenceError(
            "horizon_hours must be positive — a target at or before the sealing "
            "moment is not a prediction, it is hindsight"
        )
    baseline_when = now - datetime.timedelta(hours=horizon_hours)
    baseline = star_count_at_or_before(snapshots, baseline_when)
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
        f"stargazer count will be at least {threshold} "
        f"(currently {current_count}{change_clause})."
    )
    return {"claim": claim, "confidence": float(confidence)}


def seal_star_prediction(
    now: datetime.datetime,
    ts: str,
    current_count: int,
    actor: str = DEFAULT_ACTOR,
    snapshots: list[dict] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs,
) -> dict:
    """Build one star-cadence prediction and seal it. `now` and `ts` are
    always passed in by the caller, same discipline `cadence.py` and
    `oracle_engine.prediction` hold everywhere else in this desk."""
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
    _count = fetch_star_count()
    record_snapshot(_count, _ts)
    _entry = seal_star_prediction(now=_now, ts=_ts, current_count=_count)
    print(_entry["hash"])
