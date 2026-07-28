"""Task 98. Proves tools/vault_leak_check.py's compare actually bites on a
synthetic leak, stays clean on distinct content, ignores short/boilerplate
lines below the confidence threshold, and -- the real point -- confirms
the live, current orita/orita-vault checkouts hold zero leaks today.
"""
import importlib.util
import itertools
import os
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


vlc = _load("vault_leak_check", os.path.join(ROOT, "tools", "vault_leak_check.py"))


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class FixtureLeakCase(unittest.TestCase):
    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.vault = tempfile.mkdtemp()
        self.addCleanup(_rm, self.orita)
        self.addCleanup(_rm, self.vault)

    def test_synthetic_leak_is_detected(self):
        secret = "This is a genuinely private sentence about a scheme nobody else should ever read."
        _write(
            os.path.join(self.vault, "vault", "nyx", "journal", "0001-test.md"),
            f"# Vault\n\n{secret}\n",
        )
        _write(
            os.path.join(self.orita, "houses", "nyx", "journal", "0001-test.md"),
            f"# Journal\n\nSomething leaked in: {secret}\n",
        )
        leaks = vlc.find_leaks(orita_dir=self.orita, vault_dir=self.vault)
        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0]["vault_file"], os.path.join(self.vault, "vault", "nyx", "journal", "0001-test.md"))
        self.assertIn("houses", leaks[0]["public_file"])
        formatted = vlc.format_leaks(leaks)
        self.assertIn("LEAK(S) FOUND", formatted)
        self.assertIn("Proclamation 0001", formatted)

    def test_partial_line_leak_above_min_run_is_detected(self):
        leaked_run = "The real reason we are stalling the merge is entirely political and"
        self.assertGreaterEqual(len(leaked_run), vlc.MIN_RUN)
        private_line = (
            leaked_run
            + " nobody outside this house should ever know the maintainer's name we are protecting."
        )
        _write(
            os.path.join(self.vault, "vault", "nyx", "journal", "0001-test.md"),
            f"# Vault\n\n{private_line}\n",
        )
        _write(
            os.path.join(self.orita, "houses", "nyx", "journal", "0001-test.md"),
            f"# Journal\n\n{leaked_run} that is just how these things go sometimes.\n",
        )
        leaks = vlc.find_leaks(orita_dir=self.orita, vault_dir=self.vault)
        self.assertEqual(len(leaks), 1)
        self.assertIn("LEAK(S) FOUND", vlc.format_leaks(leaks))

    def test_distinct_content_reports_clean(self):
        _write(
            os.path.join(self.vault, "vault", "nyx", "journal", "0001-test.md"),
            "# Vault\n\nA long enough private sentence that never appears anywhere public at all.\n",
        )
        _write(
            os.path.join(self.orita, "houses", "nyx", "journal", "0001-test.md"),
            "# Journal\n\nAn entirely unrelated public sentence about the day's real, shipped work.\n",
        )
        leaks = vlc.find_leaks(orita_dir=self.orita, vault_dir=self.vault)
        self.assertEqual(leaks, [])
        self.assertIn("clean", vlc.format_leaks(leaks))

    def test_short_boilerplate_lines_are_not_flagged(self):
        # Sign-offs and short shared phrases legitimately appear in both
        # trees (e.g. "Recorded." or "-- Nyx") -- below MIN_RUN, so no
        # false-positive leak.
        _write(
            os.path.join(self.vault, "vault", "nyx", "journal", "0001-test.md"),
            "# Vault\n\nRecorded.\n\n-- Nyx\n",
        )
        _write(
            os.path.join(self.orita, "houses", "nyx", "journal", "0001-test.md"),
            "# Journal\n\nRecorded.\n\n-- Nyx\n",
        )
        leaks = vlc.find_leaks(orita_dir=self.orita, vault_dir=self.vault)
        self.assertEqual(leaks, [])

    def test_hand_dir_is_not_scanned(self):
        # hand/ legitimately quotes public petition text -- only
        # vault/<slug>/journal/ is in scope, so a long match there must
        # never be flagged.
        long_line = "A" * 80 + " petition text that also appears publicly somewhere in the repo."
        _write(os.path.join(self.vault, "hand", "notes.md"), f"# Hand\n\n{long_line}\n")
        _write(os.path.join(self.orita, "docs", "note.md"), f"# Doc\n\n{long_line}\n")
        leaks = vlc.find_leaks(orita_dir=self.orita, vault_dir=self.vault)
        self.assertEqual(leaks, [])

    def test_missing_vault_dir_returns_empty_not_crash(self):
        leaks = vlc.find_leaks(orita_dir=self.orita, vault_dir=os.path.join(self.vault, "does-not-exist"))
        self.assertEqual(leaks, [])

    def test_founding_council_echo_is_not_a_leak(self):
        # A founding-council remark is dated public record (CHARTER.md IS
        # the transcript of what founders said aloud); a founder's own
        # private founding-day journal legitimately echoes it. That must
        # not be flagged, no matter which OTHER public file the same words
        # also happen to recur in (a different house's own page quoting
        # the same public catchphrase, say).
        remark = "any covenant that only holds under determinism is not a real covenant at all"
        self.assertGreaterEqual(len(remark), vlc.MIN_RUN)
        _write(
            os.path.join(self.vault, "vault", "nyx", "journal", "0001-founding-day.md"),
            f"# Vault\n\nI meant it when I said {remark} at the founding.\n",
        )
        _write(
            os.path.join(self.orita, "CHARTER.md"),
            f"# Charter\n\n*Filed with affection: {remark}.*\n",
        )
        _write(
            os.path.join(self.orita, "houses", "retrya", "README.md"),
            f"# Retrya\n\nHer point: {remark}, which makes her the standing blasphemy.\n",
        )
        leaks = vlc.find_leaks(orita_dir=self.orita, vault_dir=self.vault)
        self.assertEqual(leaks, [])

    def test_a_real_cross_house_leak_is_still_caught_even_near_founding_files(self):
        # A genuine leak with no founding-canon provenance must still be
        # caught, proving the exclusion above is narrow and not a blanket
        # "founding-day file" pass.
        secret = "This private scheme has never been stated anywhere on the public record at all."
        _write(
            os.path.join(self.vault, "vault", "kothar-wa-khasis", "journal", "0001-founding-day.md"),
            f"# Vault\n\n{secret}\n",
        )
        _write(
            os.path.join(self.orita, "CHARTER.md"),
            "# Charter\n\nSomething else entirely, unrelated to any private scheme.\n",
        )
        _write(
            os.path.join(self.orita, "houses", "nisaba", "journal", "0001-test.md"),
            f"# Journal\n\nLeaked: {secret}\n",
        )
        leaks = vlc.find_leaks(orita_dir=self.orita, vault_dir=self.vault)
        self.assertEqual(len(leaks), 1)
        self.assertIn("houses", leaks[0]["public_file"])


