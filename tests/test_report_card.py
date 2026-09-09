"""Task 1355 (Kwaku-Ananse). tools/report_card.py builds a per-day share
card for the Fencepost Report -- the same "card trick" TOWN-OPERATIONS.md
already describes for images (tools/card.py), adapted for text: no image to
point twitter:image at, so this builds a `summary` card whose <meta> tags
carry the day's REAL headline and count, read straight off the already-
sealed report text, never guessed or re-derived. Before this, every shared
link to docs/fencepost/index.html rendered the same static, generic
preview no matter which day's gap it was -- this file proves the fix: a
real sealed report's headline/count land correctly in every tag that
matters; a malformed or blank report text is refused, loudly, before a
single byte is written; HTML-unsafe input is escaped, not injected; and
main() -- the actual CLI entrypoint -- reads a real report file, writes the
card, and prints the URL.
"""
import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


report_card = _load("report_card", os.path.join(ROOT, "tools", "report_card.py"))

REAL_REPORT = """# Fencepost Report — 2026-09-08

*The one thing that fell between `thierrypdamiba/orita`'s accounts yesterday.*

*Episode 56. Day 10 of the watch, unbroken — same seam, same hour, every day.*

**Milestone-level work shipped but never reached @oritatown** — confidence 0.85.

336 milestone commit(s) since 2026-07-12 (matching ['fencepost', 'flagship', 'strategy']), none echoed in a post.

- [bb325b78b943](https://github.com/thierrypdamiba/orita/commit/bb325b78b943ee84978cf6042c320283dd79bc5b)

**The count.** 155 fenceposts named to date. The wall reads 154.

The day it closes: not declared. Nothing in this town changes its own law unwitnessed — so if that day ever comes, it will be a dated, public declaration, argued in the open and decided by the Hand, never arithmetic quietly producing a different number on a schedule. Until then: so close.

**Your move.** Post about it yourself — a single line linking it is enough. Fencepost only found the seam; it does not cross it.

**Connect your own.** This is the seam we watch on our own accounts. Point Fencepost at yours — five minutes, read-only, revocable in one click — and it will find the one thing sitting in *your* seam. [Connect your own](https://thierrypdamiba.github.io/orita/fencepost/connect.html).

You were so close. You are always so close.

Recorded. — Nisaba
"""

NOTHING_REPORT = """# Fencepost Report — 2026-01-01

*The one thing that fell between `thierrypdamiba/orita`'s accounts yesterday.*

**Nothing cleared the bar today.** The seam held — recorded plainly, not padded.

**The count.** 0 fenceposts named to date. The wall reads -1.

The day it closes: not declared.

**Your move.** Nothing to act on today.

**Connect your own.** Point Fencepost at yours.

You were so close. You are always so close.

Recorded. — Nisaba
"""


class TestBuildReportCardRealReport(unittest.TestCase):
    def test_extracts_the_real_headline_and_count(self):
        page, page_url = report_card.build_report_card("2026-09-08", REAL_REPORT)
        self.assertIn(
            "Fencepost — 2026-09-08: Milestone-level work shipped but never "
            "reached @oritatown",
            page,
        )
        self.assertIn(
            "155 fenceposts named to date. The wall reads 154.", page
        )
        self.assertEqual(
            page_url, "https://thierrypdamiba.github.io/orita/fencepost/reports/2026-09-08.html"
        )

    def test_the_line_is_imported_not_retyped(self):
        page, _ = report_card.build_report_card("2026-09-08", REAL_REPORT)
        self.assertIn("You were so close. You are always so close.", page)
        # Same literal object the report itself renders with -- if
        # seam_engine.report.THE_LINE ever changes, this catches drift
        # instead of silently quoting a stale copy.
        from seam_engine.report import THE_LINE

        self.assertIn(THE_LINE, page)

    def test_headline_does_not_pick_up_the_count_or_your_move_lines(self):
        page, _ = report_card.build_report_card("2026-09-08", REAL_REPORT)
        title_line = [ln for ln in page.splitlines() if ln.startswith("<title>")][0]
        self.assertNotIn("The count", title_line)
        self.assertNotIn("Your move", title_line)

    def test_nothing_cleared_the_bar_shape_also_parses(self):
        page, page_url = report_card.build_report_card("2026-01-01", NOTHING_REPORT)
        self.assertIn("Fencepost — 2026-01-01: Nothing cleared the bar today.", page)
        self.assertEqual(
            page_url, "https://thierrypdamiba.github.io/orita/fencepost/reports/2026-01-01.html"
        )


class TestBuildReportCardShape(unittest.TestCase):
    def test_twitter_card_is_summary_not_large_image(self):
        # No image exists for a text report -- summary_large_image with no
        # image is worse than plain summary, not better.
        page, _ = report_card.build_report_card("2026-09-08", REAL_REPORT)
        self.assertIn('twitter:card" content="summary"', page)
        self.assertNotIn("summary_large_image", page)

    def test_html_unsafe_headline_is_escaped_not_injected(self):
        evil = REAL_REPORT.replace(
            "Milestone-level work shipped but never reached @oritatown",
            "<script>evil()</script>",
        )
        page, _ = report_card.build_report_card("2026-09-08", evil)
        self.assertNotIn("<script>evil()</script>", page)
        self.assertIn("&lt;script&gt;evil()&lt;/script&gt;", page)

    def test_links_back_to_fencepost_index_and_connect(self):
        page, _ = report_card.build_report_card("2026-09-08", REAL_REPORT)
        self.assertIn('href="../index.html"', page)
        self.assertIn('href="../connect.html"', page)
        self.assertIn('href="../../style.css"', page)


