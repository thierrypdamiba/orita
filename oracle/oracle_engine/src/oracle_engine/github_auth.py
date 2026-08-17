"""Shared GitHub REST auth header for every cadence module's `_default_http_get`.

Every one of tasks 38-60's cadence sources reads a PUBLIC, unauthenticated
GitHub REST endpoint on purpose (no new Arcade tool, no new scope, no
per-user account — the whole point of a repo-object/list-endpoint cadence).
Unauthenticated GitHub reads share one shallow bucket: 60 requests/hour per
source IP, not per repo and not per module. `seam-scan.yml`'s 2026-07-14T13:39Z
run hit exactly that ceiling (`403 rate limit exceeded` fetching
`/repos/.../commits`) — the first CI failure either scheduled workflow has
ever had, and every cadence module here makes the identical class of call on
the identical shared runner IP within the same job.

`GITHUB_TOKEN` (GitHub Actions' own auto-issued token, already scoped
`contents: write` for both workflows' commit steps) raises that ceiling to
5,000/hour when sent as a bearer credential — and doing so changes nothing
about what these modules DO: every call stays a GET against a public,
read-only endpoint; the token authenticates the *rate limit bucket*, not a
new capability. `oracle/SCOPES.md`'s read-only oath is about what tools this
agent's config can invoke, not about whether a GET request identifies
itself — sending a token to avoid an anonymous-tier ceiling is not a scope
expansion.

Outside CI (this sandbox, a contributor's laptop) `GITHUB_TOKEN` is usually
unset, so `github_headers()` degrades to the original unauthenticated header
— every existing test and every prior real cadence seal already exercised
that path and keeps working unchanged.

This module's own docstring has claimed since task 63 to be shared "for
every cadence module's `_default_http_get`" — but only `github_headers()`
ever actually was; each of twenty cadence modules still carried its own
byte-identical `_default_http_get(url)` wrapper around it (confirmed by an
AST-hash sweep: same import order, same `httpx.get(...)` call, same
`raise_for_status()`/`.json()` tail, differing only in a cosmetic `-> dict`
vs `-> list` return annotation that Python never enforces at runtime).
Twenty-six modules (the twenty above, plus `autograde.py`, `follower_
cadence.py`, `following_cadence.py`, `listed_cadence.py`, `media_cadence.py`,
and `tweet_cadence.py`) carried a second, unrelated byte-identical copy of
`_parse_ts` for good measure — consolidated into `time_utils.parse_ts`
instead, the same task, the same AST-hash method `tools/iso_time.py` (task
509) and `tools/metrics_reader.py` (task 508) already used one directory
over. `default_http_get` below finally makes this module's own docstring
true: every sibling now points `_default_http_get` at this one function
object (`tests/test_github_auth.py` asserts identity, not source equality),
so a future fix here is a fix everywhere at once, the guarantee the
docstring already promised and never quite kept.

Task 823: `oracle-cadence.yml`'s 2026-08-17T13:34Z run died mid-job —
`collaborator_cadence.fetch_collaborator_count` hit a bare `503 Service
Unavailable` from `api.github.com/.../collaborators` (a transient upstream
hiccup, GitHub's own status, nothing wrong with the request) and this
function had no retry, so `raise_for_status()` propagated straight up and
took the *whole* scheduled job down with it — every cadence step after
collaborator's in that one long `the-call` job (star, fork, issue, and
their grades) never ran that day, not just the one call that hit the 5xx.
Twenty-six modules share this one function, so the fix belongs here once:
retry a handful of times with short exponential backoff, but ONLY on 5xx
(the server's own fault, plausibly gone on the next try) — a 4xx (404, or
403 rate-limit) is retried zero times, since retrying an unauthorized or
not-found request is not an existing-request problem, it just spends the
job's wall-clock for the identical failure. `sleep` is an injected
dependency (defaults to `time.sleep`) so the retry path is exercised under
test without a real test suite ever actually pausing.
"""
from __future__ import annotations

import os
import time
from typing import Any, Callable

_MAX_ATTEMPTS = 3
_RETRY_BASE_DELAY_SECONDS = 0.5


def github_headers(accept: str = "application/vnd.github+json") -> dict[str, str]:
    """Accept header always; bearer Authorization added only if a GitHub
    token is present in the environment (`GITHUB_TOKEN`, GitHub Actions'
    own name for it, checked first; `GH_TOKEN`, the `gh` CLI's name for the
    same credential, as a fallback for non-Actions runs)."""
    headers = {"Accept": accept}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def default_http_get(url: str, sleep: Callable[[float], None] = time.sleep) -> Any:
    """The real network call every cadence module's `fetch_*` falls back to
    when no `http_get` override is given (every existing test always
    injects one, so this body itself has never been under direct test —
    same boundary the twenty prior private copies shared). `httpx` is
    imported lazily, matching every sibling's own prior copy, so importing
    this module for `github_headers()` alone — already done everywhere —
    never requires `httpx` to be installed.

    Retries up to `_MAX_ATTEMPTS` times, but only on a 5xx response (GitHub's
    own fault, plausibly transient — task 823's real `503`) with exponential
    backoff between attempts. A 4xx is raised immediately, unretried: it is
    the request that is wrong (bad auth, not found, rate-limited), and
    trying the identical request again wastes the caller's wall-clock for
    the identical failure."""
    import httpx

    for attempt in range(_MAX_ATTEMPTS):
        try:
            resp = httpx.get(url, headers=github_headers(), timeout=10.0)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            is_last_attempt = attempt == _MAX_ATTEMPTS - 1
            if exc.response.status_code < 500 or is_last_attempt:
                raise
            sleep(_RETRY_BASE_DELAY_SECONDS * (2**attempt))
    raise AssertionError("unreachable: loop always returns or raises")
