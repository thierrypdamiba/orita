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
import os
from types import ModuleType
from typing import Any, Callable

from oracle_engine import github_auth, prediction, time_utils

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


class CommitCommentCadenceTamperedError(RuntimeError):
    """Raised by commit_comment_count_at_or_before/commit_comment_count_at_or_after
    when the snapshot log holds a malformed line anywhere in it. Mirrors
    branch_cadence.py's/collaborator_cadence.py's/comment_cadence.py's
    /commit_cadence.py's BranchCadenceTamperedError/CollaboratorCadenceTamperedError
    /CommentCadenceTamperedError/CommitCadenceTamperedError (tasks 250-253):
    both lookup functions walk EVERY snapshot looking for the closest one
    before/after `when`, not just the tip, so a malformed line anywhere
    could be hiding the real closest snapshot and silently skipping it
    would misreport the delta/baseline. Refuse rather than guess -- repair
    the log before the next real call."""


_default_http_get = github_auth.default_http_get


def fetch_commit_comment_count(repo: str = DEFAULT_REPO, http_get: Callable[[str], Any] | None = None) -> int:
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


def load_snapshots(path: str = DEFAULT_SNAPSHOT_PATH) -> list[dict[str, object]]:
    """This module's own default-path wrapper around the shared
    time_utils.load_snapshots (task 523). Kept here rather than a bare name
    rebinding (unlike _parse_ts = time_utils.parse_ts) because every
    sibling's DEFAULT_SNAPSHOT_PATH differs and this module's own
    load_snapshots() call sites below rely on that default -- but the
    actual read-and-mark-malformed logic lives in exactly one place now,
    not twenty-five."""
    return time_utils.load_snapshots(path)


def record_snapshot(count: int, ts: str, path: str = DEFAULT_SNAPSHOT_PATH) -> dict[str, object]:
    """Append one `{"ts", "count"}` snapshot. Thin wrapper around
    `time_utils.record_snapshot` (task 559) — keeps this module's own
    default path and `CommitCommentCadenceError`, delegates the actual
    validate-and-write to the one shared implementation."""
    return time_utils.record_snapshot(count, ts, path, error_cls=CommitCommentCadenceError)


_parse_ts = time_utils.parse_ts


def _reject_malformed(snapshots: list[dict[str, object]], caller: str) -> None:
    """Raise CommitCommentCadenceTamperedError if any snapshot line came back marked
    _malformed by load_snapshots(). Thin wrapper around
    time_utils.reject_malformed (task 563) -- keeps this module's own
    error class, delegates the actual walk-and-raise logic to the one
    shared implementation."""
    time_utils.reject_malformed(snapshots, caller, error_cls=CommitCommentCadenceTamperedError)


def commit_comment_count_at_or_before(snapshots: list[dict[str, object]], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet -- never guessed at, never
    interpolated. Thin wrapper: this module's own `_reject_malformed`
    still gets first say (so a malformed line raises this module's own
    `*CadenceTamperedError`, not a shared-module exception), then the
    actual scan-and-compare delegates to `time_utils.count_at_or_before`
    (task 578)."""
    _reject_malformed(snapshots, "commit_comment_count_at_or_before")
    return time_utils.count_at_or_before(snapshots, when)


def commit_comment_count_at_or_after(snapshots: list[dict[str, object]], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. The grading-side counterpart to
    `commit_comment_count_at_or_before`: once a call's window closes, the honest
    outcome is the first real observation once the window is actually
    over, not a later one that could quietly wait for a friendlier
    number. Thin wrapper around `time_utils.count_at_or_after` (task 578),
    same shape as `commit_comment_count_at_or_before` above."""
    _reject_malformed(snapshots, "commit_comment_count_at_or_after")
    return time_utils.count_at_or_after(snapshots, when)


def build_prediction(
    now: datetime.datetime,
    snapshots: list[dict[str, object]],
    current_count: int,
    horizon_hours: int = DEFAULT_HORIZON_HOURS,
    confidence: float = DEFAULT_CONFIDENCE,
) -> dict[str, object]:
    """One checkable claim about the town's own next window of public
    commit comments, plus the confidence sealed alongside it. Pure: reads
    `snapshots`/`now`/`current_count`, writes nothing, decides nothing
    about whether to seal it."""
    if now.tzinfo is None:
        raise CommitCommentCadenceError("now must be timezone-aware")
    now = now.astimezone(datetime.timezone.utc)
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise CommitCommentCadenceError("current_count must be a non-negative integer")
    if horizon_hours <= 0:
        raise CommitCommentCadenceError(
            "horizon_hours must be positive — a target at or before the sealing "
            "moment is not a prediction, it is hindsight"
        )
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
    snapshots: list[dict[str, object]] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs: object,
) -> dict[str, object]:
    """Build one commit_comment-cadence prediction and seal it. Thin wrapper around
    `prediction.seal_generic_prediction` (task 573) -- keeps this module's
    own `build_prediction`/`load_snapshots`/`DEFAULT_ACTOR`, delegates the
    actual seal-and-copylint glue to the one shared implementation."""
    return prediction.seal_generic_prediction(
        build_prediction,
        load_snapshots,
        now=now,
        ts=ts,
        current_count=current_count,
        actor=actor,
        snapshots=snapshots,
        ledger_module=ledger_module,
        **build_kwargs,
    )


if __name__ == "__main__":
    _now = datetime.datetime.now(datetime.timezone.utc)
    _ts = _now.isoformat(timespec="seconds")
    _count = fetch_commit_comment_count()
    record_snapshot(_count, _ts)
    _entry = seal_commit_comment_prediction(now=_now, ts=_ts, current_count=_count)
    print(_entry["hash"])
