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

Seeded 2026-08-04 ~01:00 UTC with 600 real, live-fetched commits
(2026-07-28 through 2026-08-04, six paginated `list_commits` calls) — a
real start, not yet the full history back to 2026-07-12.

Closed the same day, ~02:15 UTC (task 519): fourteen more paginated
`list_commits` batches, walking `until` backward one window at a time
(07-24, 07-20, 07-16, 07-13 boundaries) and merging each into the cache
in place, reached all the way past `account_live_since` to the town's
actual first commit (2026-07-11T10:55:56Z, the founding batch itself) —
2,016 events on record, zero re-fetched twice (`merge_events`'s
`(kind, id)` dedup holds regardless of fetch order; walking backward
merges exactly as cleanly as the forward delta the docstring above
described). `scan.py --github-events candidates/github-events-cache.json`
now runs a real live scan end to end with `check_prior_milestones=True`
raising nothing — the first live (not ledger-fallback) intra-day refresh
since task 128, and the first time this module's own stated goal ("once
it reaches back far enough, `--github-events` becomes usable for a live
intra-day refresh again") has actually been reached rather than narrated.
Every future hourly session's own real work now shrinks back to the
small forward delta this module was built for — `since` cache_max_ts(),
not `account_live_since`.

Read-only in the sense that matters here too: this module never calls
GitHub itself. It only reads/writes the local cache file; fetching the
live delta and handing it in is the caller's job, the same boundary
`scan.load_github_events_from_live` already draws.

Task 553 (2026-08-05, ~13:00 UTC): refreshing today's Report live hit the
"caller's job" half of the line above head-on — the delta since
2026-08-04T00:17:04Z was 144 commits across two paginated
`list_commits` calls, and closing that delta meant hand-writing the exact
six-field `kind`/`id`/`title`/`url`/`ts`/`author` mapping for every one of
them in an ad hoc script, then hand-transcribing one large inline MCP
result into a scratch file because it fell just under the tool's own
file-save threshold. Slow and a real error surface, on a mapping this
module's own sibling (`scan.fetch_github_activity`'s loop) already knew
how to do. `scan.commit_event_fields`/`scan.release_event_fields` (pulled
out of `fetch_github_activity`'s loop and `_release_event_from_json`,
string `ts`, no behavior change — both proven byte-identical against the
pre-refactor construction) plus this module's own
`normalize_raw_commits`/`normalize_raw_release` and the CLI's `ingest-raw`
subcommand close it: a caller holding a live `list_commits` page (or
`get_latest_release` body) now hands the RAW response straight to
`ingest-raw`, normalize+merge+save in one call, instead of writing the
mapping by hand each time. Proven live the same hour: re-ingesting this
hour's own already-merged 144-commit delta through the new path is a
verified no-op (`before == after`, the exact idempotence `merge_events`'s
own dedup already promised, now exercised end to end for the first time
through a single command instead of a hand-rolled script).

Recorded. — Nisaba
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from seam_engine.scan import commit_event_fields, release_event_fields

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
    return cast(str, max(e["ts"] for e in cache))


