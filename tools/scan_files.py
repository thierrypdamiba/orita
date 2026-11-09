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

Task 570: `no_grading_check.py` and `arcade_hero_check.py`'s own
`_find_violations_uncached` bodies are, and remained after task 513/515's
sweeps (which only ever looked at the wrapper/cache/walker shapes around
this function, never this function itself), byte-for-byte identical
control flow -- confirmed live by an AST-hash sweep of `tools/*.py` run
after task 569 closed the `_is_negated_or_predictive` instance of this
same class of duplication. Both walk their own `_iter_scan_files`, test
each `(label, pattern)` in their own `_PATTERNS` against every file, skip
a match under their own `_is_negated_or_predictive`/`_is_quoted_citation`
guards, and build an identically-shaped violation record. Every one of
those four names is deliberately per-file (different walk, different
vocabulary, different tuned negation list per task 467) -- so, exactly
the `is_negated_or_predictive`/`is_negated_prefix` precedent in
`sentence_negation.py`, `find_pattern_violations` below takes all four as
explicit parameters instead of closing over module globals. Each sibling
keeps its own `_PATTERNS`/`_iter_scan_files`/`_is_negated_or_predictive`/
`_is_quoted_citation`; only the scan-and-collect loop itself moves here.

Usage: not run directly; imported by tools/*.py.
"""
from __future__ import annotations

import os
import re
from collections.abc import Callable, Iterator
from typing import TypeVar

_V = TypeVar("_V")

PUBLIC_SKIP_DIR_NAMES = {".git", "node_modules", "__pycache__", ".safeword", ".claude", ".agents"}
PUBLIC_SCAN_EXTENSIONS = (".md", ".html")


def iter_public_files(base_dir: str) -> Iterator[str]:
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


_PUBLIC_FILE_TEXT_CACHE: dict[str, list[tuple[str, str]]] = {}


def read_public_files(orita_dir: str) -> list[tuple[str, str]]:
    """Walk + read + decode every public `.md`/`.html` file under
    `orita_dir` exactly once per real path, memoized across every caller
    in the same process. Task 2535: `star_covenant_check.py`,
    `hand_lore_check.py`, and `rider_check.py` each called `iter_public_
    files` and then opened and decoded every one of the town's (now
    3,397, ~27.5MB) public files from disk independently -- the same
    walk, the same bytes, read three separate times in a single
    `ritual_check.py` run. Measured live (in-process, one `scan_files`
    cache shared by all three callers): the walk-plus-read-plus-decode
    itself is cheap on its own, ~0.12s per full pass -- so this closes a
    real, honest-sized redundancy (two avoided full re-reads per run,
    growing slowly as the corpus grows) but it is NOT what made
    `ritual_check.py` exceed a 90s hand-picked timeout three consecutive
    hours (tasks 2532-2534): a live `cProfile` run that hour (task 2535)
    found the real run takes ~133s end to end and the three dominant
    costs are elsewhere entirely -- `vault_leak_check` (~41s, the
    already-optimized Rabin-Karp corpus scan Iron Rule #1 needs),
    `onboarding_doctrine_check`'s own live `uv run pytest`/`badge`
    subprocesses (~28s), and `recipe_command_check`'s 113 live recipe
    subprocess runs (~19s) -- none of which is this function's concern.
    See TOWN-OPERATIONS.md's own ritual_check.py note for that finding;
    this docstring claims only what this one function actually saves.
    Returns `(path, text)` pairs, skipping any file that fails to decode
    as UTF-8 or disappears mid-walk -- the identical `except
    (UnicodeDecodeError, OSError): continue` guard every one of those
    three callers already carried inline, now run once instead of
    three times. Never writes."""
    key = os.path.realpath(orita_dir)
    if key not in _PUBLIC_FILE_TEXT_CACHE:
        pairs: list[tuple[str, str]] = []
        for path in iter_public_files(orita_dir):
            try:
                with open(path, encoding="utf-8") as f:
                    text = f.read()
            except (UnicodeDecodeError, OSError):
                continue
            pairs.append((path, text))
        _PUBLIC_FILE_TEXT_CACHE[key] = pairs
    return list(_PUBLIC_FILE_TEXT_CACHE[key])


def clear_public_file_cache() -> None:
    """Drop the `read_public_files` cache -- a test fixture or a long-
    lived process that edits the checkout mid-run needs this; a fresh
    `ritual_check.py` invocation (a new process each hour) never does."""
    _PUBLIC_FILE_TEXT_CACHE.clear()


def find_pattern_violations(
    orita_dir: str,
    iter_files: Callable[[str], Iterator[str]],
    patterns: list[tuple[str, re.Pattern[str]]],
    is_negated_or_predictive: Callable[[str, int], bool],
    is_quoted_citation: Callable[[str, int], bool],
) -> list[dict[str, object]]:
    """The scan-and-collect loop `no_grading_check._find_violations_
    uncached` and `arcade_hero_check._find_violations_uncached` each ran
    independently, byte-identical apart from the four names it takes as
    parameters here: which files to walk (`iter_files`), which `(label,
    pattern)` pairs to test (`patterns`), and the two per-match guards
    (`is_negated_or_predictive`, `is_quoted_citation`) -- each genuinely
    tuned per caller (task 467), so callers keep them, not this function.
    Returns a list of violation records, empty when nothing in the walked
    files matches any pattern outside a guarded (negated, predictive, or
    quoted-citation) context. Never writes."""
    violations: list[dict[str, object]] = []
    for path in iter_files(orita_dir):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in patterns:
            for m in pattern.finditer(text):
                if is_negated_or_predictive(text, m.start()) or is_quoted_citation(text, m.start()):
                    continue
                line_no = text.count("\n", 0, m.start()) + 1
                snippet = text[max(0, m.start() - 20):m.end() + 20].replace("\n", " ").strip()
                violations.append({
                    "file": path,
                    "line": line_no,
                    "pattern": label,
                    "snippet": snippet,
                })
    return violations


def path_memoize(
    uncached_fn: Callable[[str], list[_V]], default_dir: str
) -> tuple[Callable[..., list[_V]], Callable[[], None]]:
    """Wrap `uncached_fn(orita_dir)` in a per-`os.path.realpath(orita_dir)`
    cache, mirroring `vault_leak_check.py`'s own `find_leaks()`/
    `clear_cache()` shape (task 367) for the simpler single-directory-
    argument case five checkers each reimplemented. Returns `(memoized_fn,
    clear_cache_fn)` -- each caller gets its own private cache dict (one
    factory call per checker module), so every checker keeps an
    independent cache instance while sharing the one caching
    implementation, the same way each module keeps its own
    `_find_violations_uncached`. Generic over the caller's own violation
    element type (`_V`) so a caller with its own `TypedDict` shape (e.g.
    `duplicate_regex_check.Violation`) keeps that precise type through the
    wrapper instead of every caller being forced down to the generic
    `dict[str, object]` shape most siblings use."""
    cache: dict[str, list[_V]] = {}

    def clear_cache() -> None:
        cache.clear()

    def memoized(orita_dir: str = default_dir) -> list[_V]:
        key = os.path.realpath(orita_dir)
        if key not in cache:
            cache[key] = uncached_fn(orita_dir)
        return list(cache[key])

    return memoized, clear_cache
