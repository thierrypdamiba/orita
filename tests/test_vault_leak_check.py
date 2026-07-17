"""Task 98. Proves tools/vault_leak_check.py's compare actually bites on a
synthetic leak, stays clean on distinct content, ignores short/boilerplate
lines below the confidence threshold, and -- the real point -- confirms
the live, current orita/orita-vault checkouts hold zero leaks today.
"""
import importlib.util
import os
import sys
import tempfile
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


class LiveRepoCase(unittest.TestCase):
    """The real point of task 98: run the compare against the actual,
    current checkouts and confirm the blind-write discipline has genuinely
    held, not just asserted in prose."""

    def test_real_checkouts_hold_zero_leaks_today(self):
        leaks = vlc.find_leaks()
        self.assertEqual(
            leaks, [],
            f"real vault leak(s) found -- Proclamation 0001 violated: {vlc.format_leaks(leaks)}",
        )


def _rm(path):
    import shutil
    shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