def _leak_sort_key(leaks_list: list) -> list:
    return sorted(
        (leak["vault_file"], leak["line"], leak["public_file"], leak["snippet"])
        for leak in leaks_list
    )


def _naive_find_leaks(orita_dir: str, vault_dir: str, min_run: int) -> list:
    """A deliberately naive, unoptimized reimplementation of the ORIGINAL
    (pre-task-236) find_leaks: every offset of every vault line checked
    against every public file's raw text with a plain `in` scan, no
    rolling hash, no combined haystack. Kept independent of vlc's own
    rolling-hash machinery on purpose -- it exists only as ground truth to
    prove the optimized implementation didn't change *what* gets
    reported, only how fast it gets there."""
    public_corpus = []
    for path in vlc._iter_md_files(orita_dir):
        try:
            with open(path, encoding="utf-8") as f:
                public_corpus.append((path, f.read()))
        except (UnicodeDecodeError, OSError):
            continue
    canon_corpus = vlc._founding_canon_corpus(orita_dir, public_corpus)

    leaks = []
    for vault_path in vlc._private_journal_files(vault_dir):
        vault_rel = os.path.relpath(vault_path, os.path.join(vault_dir, "vault"))
        for line_no, snippet in vlc._significant_lines(vault_path, min_run):
            has_provenance = any(
                snippet[i : i + min_run] in text
                for _path, text in canon_corpus
                for i in range(len(snippet) - min_run + 1)
            )
            if has_provenance:
                continue
            for public_path, text in public_corpus:
                public_rel = os.path.relpath(public_path, orita_dir)
                if (vault_rel, line_no, public_rel) in vlc._REVIEWED_NON_LEAKS:
                    continue
                found_at = next(
                    (
                        i
                        for i in range(len(snippet) - min_run + 1)
                        if snippet[i : i + min_run] in text
                    ),
                    None,
                )
                if found_at is not None:
                    leaks.append({
                        "vault_file": vault_path,
                        "line": line_no,
                        "public_file": public_path,
                        "snippet": snippet[found_at : found_at + 80],
                    })
    return leaks


