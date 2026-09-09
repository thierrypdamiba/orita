"""Proves tools/draftback_freshness_check.py actually catches a stale
`fencepost/DRAFTS/` preview (missing entirely for the live ledger tip's
date, or dated correctly but byte-mismatched), stays clean when the
committed file agrees with a fresh live re-render, degrades to
clean-but-"unavailable" (never a crash, never a false STALE) when the
live recompute can't run, and confirms the real, currently-committed
DRAFTS/ files match whatever `check_draftback_freshness()` finds true
right now.
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


dfc = _load("draftback_freshness_check", os.path.join(ROOT, "tools", "draftback_freshness_check.py"))


def _write(tmpdir, date, channel, text):
    path = os.path.join(tmpdir, f"{date}-{channel}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


class TestCheckDraftbackFreshness(unittest.TestCase):
    def test_agrees_when_both_channels_match_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "2026-09-09", "email", "email body")
            _write(tmp, "2026-09-09", "notion", "notion body")
            live = {
                "email": {"date": "2026-09-09", "preview": "email body"},
                "notion": {"date": "2026-09-09", "preview": "notion body"},
            }
            result = dfc.check_draftback_freshness(drafts_dir=tmp, live=live)
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["channels"]["email"]["status"], "current")
        self.assertEqual(result["channels"]["notion"]["status"], "current")

    def test_catches_a_missing_preview_for_the_live_tip_date(self):
        """The exact drift this module exists to catch: the ledger moved on
        (a fresh date) and nobody ever ran the CLI again -- there is no
        `<live-date>-<channel>.md` on disk at all, only a stale older one."""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "2026-07-12", "email", "old email body")
            live = {
                "email": {"date": "2026-09-09", "preview": "new email body"},
                "notion": None,
            }
            result = dfc.check_draftback_freshness(drafts_dir=tmp, live=live)
        self.assertFalse(result["clean"])
        self.assertEqual(result["channels"]["email"]["status"], "STALE")
        self.assertIn("missing", result["channels"]["email"]["reason"])

    def test_catches_a_byte_mismatch_on_a_correctly_dated_file(self):
        """Dated right, but the rendered shape has since changed underneath
        it -- e.g. a renderer fix (task 1360's Notion-parity repair) landing
        the same hour a preview was written, before the write picked it up."""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "2026-09-09", "notion", "the old shape")
            live = {"email": None, "notion": {"date": "2026-09-09", "preview": "the new shape"}}
            result = dfc.check_draftback_freshness(drafts_dir=tmp, live=live)
        self.assertFalse(result["clean"])
        self.assertEqual(result["channels"]["notion"]["status"], "STALE")
        self.assertIn("byte mismatch", result["channels"]["notion"]["reason"])

    def test_live_none_is_clean_but_unavailable_not_a_false_pass(self):
        """`live[channel] = None` means "couldn't compute it" (empty ledger
        or import failure), never "computed it and it happened to match."
        Must read clean without ever claiming a real file was checked."""
        with tempfile.TemporaryDirectory() as tmp:
            result = dfc.check_draftback_freshness(drafts_dir=tmp, live={"email": None, "notion": None})
        self.assertTrue(result["clean"])
        self.assertEqual(result["channels"]["email"]["status"], "unavailable")
        self.assertEqual(result["channels"]["notion"]["status"], "unavailable")

    def test_live_preview_state_degrades_to_none_on_any_exception(self):
        """A broken import (or any other unexpected failure inside the
        engine) must never crash the caller -- collapses to the same
        "can't verify here" `None` an empty ledger already returns."""
        real = dfc._seam_modules
        try:
            def _boom():
                raise ModuleNotFoundError("no module named 'seam_engine'")

            dfc._seam_modules = _boom
            self.assertIsNone(dfc.live_preview_state("email"))
        finally:
            dfc._seam_modules = real

    def test_format_names_stale_explicitly(self):
        result = {
            "clean": False,
            "channels": {
                "email": {"status": "STALE", "clean": False, "reason": "missing -- no x for the live ledger tip's own date"},
                "notion": {"status": "current", "clean": True},
            },
        }
        self.assertIn("STALE", dfc.format_draftback_freshness(result))

    def test_format_names_clean_explicitly(self):
        result = {
            "clean": True,
            "channels": {
                "email": {"status": "current", "clean": True},
                "notion": {"status": "unavailable", "clean": True},
            },
        }
        formatted = dfc.format_draftback_freshness(result)
        self.assertIn("email=current", formatted)
        self.assertIn("notion=unavailable", formatted)

    def test_the_real_committed_drafts_are_not_currently_stale(self):
        """Runs the real check against the real, live `fencepost/DRAFTS/`
        with no injected `live` -- either the live recompute genuinely
        agrees with what's committed, or it's unavailable in this
        environment (empty ledger). Either way `clean` must be True; a
        real STALE result here would mean this task shipped while its own
        subject was already broken."""
        result = dfc.check_draftback_freshness()
        self.assertTrue(result["clean"], result)


if __name__ == "__main__":
    unittest.main()