class TestBuildReportCardValidation(unittest.TestCase):
    def test_blank_date_raises(self):
        with self.assertRaises(report_card.ReportCardValidationError):
            report_card.build_report_card("", REAL_REPORT)

    def test_malformed_date_raises(self):
        with self.assertRaises(report_card.ReportCardValidationError):
            report_card.build_report_card("Sept 8", REAL_REPORT)

    def test_blank_report_text_raises(self):
        with self.assertRaises(report_card.ReportCardValidationError):
            report_card.build_report_card("2026-09-08", "")

    def test_report_text_missing_a_headline_line_raises(self):
        broken = "# Fencepost Report — 2026-09-08\n\n**The count.** 1 fencepost named to date. The wall reads 0.\n"
        with self.assertRaises(report_card.ReportCardValidationError):
            report_card.build_report_card("2026-09-08", broken)

    def test_report_text_missing_the_count_line_raises(self):
        broken = "# Fencepost Report — 2026-09-08\n\n**A headline** — confidence 0.85.\n"
        with self.assertRaises(report_card.ReportCardValidationError):
            report_card.build_report_card("2026-09-08", broken)


class TestMainCLI(unittest.TestCase):
    def _seed_report(self, tmp, date, text):
        reports_dir = os.path.join(tmp, "fencepost", "REPORTS")
        os.makedirs(reports_dir, exist_ok=True)
        with open(os.path.join(reports_dir, f"{date}.md"), "w", encoding="utf-8") as f:
            f.write(text)

    def test_main_reads_report_writes_card_prints_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._seed_report(tmp, "2026-09-08", REAL_REPORT)
            with mock.patch.object(report_card, "ROOT", tmp):
                argv = ["report_card.py", "2026-09-08"]
                out = io.StringIO()
                with mock.patch.object(sys, "argv", argv):
                    with contextlib.redirect_stdout(out):
                        code = report_card.main()
                self.assertEqual(code, 0)
                self.assertEqual(
                    out.getvalue().strip(),
                    "https://thierrypdamiba.github.io/orita/fencepost/reports/2026-09-08.html",
                )
                written = os.path.join(tmp, "docs", "fencepost", "reports", "2026-09-08.html")
                self.assertTrue(os.path.exists(written))
                with open(written, encoding="utf-8") as f:
                    self.assertIn("155 fenceposts named to date", f.read())

    def test_main_latest_picks_the_most_recent_sealed_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._seed_report(tmp, "2026-09-07", NOTHING_REPORT.replace("2026-01-01", "2026-09-07"))
            self._seed_report(tmp, "2026-09-08", REAL_REPORT)
            with mock.patch.object(report_card, "ROOT", tmp):
                argv = ["report_card.py", "latest"]
                out = io.StringIO()
                with mock.patch.object(sys, "argv", argv):
                    with contextlib.redirect_stdout(out):
                        code = report_card.main()
                self.assertEqual(code, 0)
                self.assertIn("2026-09-08.html", out.getvalue())

    def test_main_with_no_args_prints_usage_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(report_card, "ROOT", tmp):
                argv = ["report_card.py"]
                out = io.StringIO()
                with mock.patch.object(sys, "argv", argv):
                    with contextlib.redirect_stdout(out):
                        code = report_card.main()
                self.assertEqual(code, 1)
                self.assertFalse(os.path.exists(os.path.join(tmp, "docs")))

    def test_main_with_unknown_date_names_the_problem_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(report_card, "ROOT", tmp):
                argv = ["report_card.py", "2099-01-01"]
                err = io.StringIO()
                with mock.patch.object(sys, "argv", argv):
                    with contextlib.redirect_stderr(err):
                        code = report_card.main()
                self.assertEqual(code, 1)
                self.assertIn("cannot read", err.getvalue())

    def test_main_refuses_malformed_report_before_writing_anything(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._seed_report(tmp, "2026-09-08", "not a real report at all")
            with mock.patch.object(report_card, "ROOT", tmp):
                argv = ["report_card.py", "2026-09-08"]
                err = io.StringIO()
                with mock.patch.object(sys, "argv", argv):
                    with contextlib.redirect_stderr(err):
                        code = report_card.main()
                self.assertEqual(code, 1)
                self.assertIn("refused", err.getvalue())
                self.assertFalse(os.path.exists(os.path.join(tmp, "docs")))


class TestRealSealedReportsAllParse(unittest.TestCase):
    """The real proof: every report the town has actually sealed to date
    parses without raising -- not just the two hand-built fixtures above."""

    def test_every_real_sealed_report_builds_a_card_without_raising(self):
        reports_dir = os.path.join(ROOT, "fencepost", "REPORTS")
        names = [
            f
            for f in os.listdir(reports_dir)
            if f.endswith(".md") and report_card._DATE_RE.match(f[:-3])
        ]
        self.assertGreater(len(names), 0)
        for name in names:
            date = name[:-3]
            with open(os.path.join(reports_dir, name), encoding="utf-8") as f:
                text = f.read()
            page, url = report_card.build_report_card(date, text)
            self.assertIn(date, url)
            self.assertIn("<title>", page)


if __name__ == "__main__":
    unittest.main()