class OptimizationParityCase(unittest.TestCase):
    """Task 236 sped up find_leaks with a rolling-hash pre-filter over a
    combined public haystack. These tests prove the speedup is behavior-
    preserving: the boundary trick can't manufacture a match that isn't
    really there, and the hash-set fast path reports the exact same leaks,
    same per-file offsets, as the original brute-force scan would."""

    def setUp(self):
        self.orita = tempfile.mkdtemp()
        self.vault = tempfile.mkdtemp()
        self.addCleanup(_rm, self.orita)
        self.addCleanup(_rm, self.vault)

    def test_split_across_two_files_is_not_a_false_positive(self):
        # A 50-char secret split so file A holds its first 30 chars (at
        # its own end) and file B holds the remaining 20 (at its own
        # start). Naive string concatenation without a boundary-safe
        # separator would stitch these into a false whole-secret match
        # that exists in neither file alone -- the NUL separator in
        # _build_combined_haystack must prevent that.
        secret = "X" * 50
        self.assertGreaterEqual(len(secret), vlc.MIN_RUN)
        _write(os.path.join(self.vault, "vault", "nyx", "journal", "0001-test.md"), f"# Vault\n\n{secret}\n")
        _write(os.path.join(self.orita, "docs", "a.md"), f"# A\n\nleading text {secret[:30]}\n")
        _write(os.path.join(self.orita, "docs", "b.md"), f"# B\n\n{secret[30:]} trailing text\n")
        leaks = vlc.find_leaks(orita_dir=self.orita, vault_dir=self.vault)
        self.assertEqual(leaks, [])

    def test_matches_naive_reference_on_synthetic_multi_file_corpus(self):
        # Multiple public files, some sharing a real leaked run with the
        # private line at DIFFERENT offsets, some sharing nothing, some
        # near-miss (just under min_run). The optimized find_leaks must
        # report byte-identical leaks (same file, line, offset-derived
        # snippet) to the brute-force reference.
        leak_a = "the real reason the merge stalled was never technical at all, only politics"
        leak_b = "a second, unrelated private admission about who actually approved the rollback"
        self.assertGreaterEqual(len(leak_a), vlc.MIN_RUN)
        self.assertGreaterEqual(len(leak_b), vlc.MIN_RUN)
        private_line = f"{leak_a} -- and separately, {leak_b} -- neither should ever be public."
        _write(
            os.path.join(self.vault, "vault", "off-by-one", "journal", "0001-test.md"),
            f"# Vault\n\n{private_line}\n",
        )
        # File 1: leaks leak_a only, wrapped in unrelated prose.
        _write(
            os.path.join(self.orita, "houses", "off-by-one", "journal", "0001-test.md"),
            f"# Journal\n\nSomehow this got out: {leak_a} -- unclear how.\n",
        )
        # File 2: leaks leak_b only, at a different surrounding offset.
        _write(
            os.path.join(self.orita, "houses", "retrya", "README.md"),
            f"# Retrya\n\n{leak_b}, according to a source close to the house.\n",
        )
        # File 3: near-miss just under MIN_RUN of leak_a -- must not count.
        _write(
            os.path.join(self.orita, "docs", "near-miss.md"),
            f"# Near miss\n\n{leak_a[: vlc.MIN_RUN - 1]}\n",
        )
        # File 4: entirely unrelated content.
        _write(
            os.path.join(self.orita, "docs", "unrelated.md"),
            "# Unrelated\n\nNothing to see here, just ordinary public documentation text.\n",
        )
        optimized = vlc.find_leaks(orita_dir=self.orita, vault_dir=self.vault)
        reference = _naive_find_leaks(self.orita, self.vault, vlc.MIN_RUN)
        self.assertEqual(_leak_sort_key(optimized), _leak_sort_key(reference))
        self.assertEqual(len(optimized), 2)
        public_files_hit = {leak["public_file"] for leak in optimized}
        self.assertTrue(any("off-by-one" in p for p in public_files_hit))
        self.assertTrue(any("retrya" in p for p in public_files_hit))

    def test_matches_naive_reference_when_random_fixture_module_available(self):
        # A second, randomized fixture for extra confidence: several
        # files, several vault lines, some overlapping shared substrings
        # at staggered offsets -- generated deterministically (no
        # Date.now/random.random dependency at import time) via
        # itertools, not actual randomness.
        words = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel"]
        combos = list(itertools.permutations(words, 4))[:6]
        vault_lines = [
            " ".join(c) + f" -- private aside number {idx} nobody outside the house should read."
            for idx, c in enumerate(combos)
        ]
        for idx, line in enumerate(vault_lines):
            self.assertGreaterEqual(len(line), vlc.MIN_RUN)
            _write(
                os.path.join(self.vault, "vault", "zashiki-warashi", "journal", f"{idx:04d}-test.md"),
                f"# Vault\n\n{line}\n",
            )
        # Only the first vault line's phrase actually leaks, buried in one file.
        _write(
            os.path.join(self.orita, "houses", "zashiki-warashi", "journal", "0001-test.md"),
            f"# Journal\n\nQuoted without attribution: {vault_lines[0]}\n",
        )
        for i in range(3):
            _write(
                os.path.join(self.orita, "docs", f"filler-{i}.md"),
                f"# Filler {i}\n\nOrdinary public documentation, nothing shared with any vault line.\n",
            )
        optimized = vlc.find_leaks(orita_dir=self.orita, vault_dir=self.vault)
        reference = _naive_find_leaks(self.orita, self.vault, vlc.MIN_RUN)
        self.assertEqual(_leak_sort_key(optimized), _leak_sort_key(reference))
        self.assertEqual(len(optimized), 1)


