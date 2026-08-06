"""The Oracle Desk's twenty-fourth real cadence: a checkable claim about
the town's own public GitHub issue (and issue-thread) comment count.
(ROADMAP #77)

Task 76 read `GET /repos/{owner}/{repo}/pulls/comments` -- every
line-anchored PR REVIEW comment across the repo -- and its own note named
the endpoint it deliberately left standing: `/issues/comments`, "general
conversation, not line-anchored review." On GitHub's REST API, every
issue AND every pull-request thread shares this one comments collection,
so this module counts something task 76 structurally cannot: a reply to
Off-By-One's issue #1, an answer in the Open Door (#3/#5), the free-form
back-and-forth of the square itself, not just a remark on a specific
diff line. Same public, unauthenticated GitHub REST API family task 38
already cleared; zero new Arcade tool, zero new scope, no per-user
account.

Structurally this mirrors `comment_cadence.py`/`branch_cadence.py` line
for line on purpose -- one shape reused a twenty-fourth time is the point,
not a missed chance to unify. This run lands inside 00:00-06:00 UTC,
Nyx's and the child's shared window (`TOWN-OPERATIONS.md`'s WINDOW rule);
Zashiki-Warashi sealed the last two single-endpoint claims in this window
(tasks 67, 75) and is the house awake to seal a third.
"""
from __future__ import annotations

import datetime
import os
from types import ModuleType

from oracle_engine import github_auth, prediction, time_utils

_ORACLE_ENGINE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
_ORACLE_ROOT = os.path.join(_ORACLE_ENGINE_ROOT, "..")
DEFAULT_SNAPSHOT_PATH = os.path.normpath(os.path.join(_ORACLE_ROOT, "issue_comment_snapshots.jsonl"))

DEFAULT_REPO = "thierrypdamiba/orita"
DEFAULT_HORIZON_HOURS = 336  # two weeks -- matches task 76's rarity assumption
DEFAULT_CONFIDENCE = 0.5
DEFAULT_ACTOR = "zashiki-warashi"
_MAX_PAGES = 20  # 20 * 100 = 2000 comments, far beyond any plausible count; a hard stop, not a guess


class IssueCommentCadenceError(ValueError):
    """The issue-comment-cadence read or the prediction it produced is not
    well-formed."""


class IssueCommentCadenceTamperedError(RuntimeError):
    """Raised by issue_comment_count_at_or_before/issue_comment_count_at_or_after
    when the snapshot log holds a malformed line anywhere in it. Mirrors
    branch_cadence.py's/collaborator_cadence.py's/comment_cadence.py's
    /commit_cadence.py's/commit_comment_cadence.py's/contributor_cadence.py's
    /deployment_cadence.py's/follower_cadence.py's/following_cadence.py's
    /fork_cadence.py's/issue_cadence.py's BranchCadenceTamperedError
    /CollaboratorCadenceTamperedError/CommentCadenceTamperedError
    /CommitCadenceTamperedError/CommitCommentCadenceTamperedError
    /ContributorCadenceTamperedError/DeploymentCadenceTamperedError
    /FollowerCadenceTamperedError/FollowingCadenceTamperedError
    /ForkCadenceTamperedError/IssueCadenceTamperedError (tasks 250-260): both
    lookup functions walk EVERY snapshot looking for the closest one
    before/after `when`, not just the tip, so a malformed line anywhere
    could be hiding the real closest snapshot and silently skipping it
    would misreport the delta/baseline. Refuse rather than guess -- repair
    the log before the next real call."""


_default_http_get = github_auth.default_http_get


