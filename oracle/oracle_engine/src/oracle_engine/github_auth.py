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
"""
from __future__ import annotations

import os


def github_headers(accept: str = "application/vnd.github+json") -> dict:
    """Accept header always; bearer Authorization added only if a GitHub
    token is present in the environment (`GITHUB_TOKEN`, GitHub Actions'
    own name for it, checked first; `GH_TOKEN`, the `gh` CLI's name for the
    same credential, as a fallback for non-Actions runs)."""
    headers = {"Accept": accept}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