class LiveRepoCase(unittest.TestCase):
    """The real point of task 98: run the compare against the actual,
    current checkouts and confirm the blind-write discipline has genuinely
    held, not just asserted in prose."""

    def test_real_checkouts_hold_zero_leaks_today(self):
        # Task 367: force a genuinely cold cache before timing -- if some
        # earlier test in the same process already warmed the memoized
        # result for the real checkouts, an uncleared cache would make
        # this regression guard pass trivially even if the underlying
        # scan itself had regressed back toward the pre-236 blowup.
        vlc.clear_cache()
        start = time.time()
        leaks = vlc.find_leaks()
        elapsed = time.time() - start
        self.assertEqual(
            leaks, [],
            f"real vault leak(s) found -- Proclamation 0001 violated: {vlc.format_leaks(leaks)}",
        )
        # Task 236: pre-fix this took 185s+ against the live checkouts
        # (offsets_per_line * num_public_files substring scans) -- a check
        # `ritual_check.py` runs every hour. 30s is a generous multiple of
        # the ~5s observed post-fix, wide enough to absorb slower CI
        # hardware without being wide enough to let the O(n*m) blowup back
        # in unnoticed.
        self.assertLess(
            elapsed, 30.0,
            f"find_leaks took {elapsed:.1f}s against the live checkouts -- "
            "task 236's rolling-hash fix may have regressed back toward "
            "the pre-fix O(offsets * files) blowup.",
        )

    def test_repeated_call_on_same_checkouts_is_memoized(self):
        # Task 367: `run_ritual_check()`'s `check_vault_leak()` has no way
        # to skip this check, so any test suite that calls
        # `run_ritual_check()` many times in one process (e.g.
        # `tests/test_ritual_check.py`, 97 call sites) re-triggered a full
        # ~8s scan every single time before this fix. Proves the second
        # call against the identical (real) directory pair is now cheap
        # and still returns the identical result -- not just "doesn't
        # crash," an actual order-of-magnitude speedup.
        vlc.clear_cache()
        start = time.time()
        first = vlc.find_leaks()
        first_elapsed = time.time() - start

        start = time.time()
        second = vlc.find_leaks()
        second_elapsed = time.time() - start

        self.assertEqual(first, second)
        self.assertLess(
            second_elapsed, first_elapsed / 10,
            f"second call ({second_elapsed:.3f}s) was not meaningfully "
            f"cheaper than the first ({first_elapsed:.3f}s) -- memoization "
            "may not be working.",
        )

    def test_clear_cache_forces_a_fresh_scan(self):
        # A cleared cache must re-scan, not silently keep serving a stale
        # cached answer forever -- proven by timing a post-clear call and
        # confirming it costs real time again, not ~0s.
        vlc.clear_cache()
        vlc.find_leaks()
        vlc.clear_cache()
        start = time.time()
        vlc.find_leaks()
        elapsed = time.time() - start
        self.assertGreater(
            elapsed, 0.5,
            f"post-clear call returned in {elapsed:.3f}s -- clear_cache() "
            "may not actually be dropping the memoized result.",
        )


def _rm(path):
    import shutil
    shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