def fetch_issue_comment_count(repo: str = DEFAULT_REPO, http_get=None) -> int:
    """The repo's PUBLIC, unauthenticated issue-and-PR-thread comment count
    off the GitHub REST API's `issues/comments` collection -- read-only by
    nature, no account, no OAuth, no toolkit. Like `comment_cadence.
    fetch_comment_count`, this endpoint returns a paginated LIST, not a
    single count field, so this function pages through it rather than
    trusting one response is everything. Same pluggable `http_get` shape
    every other cadence uses, kept off the real network in tests."""
    getter = http_get or _default_http_get
    total = 0
    for page in range(1, _MAX_PAGES + 1):
        payload = getter(f"https://api.github.com/repos/{repo}/issues/comments?per_page=100&page={page}")
        if not isinstance(payload, list):
            raise IssueCommentCadenceError(f"malformed GitHub API response: {payload!r}")
        total += len(payload)
        if len(payload) < 100:
            return total
    raise IssueCommentCadenceError(f"issue-comment count exceeded the {_MAX_PAGES}-page safety cap")


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
    default path and `IssueCommentCadenceError`, delegates the actual
    validate-and-write to the one shared implementation."""
    return time_utils.record_snapshot(count, ts, path, error_cls=IssueCommentCadenceError)


_parse_ts = time_utils.parse_ts


def _reject_malformed(snapshots: list[dict], caller: str) -> None:
    """Raise IssueCommentCadenceTamperedError if any snapshot line came back marked
    _malformed by load_snapshots(). Thin wrapper around
    time_utils.reject_malformed (task 563) -- keeps this module's own
    error class, delegates the actual walk-and-raise logic to the one
    shared implementation."""
    time_utils.reject_malformed(snapshots, caller, error_cls=IssueCommentCadenceTamperedError)


def issue_comment_count_at_or_before(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet -- never guessed at, never
    interpolated. Thin wrapper: this module's own `_reject_malformed`
    still gets first say (so a malformed line raises this module's own
    `*CadenceTamperedError`, not a shared-module exception), then the
    actual scan-and-compare delegates to `time_utils.count_at_or_before`
    (task 578)."""
    _reject_malformed(snapshots, "issue_comment_count_at_or_before")
    return time_utils.count_at_or_before(snapshots, when)


def issue_comment_count_at_or_after(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. The grading-side counterpart to
    `issue_comment_count_at_or_before`: once a call's window closes, the honest
    outcome is the first real observation once the window is actually
    over, not a later one that could quietly wait for a friendlier
    number. Thin wrapper around `time_utils.count_at_or_after` (task 578),
    same shape as `issue_comment_count_at_or_before` above."""
    _reject_malformed(snapshots, "issue_comment_count_at_or_after")
    return time_utils.count_at_or_after(snapshots, when)


def build_prediction(
    now: datetime.datetime,
    snapshots: list[dict],
    current_count: int,
    horizon_hours: int = DEFAULT_HORIZON_HOURS,
    confidence: float = DEFAULT_CONFIDENCE,
) -> dict:
    """One checkable claim about the town's own next window of public
    issue-and-PR-thread comments, plus the confidence sealed alongside it.
    Pure: reads `snapshots`/`now`/`current_count`, writes nothing, decides
    nothing about whether to seal it."""
    if now.tzinfo is None:
        raise IssueCommentCadenceError("now must be timezone-aware")
    now = now.astimezone(datetime.timezone.utc)
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise IssueCommentCadenceError("current_count must be a non-negative integer")
    if horizon_hours <= 0:
        raise IssueCommentCadenceError(
            "horizon_hours must be positive — a target at or before the sealing "
            "moment is not a prediction, it is hindsight"
        )
    baseline_when = now - datetime.timedelta(hours=horizon_hours)
    baseline = issue_comment_count_at_or_before(snapshots, baseline_when)
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
        f"issue and pull-request thread comment count will be at least {threshold} "
        f"(currently {current_count}{change_clause})."
    )
    return {"claim": claim, "confidence": float(confidence)}


def seal_issue_comment_prediction(
    now: datetime.datetime,
    ts: str,
    current_count: int,
    actor: str = DEFAULT_ACTOR,
    snapshots: list[dict] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs,
) -> dict:
    """Build one issue_comment-cadence prediction and seal it. Thin wrapper around
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
    _count = fetch_issue_comment_count()
    record_snapshot(_count, _ts)
    _entry = seal_issue_comment_prediction(now=_now, ts=_ts, current_count=_count)
    print(_entry["hash"])
