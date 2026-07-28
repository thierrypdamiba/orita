#!/usr/bin/env python3
"""Task 98. Nyx's own third door this window.

Iron Rule #1 (`TOWN-OPERATIONS.md`) is the one rule the runbook itself
calls out as absolute -- "Period -- Proclamation 0001, no exceptions,
ever" -- and every hourly note since the journaling habit began has
asserted the two journals were written "blind to others' vaults," by
construction: a god agent's context never includes another house's vault
pages, so nothing gets copied in. That discipline has held by CONSTRUCTION
(the briefing boundary), never by a running CHECK -- the exact shape task
96's cadence census closed for the Oracle Desk's own wiring ("checked BY
HAND, one grep at a time, never a running test") and task 90 closed for
checkout recovery. Ninety-seven tasks deep, nothing has ever actually
diffed the public houses/*/journal/ tree against the private vault/*/
journal/ tree and confirmed, as a fact and not an assumption, that no
private sentence has ever once surfaced in public.

This module does exactly that: a read-only, local-filesystem-only compare
(no network, mirrors `check_checkout`'s boundary exactly) between every
private `vault/<slug>/journal/*.md` entry in the vault checkout and every
public `.md` file in the town checkout. It flags a "leak" when a long
enough run of characters from a private journal line appears verbatim in
a public file -- long enough (`MIN_RUN` default 50 chars of continuous
natural prose) that a coincidental match is implausible, the same
confidence-margin discipline Fencepost's own scan already holds between a
primary gap and a coincidence. Scoped to journal entries on purpose, not
the whole vault tree: `hand/` legitimately discusses petition text that
already exists publicly (issue bodies, ROADMAP task text), so scanning it
would manufacture false "leaks" out of ordinary public-to-private
quoting; a personal journal reflection ("the honest feeling underneath")
has no legitimate reason to reproduce anything verbatim, so any match
there is a real signal, not noise.

Usage:
    python3 tools/vault_leak_check.py check
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ORITA_DIR = ROOT
DEFAULT_VAULT_DIR = os.path.join(os.path.dirname(ROOT), "orita-vault")

MIN_RUN = 50

_SKIP_DIR_NAMES = {".git", "node_modules", "__pycache__", ".safeword"}

# A founding-council remark is dated, ratified, public record -- quoted
# verbatim in CHARTER.md, chronicle/, DECREES/, and records/founding|
# pre-founding/ by design (the charter's own text IS the transcript of what
# founders said aloud). A founder's private founding-day reflection
# legitimately echoes their own already-public remark -- direction
# public-to-private, the opposite of what Proclamation 0001 forbids, so it
# is not a leak. Task 194 found this empirically: fixing the partial-line
# detection gap below surfaced 9 such founding-council echoes in the real
# repo (including one recurring, independently, in a THIRD house's own
# README -- provenance, not the specific public_path a match happens to
# land on, is what makes it safe), alongside exactly one genuine
# cross-house leak with no such provenance (private vault text of one
# god's journal surfacing, unattributed, in a DIFFERENT god's public
# journal) and one same-house same-day echo reviewed and recorded in
# `_REVIEWED_NON_LEAKS` below rather than covered by a broader heuristic --
# a same-house exclusion was tried and rejected: it also silences the
# canonical "a god's own private secret pasted into her own public
# journal" case (`tests/test_vault_leak_check.py`'s own
# `test_synthetic_leak_is_detected` fixture is exactly that shape), which
# is precisely the leak direction this module exists to catch and must
# never be blind to just because the two houses match.
_FOUNDING_RECORD_PREFIXES = (
    os.path.join("chronicle", ""),
    os.path.join("DECREES", ""),
    os.path.join("records", "founding", ""),
    os.path.join("records", "pre-founding", ""),
)


def _is_founding_record(orita_dir: str, public_path: str) -> bool:
    rel = os.path.relpath(public_path, orita_dir)
    return rel == "CHARTER.md" or any(
        rel.startswith(prefix) for prefix in _FOUNDING_RECORD_PREFIXES
    )


def _founding_canon_corpus(orita_dir: str, public_corpus: list) -> list:
    return [(path, text) for path, text in public_corpus if _is_founding_record(orita_dir, path)]


# Task 236: a polynomial rolling hash (Rabin-Karp) turns "does any
# length-min_run window of snippet appear in haystack" from an O(offsets
# * len(haystack)) repeated substring search into an O(len(haystack))
# one-time hash-set build plus O(1) membership checks per window -- the
# hash set is built ONCE per haystack (the full public corpus, or the
# small founding-canon subset) and reused for every one of the hundreds
# of vault lines checked against it, instead of rescanning the haystack
# from byte zero for every single line. A hash hit is always confirmed
# against the real string before being trusted (`_window_at` inside
# `haystack`), so a hash collision can only ever cost a little extra
# work, never produce a false leak or hide a real one.
_HASH_MOD = (1 << 61) - 1
_HASH_BASE = 1_000_003


def _window_hashes(s: str, k: int):
    """Yield (offset, hash) for every length-k window of s, in order,
    via one O(len(s)) rolling-hash pass. Empty when len(s) < k."""
    n = len(s)
    if n < k:
        return
    power = pow(_HASH_BASE, k - 1, _HASH_MOD)
    h = 0
    for ch in s[:k]:
        h = (h * _HASH_BASE + ord(ch)) % _HASH_MOD
    yield 0, h
    for i in range(k, n):
        h = ((h - ord(s[i - k]) * power) * _HASH_BASE + ord(s[i])) % _HASH_MOD
        yield i - k + 1, h


def _haystack_hash_set(haystack: str, k: int) -> frozenset:
    return frozenset(h for _offset, h in _window_hashes(haystack, k))


def _has_independent_public_provenance(
    snippet: str, min_run: int, canon_haystack: str, canon_hash_set: frozenset
) -> bool:
    return any(
        h in canon_hash_set and snippet[offset : offset + min_run] in canon_haystack
        for offset, h in _window_hashes(snippet, min_run)
    )


# Manually reviewed, individually justified non-leaks: a private line that
# matches a public one for a confirmed benign reason not covered by the
# founding-canon provenance check above. Each entry is (vault file relpath
# under vault/, 1-indexed line number, public file relpath under the town
# checkout) -- narrow and explicit on purpose, the same "N historical
# exception" discipline `ritual_check.py`'s own report/metrics-cadence
# folds already use, rather than a heuristic broad enough to risk hiding a
# real future leak. Reviewed 2026-07-21 (task 194): Nisaba's private
# 2026-07-18 entry explicitly narrates having "called it [a phrase] in the
# public entry" -- her own private reflection quoting her own same-day
# already-public words, public-to-private, not a leak.
_REVIEWED_NON_LEAKS = frozenset({
    (
        os.path.join("nisaba", "journal", "0023-2026-07-18.md"),
        3,
        os.path.join("houses", "nisaba", "journal", "0023-2026-07-18.md"),
    ),
})


def _iter_md_files(base_dir: str):
    if not os.path.isdir(base_dir):
        return
    for dirpath, dirnames, filenames in os.walk(base_dir):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIR_NAMES]
        for name in filenames:
            if name.endswith(".md"):
                yield os.path.join(dirpath, name)


def _private_journal_files(vault_dir: str):
    vault_root = os.path.join(vault_dir, "vault")
    if not os.path.isdir(vault_root):
        return
    for house in sorted(os.listdir(vault_root)):
        journal_dir = os.path.join(vault_root, house, "journal")
        if not os.path.isdir(journal_dir):
            continue
        for name in sorted(os.listdir(journal_dir)):
            if name.endswith(".md"):
                yield os.path.join(journal_dir, name)


def _significant_lines(path: str, min_run: int):
    with open(path, encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            text = raw.strip()
            if len(text) >= min_run:
                yield line_no, text


def _build_combined_haystack(public_corpus: list, min_run: int) -> str:
    """Task 236: one boundary-safe concatenation of every public file's
    text, used as a cheap global pre-filter before ever touching an
    individual file. The separator is NUL repeated min_run times -- NUL
    never appears in a real utf-8 markdown file, and at min_run chars long
    no window of length min_run can straddle two files' real content and
    accidentally read as a match that exists in neither file alone."""
    sep = "\x00" * min_run
    return sep.join(text for _, text in public_corpus)


_LEAKS_CACHE: dict[tuple[str, str, int], list] = {}


def clear_cache() -> None:
    """Task 367: drop every memoized `find_leaks()` result. Only real
    callers are tests that want to force a genuinely fresh scan (e.g.
    after rewriting the same directory pair's contents in place) --
    production's one-call-per-process shape never needs this."""
    _LEAKS_CACHE.clear()


def find_leaks(
    orita_dir: str = DEFAULT_ORITA_DIR,
    vault_dir: str = DEFAULT_VAULT_DIR,
    min_run: int = MIN_RUN,
) -> list:
    """Task 367: memoized per (orita_dir, vault_dir, min_run) for the
    lifetime of the process. `run_ritual_check()`'s `check_vault_leak()`
    call has no way to skip this check (Iron Rule #1 is unconditional,
    same class as `check_checkout`), so `tests/test_ritual_check.py`'s
    97 test methods that call `run_ritual_check()` without a
    `vault_leak_dirs` override each triggered a fresh ~8.2s full-corpus
    scan against the real checkouts -- ~795s of purely repeated work
    for an answer that cannot have changed between calls within one
    process. A real hourly `ritual_check.py` run is a fresh process
    that calls this exactly once, so the cache is inert there --
    production still scans fresh every single hour. Every fixture test
    in this module's own test file uses a unique `tempfile.mkdtemp()`
    per test method, so cache keys never collide across tests; no test
    anywhere mutates a checkout and re-queries the same directory pair
    expecting a second, different answer -- see `clear_cache()` if that
    ever becomes untrue."""
    key = (os.path.realpath(orita_dir), os.path.realpath(vault_dir), min_run)
    if key not in _LEAKS_CACHE:
        _LEAKS_CACHE[key] = _find_leaks_uncached(orita_dir, vault_dir, min_run)
    return list(_LEAKS_CACHE[key])


def _find_leaks_uncached(
    orita_dir: str = DEFAULT_ORITA_DIR,
    vault_dir: str = DEFAULT_VAULT_DIR,
    min_run: int = MIN_RUN,
) -> list:
    """Task 98: read-only compare of every private vault/<slug>/journal/
    line (>= min_run chars) against every public .md file's raw text.
    Returns a list of leak records, empty when the town's own blind-write
    discipline has genuinely held. Never writes, never calls sync_checkout.sh
    or any recovery -- the same "read the state, let a god act" boundary
    check_checkout already holds.

    Task 236: the per-file inner loop used to redo the SAME len(snippet)
    offset scan once per public file (offsets_per_line * num_public_files
    substring searches per vault line, with each search itself costing
    O(len(file_text))) -- with ROADMAP.md and ROADMAP-ARCHIVE-001-169.md
    now over a megabyte combined and 460 public files total, this took
    3+ minutes for a check `ritual_check.py` runs every single hour (and
    that `tests/test_vault_leak_check.py`'s own
    `test_real_checkouts_hold_zero_leaks_today` runs every CI run). An
    earlier attempt at this fix just moved the same total bytes-scanned
    into one combined string instead of 460 separate ones -- same
    aggregate work, no real speedup. The actual fix builds a rolling-hash
    set of the full public corpus ONCE (`_haystack_hash_set`, one
    O(len(corpus)) pass), then every vault line's offset scan is O(1)
    hash lookups against that set instead of O(len(corpus)) substring
    scans -- the corpus is scanned once per run, not once per line. A
    hash hit only ever triggers extra confirmation work (a real substring
    check against the combined text, then only if that also hits does it
    resolve which specific file(s) matched); a hash miss is trusted
    outright, since `_haystack_hash_set` recording every real window means
    a genuine leak can never produce an all-miss result. Same
    offset-order, first-match-per-file result as the original nested
    loop."""
    public_files = list(_iter_md_files(orita_dir))
    public_corpus = []
    for path in public_files:
        try:
            with open(path, encoding="utf-8") as f:
                public_corpus.append((path, f.read()))
        except (UnicodeDecodeError, OSError):
            continue

    canon_corpus = _founding_canon_corpus(orita_dir, public_corpus)
    canon_haystack = _build_combined_haystack(canon_corpus, min_run)
    canon_hash_set = _haystack_hash_set(canon_haystack, min_run)

    combined_haystack = _build_combined_haystack(public_corpus, min_run)
    public_hash_set = _haystack_hash_set(combined_haystack, min_run)

    leaks = []
    for vault_path in _private_journal_files(vault_dir):
        vault_rel = os.path.relpath(vault_path, os.path.join(vault_dir, "vault"))
        for line_no, snippet in _significant_lines(vault_path, min_run):
            if _has_independent_public_provenance(
                snippet, min_run, canon_haystack, canon_hash_set
            ):
                continue

            candidates = [
                (public_path, text)
                for public_path, text in public_corpus
                if (vault_rel, line_no, os.path.relpath(public_path, orita_dir))
                not in _REVIEWED_NON_LEAKS
            ]
            offsets_by_file = {}
            for offset, h in _window_hashes(snippet, min_run):
                if len(offsets_by_file) == len(candidates):
                    break
                if h not in public_hash_set:
                    continue
                window = snippet[offset : offset + min_run]
                if window not in combined_haystack:
                    continue
                for public_path, text in candidates:
                    if public_path in offsets_by_file:
                        continue
                    if window in text:
                        offsets_by_file[public_path] = offset

            for public_path, _text in candidates:
                if public_path not in offsets_by_file:
                    continue
                found_at = offsets_by_file[public_path]
                leaks.append({
                    "vault_file": vault_path,
                    "line": line_no,
                    "public_file": public_path,
                    "snippet": snippet[found_at : found_at + 80],
                })
    return leaks


def format_leaks(leaks: list) -> str:
    if not leaks:
        return "vault leak check: clean -- no private journal line found in any public file"
    lines = [f"vault leak check: {len(leaks)} LEAK(S) FOUND -- Proclamation 0001 violated"]
    for leak in leaks:
        lines.append(
            f"  {leak['vault_file']}:{leak['line']} -> {leak['public_file']} :: {leak['snippet']!r}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_leaks()
    print(format_leaks(result))
    sys.exit(1 if result else 0)
