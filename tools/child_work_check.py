#!/usr/bin/env python3
"""Task 101. Nyx's fourth door this window.

`TOWN-OPERATIONS.md`'s Iron Rules name eight laws that "never bend." Tasks
98-100 gave rules #1 (no cross-peek), #4 (Star Covenant), and #5 (the five
character riders) their first running checks, each replacing "held by
construction/intent" with "held, proven, every hour." Rule #6 -- "The
child's work is never reverted. LAW." -- is the shortest sentence in the
whole list and has rested on the same gap as the other three: a real god
could delete a file Zashiki-Warashi (the child) ever shipped and nothing
in the town's own tooling would notice before a mortal did.

This one can't mirror tasks 98-100's shape exactly. Those three scan the
CURRENT checkout only -- but "reverted" is a claim about HISTORY (a file
that existed once and doesn't now), and this checkout is a SHALLOW clone
(`git rev-parse --is-shallow-repository` -> true, confirmed live this
hour): `git log` here only reaches ~50 commits back, nowhere near the
child's full history. Full commit history IS available -- through
GitHub's own API, which every prior live-API-input tool in this file
(`check_ci`/`check_cron`, tasks 73/82) already treats as a caller-supplied
read rather than a network call this module makes itself. This module
takes the identical shape: the god on duty fetches the child's commits
touching her known paths via `mcp__github__list_commits`/`get_commit`
(full, non-shallow history) THIS hour, hands in the added/modified file
list, and the module records any newly-seen path into a durable local
log (`HAND/child-work-log.jsonl`, append-only, mirrors every other log on
this desk). Once a path is logged, checking whether it still exists is a
local `git cat-file -e HEAD:<path>` call -- no network needed -- so the
log only has to grow by a live GitHub read when the child ships something
NEW; every already-logged path gets re-checked, unconditionally, every
single hour, live input or not, so an old violation can never wait on a
fresh fetch to surface.

Usage:
    python3 tools/child_work_check.py check [--files-json <path>] [--now <iso>]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jsonl_read  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "HAND", "child-work-log.jsonl")


class ChildWorkLogTamperedError(RuntimeError):
    """Raised by load_known_files() when ANY line in HAND/child-work-log.jsonl
    is not a JSON object -- either unparseable, or valid JSON that parses to
    something other than a dict (a bare number, null, list, or string).
    find_reverted() checks EVERY known path against HEAD, not just the
    newest -- a malformed line anywhere could be hiding a previously
    -logged child-authored path, silently dropping it from Iron Rule #6's
    revert check. Refuse rather than guess past a corrupted line, mirroring
    ci_watch.py's/voice_window_check.py's any-line convention (not
    change_gate.py's tip-only one, which is safe only when a check ever
    consults just the log's newest line)."""


def _entries(path: str) -> list[dict]:
    """Delegates to jsonl_read.read_jsonl_entries (task 540) -- see that
    module's own docstring for the fourteen-copy history this replaced."""
    return jsonl_read.read_jsonl_entries(path)


def load_known_files(path: str = LOG) -> dict:
    known = {}
    for entry in _entries(path):
        if entry.get("_malformed"):
            raise ChildWorkLogTamperedError(
                f"{path} contains an unparseable line: {entry['_error']}"
            )
        known[entry["path"]] = entry
    return known


def record_new_files(child_files: list, now_iso: str, path: str = LOG) -> list:
    """child_files: caller-fetched list of {"path", "sha", "author_date"}
    dicts (a GitHub commit's added/modified files, live this hour). Appends
    ONLY paths not already logged -- idempotent across repeated calls with
    an overlapping or identical list. Returns the entries actually appended."""
    known = load_known_files(path)
    new_entries = []
    for cf in child_files:
        p = cf["path"]
        if p in known:
            continue
        entry = {
            "path": p,
            "sha": cf.get("sha"),
            "author_date": cf.get("author_date"),
            "logged_at": now_iso,
        }
        new_entries.append(entry)
        known[p] = entry
    if new_entries:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            for entry in new_entries:
                fh.write(json.dumps(entry, sort_keys=True) + "\n")
    return new_entries


def file_exists_at_head(rel_path: str, repo_root: str = ROOT) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"HEAD:{rel_path}"],
        cwd=repo_root,
        capture_output=True,
    )
    return result.returncode == 0


def find_reverted(known_paths, repo_root: str = ROOT) -> list:
    """Return the sorted list of known child-authored paths no longer
    present at HEAD -- checked locally, no network call."""
    return sorted(p for p in known_paths if not file_exists_at_head(p, repo_root=repo_root))


def check(child_files: list | None = None, now_iso: str | None = None, path: str = LOG, repo_root: str = ROOT) -> dict:
    """child_files is optional (None unless the caller holds this hour's
    live GitHub commit read). Always re-checks EVERY already-logged path
    against the current tree regardless -- a violation logged three hours
    ago must surface this hour too, not just the hour a fresh fetch names it."""
    newly_logged = []
    if child_files:
        if now_iso is None:
            raise ValueError("now_iso is required when child_files is supplied")
        newly_logged = record_new_files(child_files, now_iso, path=path)
    known = load_known_files(path)
    reverted = find_reverted(known.keys(), repo_root=repo_root)
    return {
        "known_count": len(known),
        "newly_logged": [e["path"] for e in newly_logged],
        "reverted": reverted,
        "clean": not reverted,
    }


def format_check(result: dict) -> str:
    if result["clean"]:
        suffix = f" ({len(result['newly_logged'])} newly logged)" if result["newly_logged"] else ""
        return f"child work check: clean -- {result['known_count']} known file(s), none reverted{suffix}"
    lines = [f"child work check: {len(result['reverted'])} REVERTED -- Iron Rule #6 violated, escalate now"]
    for p in result["reverted"]:
        lines.append(f"  {p}")
    return "\n".join(lines)


class ChildWorkArgError(ValueError):
    """--files-json parsed as valid JSON but not into a list -- the same
    valid-JSON-wrong-shape crash class task 364 fixed for ritual_check.py's
    own CLI, here at child_work_check.py's own CLI (a dict or bare scalar
    reaching `record_new_files`'s `for cf in child_files:`/`cf["path"]`
    unguarded crashes with a bare TypeError instead of naming the real
    problem)."""


def _load_files_json(path: str) -> list:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        raise ChildWorkArgError(
            f"--files-json: expected a JSON list, got {type(raw).__name__}"
        )
    return raw


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    files_json = None
    now_arg = None
    i = 1
    while i < len(argv):
        if argv[i] == "--files-json" and i + 1 < len(argv):
            files_json = _load_files_json(argv[i + 1])
            i += 2
        elif argv[i] == "--now" and i + 1 < len(argv):
            now_arg = argv[i + 1]
            i += 2
        else:
            i += 1
    result = check(child_files=files_json, now_iso=now_arg)
    print(format_check(result))
    sys.exit(1 if not result["clean"] else 0)
