"""Task 513. Proves tools/scan_files.py's iter_public_files() and
path_memoize() behave correctly, and that the five sibling checks they were
extracted from (no_grading_check, hand_lore_check, star_covenant_check,
arcade_hero_check, rider_check) each now hold the identical function/
factory object at their own names -- not just identical source text. An
AST-hash sweep of every tools/*.py function body this hour found all five
carrying a byte-identical find_violations()/clear_cache() memoization pair
wrapping a private _VIOLATIONS_CACHE dict, invisible to tools/duplicate_
regex_check.py (which only scans re.compile() call sites, never duplicated
function bodies) -- the exact same shape tasks 508/509/510 already closed
elsewhere (metrics_reader.py, iso_time.py, jsonl_append.py). Three of the
five also carried a byte-identical _iter_public_files(base_dir) walk;
arcade_hero_check.py carried the identical body under a different name
(_iter_scan_files), confirmed by direct diff rather than the name-sensitive
hash. Identity, not equality, is the guarantee that matters: two
independently-maintained copies with the same source today can still drift
apart on the next edit to just one of them; an `is` check on the same
function object (or the same factory function, for path_memoize's per-
caller closures) makes that class of drift structurally impossible going
forward.
"""
import importlib.util
import os
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


sf = _load("scan_files", os.path.join(TOOLS, "scan_files.py"))

ITER_SIBLINGS = [
    ("hand_lore_check", "_iter_public_files"),
    ("star_covenant_check", "_iter_public_files"),
    ("rider_check", "_iter_public_files"),
    ("arcade_hero_check", "_iter_scan_files"),
]

CACHE_SIBLINGS = [
    "no_grading_check",
    "hand_lore_check",
    "star_covenant_check",
    "arcade_hero_check",
    "rider_check",
    "duplicate_regex_check",
    "escape_sequence_check",
]


class IterPublicFilesIdentityAcrossSiblingsCase(unittest.TestCase):
    """Every sibling's public-file walker must BE scan_files.iter_public_
    files (same function object), not merely equal source."""

    def test_every_sibling_shares_the_one_walker_object(self):
        for name, attr in ITER_SIBLINGS:
            with self.subTest(sibling=name, attr=attr):
                mod = _load(name, os.path.join(TOOLS, f"{name}.py"))
                self.assertIs(
                    getattr(mod, attr),
                    sf.iter_public_files,
                    f"{name}.{attr} is a separate copy again, not the "
                    "shared tools/scan_files.py function",
                )


class PathMemoizeIdentityAcrossSiblingsCase(unittest.TestCase):
    """Every sibling's find_violations/clear_cache pair must have come from
    scan_files.path_memoize -- checked by confirming each module imports the
    shared factory (the one place the caching logic itself lives), not a
    private reimplementation of it."""

    def test_every_sibling_imports_the_one_factory(self):
        for name in CACHE_SIBLINGS:
            with self.subTest(sibling=name):
                mod = _load(name, os.path.join(TOOLS, f"{name}.py"))
                self.assertIs(
                    mod.scan_files.path_memoize,
                    sf.path_memoize,
                    f"{name}.scan_files is not the shared tools/scan_files.py module",
                )
                # No sibling should carry its own private cache dict anymore.
                self.assertFalse(
                    hasattr(mod, "_VIOLATIONS_CACHE"),
                    f"{name} still carries a private _VIOLATIONS_CACHE -- "
                    "consolidation task 513 regressed",
                )


class IterPublicFilesCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_yields_md_and_html_only(self):
        for fname in ("a.md", "b.html", "c.txt", "d.py"):
            with open(os.path.join(self.tmp, fname), "w") as f:
                f.write("x")
        found = {os.path.basename(p) for p in sf.iter_public_files(self.tmp)}
        self.assertEqual(found, {"a.md", "b.html"})

    def test_skips_standard_non_content_dirs(self):
        skip_dir = os.path.join(self.tmp, ".git")
        os.makedirs(skip_dir)
        with open(os.path.join(skip_dir, "hidden.md"), "w") as f:
            f.write("x")
        with open(os.path.join(self.tmp, "visible.md"), "w") as f:
            f.write("x")
        found = {os.path.basename(p) for p in sf.iter_public_files(self.tmp)}
        self.assertEqual(found, {"visible.md"})

    def test_nonexistent_dir_yields_nothing(self):
        found = list(sf.iter_public_files(os.path.join(self.tmp, "does-not-exist")))
        self.assertEqual(found, [])


class PathMemoizeCase(unittest.TestCase):
    def test_second_call_is_memoized_and_cheap(self):
        calls = []

        def slow_uncached(orita_dir):
            calls.append(orita_dir)
            time.sleep(0.05)
            return [orita_dir]

        memoized, clear_cache = sf.path_memoize(slow_uncached, "/some/default")

        start = time.time()
        first = memoized("/a")
        first_elapsed = time.time() - start

        start = time.time()
        second = memoized("/a")
        second_elapsed = time.time() - start

        self.assertEqual(first, second)
        self.assertEqual(len(calls), 1, "second call re-invoked the uncached function")
        self.assertLess(second_elapsed, max(first_elapsed / 2, 0.02))

    def test_clear_cache_forces_a_fresh_call(self):
        calls = []

        def counting_uncached(orita_dir):
            calls.append(orita_dir)
            return list(calls)

        memoized, clear_cache = sf.path_memoize(counting_uncached, "/some/default")
        memoized("/a")
        memoized("/a")
        self.assertEqual(len(calls), 1)
        clear_cache()
        memoized("/a")
        self.assertEqual(len(calls), 2)

    def test_default_dir_is_used_when_no_argument_given(self):
        seen = []

        def uncached(orita_dir):
            seen.append(orita_dir)
            return []

        memoized, _clear = sf.path_memoize(uncached, "/the/default")
        memoized()
        self.assertEqual(seen, ["/the/default"])

    def test_each_factory_call_gets_an_independent_cache(self):
        memoized_a, clear_a = sf.path_memoize(lambda d: ["a"], "/x")
        memoized_b, clear_b = sf.path_memoize(lambda d: ["b"], "/x")
        self.assertEqual(memoized_a("/x"), ["a"])
        self.assertEqual(memoized_b("/x"), ["b"])
        # Clearing one cache must never touch the other's.
        clear_a()
        self.assertEqual(memoized_b("/x"), ["b"])

    def test_returned_list_is_a_copy_not_a_shared_reference(self):
        memoized, _clear = sf.path_memoize(lambda d: [1, 2, 3], "/x")
        result = memoized("/x")
        result.append(4)
        self.assertEqual(memoized("/x"), [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