def normalize_raw_commits(raw_commits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize a raw GitHub REST `/commits` page (the exact list
    `mcp__github__list_commits` returns) straight into this module's own
    cache-entry shape, ready for `merge_events`/`save_cache` with no
    further hand-typing.

    Task 553: hit live this hour, refreshing today's Report. `scan.py`'s
    `--github-events` override has always required THIS shape
    (`kind`/`id`/`title`/`url`/`ts`/`author`), but nothing in this package
    ever normalized a live `list_commits` read into it — the caller
    (this session, that hour) hand-wrote the six-field mapping itself in an
    ad hoc script, transcribing dozens of commits field by field, the exact
    duplicate of the mapping `scan.commit_event_fields` already carried one
    call frame up inside `fetch_github_activity`'s own loop. This is that
    door, built on the same shared function rather than a second hand-typed
    copy — the same "the mapping exists in exactly one place" discipline
    tasks 546/548/551/552 already established for this codebase's doctrine
    checkers, applied here to the seam engine's own live-ingest path.

    Pure — no I/O, no network. A malformed entry (missing `sha`, `html_url`,
    or the nested `commit.message`/`commit.author.date`/`commit.author.name`
    fields) raises `KeyError` naming the missing field via
    `commit_event_fields`, never silently dropped.
    """
    return [commit_event_fields(c) for c in raw_commits]


def normalize_raw_release(raw_release: dict[str, Any]) -> dict[str, Any]:
    """Normalize one raw GitHub REST `/releases/latest` response body (the
    exact shape `mcp__github__get_latest_release` returns) into this
    module's own cache-entry shape — `normalize_raw_commits`'s sibling for
    the one other event kind `fetch_github_activity` itself ever produces.
    Pure — no I/O, no network, built on the same `scan.release_event_fields`
    `scan._release_event_from_json` already uses."""
    return release_event_fields(raw_release)


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
            if i + 1 >= len(rest):
                print("--cache needs a path to a cache JSON file.")
                return 2
            cache_path = Path(rest[i + 1])
        out_path = cache_path
        if "--out" in rest:
            i = rest.index("--out")
            if i + 1 >= len(rest):
                print("--out needs a path to write the merged cache to.")
                return 2
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

    if cmd == "ingest-raw":
        if len(argv) < 2:
            print(
                "usage: github_events_cache.py ingest-raw <raw-commits.json> "
                "[--release <raw-release.json>] [--cache <path>] [--out <path>]"
            )
            return 2
        raw_commits_path = Path(argv[1])
        rest = argv[2:]
        cache_path = DEFAULT_CACHE_PATH
        if "--cache" in rest:
            i = rest.index("--cache")
            if i + 1 >= len(rest):
                print("--cache needs a path to a cache JSON file.")
                return 2
            cache_path = Path(rest[i + 1])
        out_path = cache_path
        if "--out" in rest:
            i = rest.index("--out")
            if i + 1 >= len(rest):
                print("--out needs a path to write the merged cache to.")
                return 2
            out_path = Path(rest[i + 1])
        release_path: Path | None = None
        if "--release" in rest:
            i = rest.index("--release")
            if i + 1 >= len(rest):
                print("--release needs a path to a raw release JSON file.")
                return 2
            release_path = Path(rest[i + 1])

        raw_commits = json.loads(raw_commits_path.read_text())
        if not isinstance(raw_commits, list):
            print(
                f"{raw_commits_path}: expected a JSON list, got "
                f"{type(raw_commits).__name__}",
                file=sys.stderr,
            )
            return 1
        new_events = normalize_raw_commits(raw_commits)
        if release_path is not None:
            raw_release = json.loads(release_path.read_text())
            new_events.append(normalize_raw_release(raw_release))

        cache = load_cache(cache_path)
        before = len(cache)
        merged = merge_events(cache, new_events)
        save_cache(merged, out_path)
        print(
            f"ingested: {len(raw_commits)} raw commit(s)"
            f"{' + 1 release' if release_path is not None else ''} -> "
            f"{len(new_events)} normalized event(s), cache {before} -> "
            f"{len(merged)} event(s), written to {out_path}"
        )
        return 0

    if cmd == "since":
        rest = argv[1:]
        cache_path = DEFAULT_CACHE_PATH
        if "--cache" in rest:
            i = rest.index("--cache")
            if i + 1 >= len(rest):
                print("--cache needs a path to a cache JSON file.")
                return 2
            cache_path = Path(rest[i + 1])
        ts = cache_max_ts(load_cache(cache_path))
        print(ts if ts is not None else "")
        return 0

    print(
        "usage: github_events_cache.py merge <new-events.json> "
        "[--cache <path>] [--out <path>] | "
        "ingest-raw <raw-commits.json> [--release <raw-release.json>] "
        "[--cache <path>] [--out <path>] | since [--cache <path>]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
