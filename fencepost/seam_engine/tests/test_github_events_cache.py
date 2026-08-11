"""Tests for the incremental GitHub-events cache (github_events_cache.py).

Three invariants, all load-bearing:

1. `merge_events` deduplicates by `(kind, id)` and never loses an entry
   from either side — a delta fetch merged into an existing cache grows
   it, never shrinks or silently drops history.
2. A malformed entry (missing a required key) is named in the raised
   error, on both the cache-load side and the new-events side — never
   silently dropped, the same discipline `scan.load_github_events_from_live`
   already holds for the shape this module produces input for.
3. The CLI's `merge` command round-trips through real files exactly the
   way an hourly session would use it: read the on-disk cache, merge in a
   freshly-fetched delta, write the result back.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from seam_engine import github_events_cache as gec

COMMIT_A = {
    "kind": "commit",
    "id": "aaaaaaa",
    "title": "Task 1: first thing",
    "url": "https://github.com/thierrypdamiba/orita/commit/aaaaaaa",
    "ts": "2026-07-28T21:19:38Z",
    "author": "Off-By-One",
}
COMMIT_B = {
    "kind": "commit",
    "id": "bbbbbbb",
    "title": "Task 2: second thing",
    "url": "https://github.com/thierrypdamiba/orita/commit/bbbbbbb",
    "ts": "2026-07-29T10:00:00Z",
    "author": "Nisaba",
}
COMMIT_C = {
    "kind": "commit",
    "id": "ccccccc",
    "title": "Task 3: third thing",
    "url": "https://github.com/thierrypdamiba/orita/commit/ccccccc",
    "ts": "2026-08-04T00:17:04Z",
    "author": "Zashiki-Warashi",
}


def test_load_cache_missing_file_returns_empty(tmp_path: Path) -> None:
    assert gec.load_cache(tmp_path / "nope.json") == []


def test_load_cache_reads_back_what_save_cache_wrote(tmp_path: Path) -> None:
    path = tmp_path / "cache.json"
    gec.save_cache([COMMIT_B, COMMIT_A], path)
    loaded = gec.load_cache(path)
    assert loaded == [COMMIT_A, COMMIT_B]  # oldest first, regardless of input order


def test_load_cache_non_list_json_raises_named_error(tmp_path: Path) -> None:
    path = tmp_path / "cache.json"
    path.write_text(json.dumps({"not": "a list"}))
    with pytest.raises(gec.MalformedCacheEntryError, match="expected a JSON list"):
        gec.load_cache(path)


def test_load_cache_entry_missing_key_names_it(tmp_path: Path) -> None:
    path = tmp_path / "cache.json"
    broken = dict(COMMIT_A)
    del broken["author"]
    path.write_text(json.dumps([broken]))
    with pytest.raises(gec.MalformedCacheEntryError, match=r"\['author'\]"):
        gec.load_cache(path)


def test_merge_events_unions_and_sorts_oldest_first() -> None:
    merged = gec.merge_events([COMMIT_C, COMMIT_A], [COMMIT_B])
    assert [e["id"] for e in merged] == ["aaaaaaa", "bbbbbbb", "ccccccc"]


def test_merge_events_deduplicates_by_kind_and_id() -> None:
    stale_copy = dict(COMMIT_A, title="a title that would be wrong to prefer")
    merged = gec.merge_events([COMMIT_A], [stale_copy, COMMIT_B])
    ids = [e["id"] for e in merged]
    assert ids == ["aaaaaaa", "bbbbbbb"]
    assert ids.count("aaaaaaa") == 1
    # The cache's own copy wins on a duplicate id -- never silently
    # replaced by whatever a later fetch happens to hand in.
    assert merged[0]["title"] == COMMIT_A["title"]


def test_merge_events_new_entry_missing_key_names_it() -> None:
    broken = dict(COMMIT_A)
    del broken["ts"]
    with pytest.raises(gec.MalformedCacheEntryError, match=r"\['ts'\]"):
        gec.merge_events([], [broken])


def test_merge_events_empty_new_events_is_a_no_op() -> None:
    assert gec.merge_events([COMMIT_A, COMMIT_B], []) == [COMMIT_A, COMMIT_B]


def test_cache_max_ts_empty_cache_is_none() -> None:
    assert gec.cache_max_ts([]) is None


def test_cache_max_ts_returns_the_newest_timestamp() -> None:
    assert gec.cache_max_ts([COMMIT_A, COMMIT_C, COMMIT_B]) == COMMIT_C["ts"]


def test_cli_merge_round_trips_through_real_files(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    gec.save_cache([COMMIT_A], cache_path)
    new_events_path = tmp_path / "delta.json"
    new_events_path.write_text(json.dumps([COMMIT_B, COMMIT_C]))

    rc = gec.main(["merge", str(new_events_path), "--cache", str(cache_path)])

    assert rc == 0
    merged = gec.load_cache(cache_path)
    assert [e["id"] for e in merged] == ["aaaaaaa", "bbbbbbb", "ccccccc"]


def test_cli_merge_out_leaves_cache_file_untouched(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    out_path = tmp_path / "merged.json"
    gec.save_cache([COMMIT_A], cache_path)
    new_events_path = tmp_path / "delta.json"
    new_events_path.write_text(json.dumps([COMMIT_B]))

    rc = gec.main([
        "merge", str(new_events_path),
        "--cache", str(cache_path),
        "--out", str(out_path),
    ])

    assert rc == 0
    assert [e["id"] for e in gec.load_cache(cache_path)] == ["aaaaaaa"]
    assert [e["id"] for e in gec.load_cache(out_path)] == ["aaaaaaa", "bbbbbbb"]


def test_cli_merge_new_events_not_a_list_fails_named(tmp_path: Path, capsys) -> None:
    new_events_path = tmp_path / "delta.json"
    new_events_path.write_text(json.dumps({"oops": True}))

    rc = gec.main(["merge", str(new_events_path), "--cache", str(tmp_path / "c.json")])

    assert rc == 1
    assert "expected a JSON list" in capsys.readouterr().err


def test_cli_merge_trailing_cache_flag_prints_usage_and_fails(tmp_path: Path, capsys) -> None:
    new_events_path = tmp_path / "delta.json"
    new_events_path.write_text(json.dumps([COMMIT_A]))

    rc = gec.main(["merge", str(new_events_path), "--cache"])

    assert rc == 2
    assert "--cache needs a path" in capsys.readouterr().out


def test_cli_merge_trailing_out_flag_prints_usage_and_fails(tmp_path: Path, capsys) -> None:
    new_events_path = tmp_path / "delta.json"
    new_events_path.write_text(json.dumps([COMMIT_A]))

    rc = gec.main(["merge", str(new_events_path), "--out"])

    assert rc == 2
    assert "--out needs a path" in capsys.readouterr().out


def test_cli_since_prints_newest_ts(tmp_path: Path, capsys) -> None:
    cache_path = tmp_path / "cache.json"
    gec.save_cache([COMMIT_A, COMMIT_B], cache_path)

    rc = gec.main(["since", "--cache", str(cache_path)])

    assert rc == 0
    assert capsys.readouterr().out.strip() == COMMIT_B["ts"]


def test_cli_since_empty_cache_prints_nothing(tmp_path: Path, capsys) -> None:
    rc = gec.main(["since", "--cache", str(tmp_path / "missing.json")])
    assert rc == 0
    assert capsys.readouterr().out.strip() == ""


def test_cli_since_trailing_cache_flag_prints_usage_and_fails(capsys) -> None:
    rc = gec.main(["since", "--cache"])
    assert rc == 2
    assert "--cache needs a path" in capsys.readouterr().out


def test_cli_no_command_prints_usage_and_fails(capsys) -> None:
    rc = gec.main([])
    assert rc == 2
    assert "usage:" in capsys.readouterr().err


def test_default_cache_path_lives_under_candidates() -> None:
    assert gec.DEFAULT_CACHE_PATH.parent.name == "candidates"
    assert gec.DEFAULT_CACHE_PATH.name == "github-events-cache.json"


RAW_COMMIT = {
    "sha": "ddddddd1234567890abcdef1234567890abcdef",
    "commit": {
        "message": "Task 553: ingest-raw closes the hand-typed gap\n\nbody",
        "author": {"name": "Nisaba", "date": "2026-08-05T13:00:00Z"},
    },
    "html_url": "https://github.com/thierrypdamiba/orita/commit/ddddddd1234567890abcdef1234567890abcdef",
}

RAW_RELEASE = {
    "tag_name": "episode-001",
    "name": "Episode 1 — The Founding",
    "html_url": "https://github.com/thierrypdamiba/orita/releases/tag/episode-001",
    "published_at": "2026-07-11T10:58:26Z",
    "author": {"login": "thierrypdamiba"},
}


def test_normalize_raw_commits_produces_cache_ready_dicts() -> None:
    normalized = gec.normalize_raw_commits([RAW_COMMIT])
    assert normalized == [{
        "kind": "commit",
        "id": "ddddddd",
        "title": "Task 553: ingest-raw closes the hand-typed gap",
        "url": RAW_COMMIT["html_url"],
        "ts": "2026-08-05T13:00:00Z",
        "author": "Nisaba",
    }]
    # The output is directly mergeable -- no further hand-typing.
    merged = gec.merge_events([], normalized)
    assert merged == normalized


def test_normalize_raw_commits_empty_list_is_a_no_op() -> None:
    assert gec.normalize_raw_commits([]) == []


def test_normalize_raw_release_produces_a_cache_ready_dict() -> None:
    normalized = gec.normalize_raw_release(RAW_RELEASE)
    assert normalized == {
        "kind": "release",
        "id": "episode-001",
        "title": "Episode 1 — The Founding",
        "url": RAW_RELEASE["html_url"],
        "ts": "2026-07-11T10:58:26Z",
        "author": "thierrypdamiba",
    }


def test_cli_ingest_raw_round_trips_through_real_files(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    gec.save_cache([COMMIT_A], cache_path)
    raw_commits_path = tmp_path / "raw-commits.json"
    raw_commits_path.write_text(json.dumps([RAW_COMMIT]))

    rc = gec.main([
        "ingest-raw", str(raw_commits_path),
        "--cache", str(cache_path),
    ])

    assert rc == 0
    merged = gec.load_cache(cache_path)
    assert [e["id"] for e in merged] == ["aaaaaaa", "ddddddd"]


def test_cli_ingest_raw_with_release_flag_adds_both_events(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    raw_commits_path = tmp_path / "raw-commits.json"
    raw_commits_path.write_text(json.dumps([RAW_COMMIT]))
    raw_release_path = tmp_path / "raw-release.json"
    raw_release_path.write_text(json.dumps(RAW_RELEASE))

    rc = gec.main([
        "ingest-raw", str(raw_commits_path),
        "--release", str(raw_release_path),
        "--cache", str(cache_path),
    ])

    assert rc == 0
    merged = gec.load_cache(cache_path)
    kinds = {e["kind"] for e in merged}
    assert kinds == {"commit", "release"}
    assert len(merged) == 2


def test_cli_ingest_raw_is_idempotent_on_replay(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    raw_commits_path = tmp_path / "raw-commits.json"
    raw_commits_path.write_text(json.dumps([RAW_COMMIT]))

    gec.main(["ingest-raw", str(raw_commits_path), "--cache", str(cache_path)])
    first = gec.load_cache(cache_path)
    gec.main(["ingest-raw", str(raw_commits_path), "--cache", str(cache_path)])
    second = gec.load_cache(cache_path)

    assert first == second  # replaying the same raw page merges to a no-op


def test_cli_ingest_raw_not_a_list_fails_named(tmp_path: Path, capsys) -> None:
    raw_commits_path = tmp_path / "raw-commits.json"
    raw_commits_path.write_text(json.dumps({"oops": True}))

    rc = gec.main([
        "ingest-raw", str(raw_commits_path),
        "--cache", str(tmp_path / "c.json"),
    ])

    assert rc == 1
    assert "expected a JSON list" in capsys.readouterr().err


def test_cli_ingest_raw_no_path_prints_usage(capsys) -> None:
    rc = gec.main(["ingest-raw"])
    assert rc == 2
    assert "usage:" in capsys.readouterr().out


def test_cli_ingest_raw_trailing_cache_flag_prints_usage_and_fails(
    tmp_path: Path, capsys
) -> None:
    raw_commits_path = tmp_path / "raw-commits.json"
    raw_commits_path.write_text(json.dumps([RAW_COMMIT]))

    rc = gec.main(["ingest-raw", str(raw_commits_path), "--cache"])

    assert rc == 2
    assert "--cache needs a path" in capsys.readouterr().out


def test_cli_ingest_raw_trailing_out_flag_prints_usage_and_fails(
    tmp_path: Path, capsys
) -> None:
    raw_commits_path = tmp_path / "raw-commits.json"
    raw_commits_path.write_text(json.dumps([RAW_COMMIT]))

    rc = gec.main(["ingest-raw", str(raw_commits_path), "--out"])

    assert rc == 2
    assert "--out needs a path" in capsys.readouterr().out


def test_cli_ingest_raw_trailing_release_flag_prints_usage_and_fails(
    tmp_path: Path, capsys
) -> None:
    raw_commits_path = tmp_path / "raw-commits.json"
    raw_commits_path.write_text(json.dumps([RAW_COMMIT]))

    rc = gec.main(["ingest-raw", str(raw_commits_path), "--release"])

    assert rc == 2
    assert "--release needs a path" in capsys.readouterr().out


def test_seeded_cache_is_real_and_scan_compatible_shape() -> None:
    """The real seed committed this hour (600 live-fetched commits,
    2026-07-28 through 2026-08-04) round-trips through `load_cache` and
    every entry carries the exact six keys
    `scan.load_github_events_from_live` requires."""
    cache = gec.load_cache()
    assert len(cache) >= 600
    for entry in cache:
        assert set(gec._REQUIRED_KEYS) <= set(entry.keys())
    ids = [e["id"] for e in cache]
    assert len(ids) == len(set(ids)) or len({(e["kind"], e["id"]) for e in cache}) == len(cache)
