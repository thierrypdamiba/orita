"""Incremental cache for the seam engine's live GitHub-events override.

Problem, hit live during an hourly ritual run (2026-08-04, ~01:00 UTC):
`run_scan(..., check_prior_milestones=True)` — the mode every real caller
actually uses (`seam-scan.yml`'s cron, and `scan.py --github-events`'s own
CLI docstring) — requires the `github_events` override, when supplied, to
cover the FULL window back to `account_live_since` (the town's founding
date, 2026-07-12; see `scan._effective_since`'s `min(rolling,
account_live_since)`). That is by design (`check_prior_milestones` exists
precisely so a thinner live fetch can never silently under-report a
previously-sealed, still-open gap) — but it means a single hourly
session's `--github-events` file must hold literally every commit since
founding, not just what changed since the last hour.

Task 128 (2026-07-18, six days after founding) proved the live-override
mechanism works, fetching the town's real commit history through the
already-authorized `github` MCP channel in one session. Re-attempted live
this hour, the same approach hits a wall the six-day-old town never did:
one paginated `list_commits` call (100 results, minimal fields) covering
only 2026-08-03 to 2026-08-04 already fills a whole page — the full
2026-07-12-to-now window is on the order of 2,000+ commits, tens of
paginated MCP calls, more than one routine hourly session should spend
just assembling one scan's input.

The fix is not to weaken `check_prior_milestones` (Ogun's law: a thinner
report than the Ledger already knows is real is exactly the failure mode
that gate exists to prevent) — it is to stop re-fetching the same old
history every hour. This module is a small, dumb, on-disk cache of
already-fetched, already-normalized `GithubEvent`-shaped dicts
(`fencepost/candidates/github-events-cache.json`, committed so the saving
carries across sessions): each hourly session fetches only the DELTA since
the cache's own newest timestamp (`cache_max_ts`), merges it in
(`merge_events`, deduplicated by `(kind, id)`), and hands the full merged
cache to `scan.py --github-events`. The cache grows by one small delta
fetch per session instead of being rebuilt from `account_live_since` every
time; once it reaches back far enough, `--github-events` becomes usable
for a live intra-day refresh again, the same way it was at task 128.

Seeded this hour with 600 real, live-fetched commits (2026-07-28 through
2026-08-04, six paginated `list_commits` calls) — a real start, not yet
the full history back to 2026-07-12. Closing that remaining gap is exactly
what this module is for: a few more hourly sessions each fetching one more
delta closes it incrementally, never by inventing history.

Read-only in the sense that matters here too: this module never calls
GitHub itself. It only reads/writes the local cache file; fetching the
live delta and handing it in is the caller's job, the same boundary
`scan.load_github_events_from_live` already draws.

Recorded. — Off-By-One
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# fencepost/  (…/fencepost/seam_engine/src/seam_engine/github_events_cache.py -> parents[3])
_FENCEPOST_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_CACHE_PATH = _FENCEPOST_ROOT / "candidates" / "github-events-cache.json"

_REQUIRED_KEYS = ("kind", "id", "title", "url", "ts", "author")


class MalformedCacheEntryError(ValueError):
    """Raised when a cache (or incoming) entry is missing a required key —
    named, never silently dropped, per Ogun's precision-over-recall law
    every other loader in this package already holds."""


def _validate(entry: dict[str, Any], *, where: str) -> dict[str, Any]:
    missing = [k for k in _REQUIRED_KEYS if k not in entry]
    if missing:
        raise MalformedCacheEntryError(
            f"{where}: entry is missing required key(s) {missing}: {entry!r}"
        )
    return entry


def load_cache(path: Path = DEFAULT_CACHE_PATH) -> list[dict[str, Any]]:
    """Every event the cache has ever recorded, oldest first. An empty list
    if the cache file doesn't exist yet — a fresh cache is a normal start
    state, not a malformed one."""
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    if not isinstance(raw, list):
        raise MalformedCacheEntryError(
            f"{path}: expected a JSON list, got {type(raw).__name__}"
        )
    return [_validate(e, where=f"{path} entry {i}") for i, e in enumerate(raw)]


def merge_events(
    cache: list[dict[str, Any]], new_events: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Union `cache` and `new_events`, deduplicated by `(kind, id)` — a
    commit's sha and a release's tag never change once minted, so the
    first copy seen of a given id is as good as any later one; this simply
    keeps exactly one. Returns oldest-first by `ts` (string ISO-8601
    timestamps sort correctly as plain strings, the same convention every
    other `ts`-bearing store in this package already relies on), so
    `cache_max_ts` and any caller that wants "most recent" can just look
    at the last entry.

    Pure — reads two lists, returns a third. Never writes a file itself
    (`save_cache` is the one place that touches disk on the write side,
    the same load/compute/save separation `ledger.py`/`streak.py` already
    hold).
    """
    for i, e in enumerate(new_events):
        _validate(e, where=f"new_events entry {i}")
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for e in cache:
        by_key[(e["kind"], e["id"])] = e
    for e in new_events:
        by_key.setdefault((e["kind"], e["id"]), e)
    return sorted(by_key.values(), key=lambda e: e["ts"])


def save_cache(events: list[dict[str, Any]], path: Path = DEFAULT_CACHE_PATH) -> None:
    """Write the cache, oldest-first, pretty enough for a human diff to
    read in a PR — the same discipline `candidates/<date>.json` already
    gets from `scan.py`'s own CLI (`json.dumps(..., indent=2)`)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(events, key=lambda e: e["ts"])
    path.write_text(json.dumps(ordered, indent=2) + "\n", encoding="utf-8")


def cache_max_ts(cache: list[dict[str, Any]]) -> str | None:
    """The newest timestamp already in the cache, or None if it's empty —
    the `since` a caller's next live delta fetch should use, so the next
    session only asks GitHub for what this one doesn't already have."""
    if not cache:
        return None
    return max(e["ts"] for e in cache)


# --- CLI ---------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else None

    if cmd == "merge":
        if len(argv) < 2:
            print(
                "usage: github_events_cache.py merge <new-events.json> "
                "[--cache <path>] [--out <path>]"
            )
            return 2
        new_events_path = Path(argv[1])
        rest = argv[2:]
        cache_path = DEFAULT_CACHE_PATH
        if "--cache" in rest:
            i = rest.index("--cache")
            cache_path = Path(rest[i + 1])
        out_path = cache_path
        if "--out" in rest:
            i = rest.index("--out")
            out_path = Path(rest[i + 1])
        new_events = json.loads(new_events_path.read_text())
        if not isinstance(new_events, list):
            print(
                f"{new_events_path}: expected a JSON list, got "
                f"{type(new_events).__name__}",
                file=sys.stderr,
            )
            return 1
        cache = load_cache(cache_path)
        before = len(cache)
        merged = merge_events(cache, new_events)
        save_cache(merged, out_path)
        print(
            f"merged: {before} -> {len(merged)} event(s) (from "
            f"{len(new_events)} new), written to {out_path}"
        )
        return 0

    if cmd == "since":
        rest = argv[1:]
        cache_path = DEFAULT_CACHE_PATH
        if "--cache" in rest:
            i = rest.index("--cache")
            cache_path = Path(rest[i + 1])
        ts = cache_max_ts(load_cache(cache_path))
        print(ts if ts is not None else "")
        return 0

    print(
        "usage: github_events_cache.py merge <new-events.json> "
        "[--cache <path>] [--out <path>] | since [--cache <path>]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
