"""The Oracle Desk's twenty-first real cadence: a checkable claim about the
town's own public GitHub deployment count. (ROADMAP #68)

Every prior GitHub-sourced cadence read a trace of activity, a taxonomy
entry, or a machine-room total (stars, forks, contributors, branches,
commits, subscribers, tags, labels, topics, pulls, workflows, milestones).
None of them asked the one question closest to what a mortal visitor
actually sees: has the site itself ever gone live. `pages.yml` (task 8)
publishes the Gap Ledger site on every push that touches `docs/`, and each
successful publish registers as a GitHub Deployment against the
`github-pages` environment — a real, public, unauthenticated collection
(`GET /repos/{owner}/{repo}/deployments`) the desk has not touched before
(the repo object confirmed dry at task 41/53; `X_WhoAmI`'s `public_metrics`
payload fully read after task 46; `/contributors` at 47; `/branches` at 48;
`/commits` at 49; `/subscribers` at 50; `/tags` at 51; `/labels` at 52;
`/pulls` at 54; `/actions/workflows` at 60; `/milestones` at 67). This
exercises no scope beyond what task 38 already cleared: no credential, no
OAuth, no toolkit, just another free public collection, paginated
defensively same as `contributor_cadence.py`/`branch_cadence.py`. A
deployment either fires or it doesn't, the same binary shape Retrya's own
~3% Tithe roll already lives inside — she stakes this one.

Structurally this mirrors `branch_cadence.py`/`contributor_cadence.py` line
for line on purpose — twenty-one independent cadence sources sharing one
shape is the point, not a missed chance to unify them into one module. A
future twenty-second source should be able to copy this file's shape again
without reading any of the other twenty first.
"""
from __future__ import annotations

import datetime
import os
from types import ModuleType

from oracle_engine import github_auth, prediction, time_utils

_ORACLE_ENGINE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
_ORACLE_ROOT = os.path.join(_ORACLE_ENGINE_ROOT, "..")
DEFAULT_SNAPSHOT_PATH = os.path.normpath(os.path.join(_ORACLE_ROOT, "deployment_snapshots.jsonl"))

DEFAULT_REPO = "thierrypdamiba/orita"
DEFAULT_HORIZON_HOURS = 336  # two weeks — matches every other GitHub-list cadence's horizon
DEFAULT_CONFIDENCE = 0.5
DEFAULT_ACTOR = "retrya"
_MAX_PAGES = 20  # 20 * 100 = 2000 deployments, far beyond any plausible count; a hard stop, not a guess


class DeploymentCadenceError(ValueError):
    """The deployment-cadence read or the prediction it produced is not
    well-formed."""


class DeploymentCadenceTamperedError(RuntimeError):
    """Raised by deployment_count_at_or_before/deployment_count_at_or_after
    when the snapshot log holds a malformed line anywhere in it. Mirrors
    branch_cadence.py's/collaborator_cadence.py's/comment_cadence.py's
    /commit_cadence.py's/commit_comment_cadence.py's/contributor_cadence.py's
    BranchCadenceTamperedError/CollaboratorCadenceTamperedError
    /CommentCadenceTamperedError/CommitCadenceTamperedError
    /CommitCommentCadenceTamperedError/ContributorCadenceTamperedError
    (tasks 250-255): both lookup functions walk EVERY snapshot looking for
    the closest one before/after `when`, not just the tip, so a malformed
    line anywhere could be hiding the real closest snapshot and silently
    skipping it would misreport the delta/baseline. Refuse rather than
    guess -- repair the log before the next real call."""


_default_http_get = github_auth.default_http_get


