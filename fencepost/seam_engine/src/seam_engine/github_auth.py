"""Shared GitHub REST auth header for `scan.py`'s `fetch_github_activity`.

Unauthenticated GitHub REST reads share one shallow bucket: 60 requests/hour
per source IP, not per repo. `seam-scan.yml`'s 2026-07-14T13:39Z run hit
exactly that ceiling (`403 rate limit exceeded` fetching `/repos/.../commits`)
-- the first failure this scheduled workflow has ever had.

`GITHUB_TOKEN` (GitHub Actions' own auto-issued token, already scoped
`contents: write` for this workflow's commit step) raises that ceiling to
5,000/hour when sent as a bearer credential. Sending it changes nothing
about what `fetch_github_activity` does -- every call stays a GET against a
public, read-only endpoint (SCOPES.md's read-only oath); the token
authenticates the *rate-limit bucket*, not a new capability.

Outside CI (this sandbox, a contributor's laptop) `GITHUB_TOKEN` is usually
unset, so `github_headers()` degrades to the original unauthenticated
header -- the existing test suite's fixtures keep working unchanged.
"""
from __future__ import annotations

import os


def github_headers(accept: str = "application/vnd.github+json") -> dict:
    """Accept + User-Agent always; bearer Authorization added only if a
    GitHub token is present in the environment (`GITHUB_TOKEN`, GitHub
    Actions' own name for it, checked first; `GH_TOKEN`, the `gh` CLI's
    name for the same credential, as a fallback for non-Actions runs)."""
    headers = {"Accept": accept, "User-Agent": "fencepost-seam-scan"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
