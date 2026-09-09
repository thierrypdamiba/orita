"""Proves tools/report_card_freshness_check.py actually catches a stale
`docs/fencepost/reports/<date>.html` share card (missing entirely for the
latest sealed report's date, or dated correctly but byte-mismatched),
stays clean when the committed file agrees with a fresh live re-render,
degrades to clean-but-"unavailable" (never a crash, never a false STALE)
when no report has ever been sealed, and confirms the real, currently-
committed card matches whatever `check_report_card_freshness()` finds
true right now.
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


rcfc = _load("report_card_freshness_check", os.path.join(ROOT, "tools", "report_card_freshness_check.py"))


class TestCheckReportCardFreshness(unittest.TestCase):
    def test_agrees_when_committed_card_matches_live(self):
        with tempfile.TemporaryDirectory() as cards_dir:
            path = os.path.join(cards_dir, "2026-09-09.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write("<title>card body</title>")
            live = {"date": "2026-09-09", "page": "<title>card body</title>"}
            result = rcfc.check_report_card_freshness(cards_dir=cards_dir, live=live)
        self.assertTrue(result["clean"], result)
        self.assertEqual(result["status"], "current")

    def test_catches_a_missing_card_for_the_latest_sealed_date(self):
        """The exact drift this module exists to catch: the report sealed
        for a new day (2026-09-09) and nobody ever ran `report_card.py`
        again -- there is no `2026-09-09.html` at all, only a stale older
        one from the day the tool was built. Site's own "share today's
        report" link 404s the moment this happens."""
        with tempfile.TemporaryDirectory() as cards_dir:
            path = os.path.join(cards_dir, "2026-09-08.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write("<title>yesterday's card</title>")
            live = {"date": "2026-09-09", "page": "<title>today's card</title>"}
            result = rcfc.check_report_card_freshness(cards_dir=cards_dir, live=live)
        self.assertFalse(result["clean"])
        self.assertEqual(result["status"], "STALE")
        self.assertIn("missing", result["reason"])

    def test_catches_a_byte_mismatch_on_a_correctly_dated_card(self):
        """Dated right, but the rendered shape has since changed underneath
        it -- e.g. a `report_card.py` template fix landing the same hour a
        card was written, before the write picked it up."""
        with tempfile.TemporaryDirectory() as cards_dir:
            path = os.path.join(cards_dir, "2026-09-09.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write("<title>the old shape</title>")
            live = {"date": "2026-09-09", "page": "<title>the new shape</title>"}
            result = rcfc.check_report_card_freshness(cards_dir=cards_dir, live=live)
        self.assertFalse(result["clean"])
        self.assertEqual(result["status"], "STALE")
        self.assertIn("byte mismatch", result["reason"])

    def test_live_none_is_clean_but_unavailable_not_a_false_pass(self):
        """`live=None` means "no sealed report exists yet," never "computed
        it and it happened to match." Must read clean without ever
        claiming a real file was checked."""
        result = rcfc.check_report_card_freshness(live=None)
        self.assertTrue(result["clean"])
        self.assertEqual(result["status"], "unavailable")

    def test_live_card_state_degrades_to_none_on_any_exception(self):
        """A broken import (or any other unexpected failure) must never
        crash the caller -- collapses to the same "can't verify here"
        `None` an empty REPORTS/ directory already returns."""
        real = rcfc._report_card_module

        def _boom():
            raise ModuleNotFoundError("no module named 'report_card'")

        rcfc._report_card_module = _boom
        try:
            with tempfile.TemporaryDirectory() as reports_dir:
                path = os.path.join(reports_dir, "2026-09-09.md")
                with open(path, "w", encoding="utf-8") as f:
                    f.write("**A gap** -- confidence 0.9.\n**The count.** 1 named.\n")
                self.assertIsNone(rcfc.live_card_state(reports_dir))
        finally:
            rcfc._report_card_module = real

    def test_live_card_state_none_when_no_report_ever_sealed(self):
        with tempfile.TemporaryDirectory() as reports_dir:
            self.assertIsNone(rcfc.live_card_state(reports_dir))

    def test_format_names_stale_explicitly(self):
        result = {"clean": False, "status": "STALE", "reason": "missing -- no x for the latest sealed report's own date"}
        self.assertIn("STALE", rcfc.format_report_card_freshness(result))

    def test_format_names_clean_explicitly(self):
        result = {"clean": True, "status": "current", "date": "2026-09-09"}
        formatted = rcfc.format_report_card_freshness(result)
        self.assertIn("clean", formatted)
        self.assertIn("2026-09-09", formatted)

    def test_format_names_unavailable_explicitly(self):
        result = {"clean": True, "status": "unavailable"}
        self.assertIn("unavailable", rcfc.format_report_card_freshness(result))

    def test_the_real_committed_card_is_not_currently_stale(self):
        """Runs the real check against the real, live
        `docs/fencepost/reports/` with no injected `live` -- either the
        live recompute genuinely agrees with what's committed, or it's
        unavailable in this environment (no sealed report). Either way
        `clean` must be True; a real STALE result here would mean this
        task shipped while its own subject was already broken."""
        result = rcfc.check_report_card_freshness()
        self.assertTrue(result["clean"], result)


if __name__ == "__main__":
    unittest.main()