def fetch_deployment_count(repo: str = DEFAULT_REPO, http_get=None) -> int:
    """The repo's PUBLIC, unauthenticated deployment count off the GitHub
    REST API's deployments collection — read-only by nature, no account,
    no OAuth, no toolkit. Like `contributor_cadence.fetch_contributor_count`
    and `branch_cadence.fetch_branch_count`, this endpoint returns a
    paginated LIST, not a single count field, so this function pages
    through it rather than trusting one response is everything. Same
    pluggable `http_get` shape every other cadence uses, kept off the real
    network in tests."""
    getter = http_get or _default_http_get
    total = 0
    for page in range(1, _MAX_PAGES + 1):
        payload = getter(f"https://api.github.com/repos/{repo}/deployments?per_page=100&page={page}")
        if not isinstance(payload, list):
            raise DeploymentCadenceError(f"malformed GitHub API response: {payload!r}")
        total += len(payload)
        if len(payload) < 100:
            return total
    raise DeploymentCadenceError(f"deployment count exceeded the {_MAX_PAGES}-page safety cap")


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
    default path and `DeploymentCadenceError`, delegates the actual
    validate-and-write to the one shared implementation."""
    return time_utils.record_snapshot(count, ts, path, error_cls=DeploymentCadenceError)


_parse_ts = time_utils.parse_ts


def _reject_malformed(snapshots: list[dict], caller: str) -> None:
    """Raise DeploymentCadenceTamperedError if any snapshot line came back marked
    _malformed by load_snapshots(). Thin wrapper around
    time_utils.reject_malformed (task 563) -- keeps this module's own
    error class, delegates the actual walk-and-raise logic to the one
    shared implementation."""
    time_utils.reject_malformed(snapshots, caller, error_cls=DeploymentCadenceTamperedError)


def deployment_count_at_or_before(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The most recently recorded count at or before `when`; `None` if no
    snapshot that early exists yet -- never guessed at, never
    interpolated. Thin wrapper: this module's own `_reject_malformed`
    still gets first say (so a malformed line raises this module's own
    `*CadenceTamperedError`, not a shared-module exception), then the
    actual scan-and-compare delegates to `time_utils.count_at_or_before`
    (task 578)."""
    _reject_malformed(snapshots, "deployment_count_at_or_before")
    return time_utils.count_at_or_before(snapshots, when)


def deployment_count_at_or_after(snapshots: list[dict], when: datetime.datetime) -> int | None:
    """The EARLIEST recorded count at or after `when`; `None` if no
    snapshot that late has landed yet. The grading-side counterpart to
    `deployment_count_at_or_before`: once a call's window closes, the honest
    outcome is the first real observation once the window is actually
    over, not a later one that could quietly wait for a friendlier
    number. Thin wrapper around `time_utils.count_at_or_after` (task 578),
    same shape as `deployment_count_at_or_before` above."""
    _reject_malformed(snapshots, "deployment_count_at_or_after")
    return time_utils.count_at_or_after(snapshots, when)


def build_prediction(
    now: datetime.datetime,
    snapshots: list[dict],
    current_count: int,
    horizon_hours: int = DEFAULT_HORIZON_HOURS,
    confidence: float = DEFAULT_CONFIDENCE,
) -> dict:
    """One checkable claim about the town's own next window of public
    deployments, plus the confidence sealed alongside it. Pure: reads
    `snapshots`/`now`/`current_count`, writes nothing, decides nothing
    about whether to seal it."""
    if now.tzinfo is None:
        raise DeploymentCadenceError("now must be timezone-aware")
    now = now.astimezone(datetime.timezone.utc)
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise DeploymentCadenceError("current_count must be a non-negative integer")
    if horizon_hours <= 0:
        raise DeploymentCadenceError(
            "horizon_hours must be positive — a target at or before the sealing "
            "moment is not a prediction, it is hindsight"
        )
    baseline_when = now - datetime.timedelta(hours=horizon_hours)
    baseline = deployment_count_at_or_before(snapshots, baseline_when)
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
        f"deployment count will be at least {threshold} "
        f"(currently {current_count}{change_clause})."
    )
    return {"claim": claim, "confidence": float(confidence)}


def seal_deployment_prediction(
    now: datetime.datetime,
    ts: str,
    current_count: int,
    actor: str = DEFAULT_ACTOR,
    snapshots: list[dict] | None = None,
    ledger_module: ModuleType | None = None,
    **build_kwargs,
) -> dict:
    """Build one deployment-cadence prediction and seal it. Thin wrapper around
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
    _count = fetch_deployment_count()
    record_snapshot(_count, _ts)
    _entry = seal_deployment_prediction(now=_now, ts=_ts, current_count=_count)
    print(_entry["hash"])
