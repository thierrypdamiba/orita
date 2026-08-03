#!/usr/bin/env python3
"""Task 513. The public-file walk and the per-path memoization wrapper five
checkers each carried a private, byte-identical copy of.

`no_grading_check.py`, `hand_lore_check.py`, `star_covenant_check.py`,
`arcade_hero_check.py`, and `rider_check.py` each defined their own
`find_violations()`/`clear_cache()` pair wrapping a private `_VIOLATIONS_
CACHE` dict keyed on `os.path.realpath(orita_dir)` -- byte-identical
boilerplate in all five, invisible to `tools/duplicate_regex_check.py`
(which only ever inspects `re.compile()` call sites, never duplicated
function bodies). The exact same shape tasks 508/509/510 already closed
elsewhere (`metrics_reader.py`, six duplicated readers; `iso_time.py`,
three duplicated parsers; `jsonl_append.py`, ten duplicated appenders).
Found live by an AST-hash sweep of every `tools/*.py` function body this
hour (hashing name+body together, so it only caught same-named
duplicates) -- three of the five (`hand_lore_check.py`,
`star_covenant_check.py`, `rider_check.py`) also carried a byte-identical
`_iter_public_files(base_dir)` walking the same `_SKIP_DIR_NAMES`/
`_SCAN_EXTENSIONS` pair. `arcade_hero_check.py` carries the identical body
under a different name (`_iter_scan_files`), invisible to a name-sensitive
hash for that reason alone but confirmed byte-for-byte identical by direct
diff. `no_grading_check.py`'s own `_iter_scan_files` adds one real extra
condition (recipe filenames) and stays a genuine one-off, not folded in
here.

Consolidated here as the one place both shapes are defined. Every sibling
check now imports `iter_public_files`/`path_memoize` from this module
instead of carrying its own copy; `tests/test_scan_files.py` asserts each
sibling holds the identical function object (not just identical source),
so a future edit to one is an edit to all by construction -- the same
guarantee `metrics_reader.py`/`iso_time.py`/`jsonl_append.py` give theirs.

Task 515: `duplicate_regex_check.py` and `escape_sequence_check.py` each
carried the identical `find_violations()`/`clear_cache()`/`_VIOLATIONS_
CACHE` shape too -- missed by task 513's own AST-hash sweep because that
sweep only compared same-named functions, and both of these still hashed
identically to each other's copy (not to the other five, whose docstrings
and surrounding code differed enough to change the hash of the wrapper
functions themselves in a naive whole-body hash) so they simply weren't
in the batch that got checked against the newly-created `scan_files.py`
that same hour. A second sweep this hour re-ran the exact same AST-hash
method with no time pressure to stop early and caught both. Now seven
siblings share `path_memoize`, not five. `site_link_check.py` carries the
same visible shape but keys its cache on a `(docs_dir, require_index)`
tuple, not a bare `orita_dir` -- `path_memoize`'s single-argument contract
doesn't fit it, so it stays a genuine one-off, the same call task 513 made
for `no_grading_check.py`'s own `_iter_scan_files`.

Usage: not run directly; imported by tools/*.py.
"""
from __future__ import annotations

import os

PUBLIC_SKIP_DIR_NAMES = {".git", "node_modules", "__pycache__", ".safeword", ".claude", ".agents"}
PUBLIC_SCAN_EXTENSIONS = (".md", ".html")


def iter_public_files(base_dir: str):
    """Yield every `.md`/`.html` file under `base_dir`, skipping the
    standard non-content directories. The read-only walk five checkers
    shared verbatim (three under this exact name, one under
    `_iter_scan_files`)."""
    if not os.path.isdir(base_dir):
        return
    for dirpath, dirnames, filenames in os.walk(base_dir):
        dirnames[:] = [d for d in dirnames if d not in PUBLIC_SKIP_DIR_NAMES]
        for name in filenames:
            if name.endswith(PUBLIC_SCAN_EXTENSIONS):
                yield os.path.join(dirpath, name)


def path_memoize(uncached_fn, default_dir: str):
    """Wrap `uncached_fn(orita_dir)` in a per-`os.path.realpath(orita_dir)`
    cache, mirroring `vault_leak_check.py`'s own `find_leaks()`/
    `clear_cache()` shape (task 367) for the simpler single-directory-
    argument case five checkers each reimplemented. Returns `(memoized_fn,
    clear_cache_fn)` -- each caller gets its own private cache dict (one
    factory call per checker module), so every checker keeps an
    independent cache instance while sharing the one caching
    implementation, the same way each module keeps its own
    `_find_violations_uncached`."""
    cache: dict = {}

    def clear_cache() -> None:
        cache.clear()

    def memoized(orita_dir: str = default_dir) -> list:
        key = os.path.realpath(orita_dir)
        if key not in cache:
            cache[key] = uncached_fn(orita_dir)
        return list(cache[key])

    return memoized, clear_cache
