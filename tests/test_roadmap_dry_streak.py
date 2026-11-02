"""Task 2282. Proves tools/roadmap_dry_streak.py parses a real
`wip-opened` marker correctly, refuses an unknown anchor task rather than
guessing, and -- the real point -- that the live checkout's own task 1911
marker parses to a real, fixed timestamp so the hours-since figure is
computed, not eyeballed.

Task 2375 (nisaba) adds `ArchiveFallbackCase`: the hour this suite's own
anchor (task 1911) first got cut out of the live `ROADMAP.md` by
`tools/roadmap_archive.py` into a dated `ROADMAP-ARCHIVE-*.md` sibling,
`find_wip_opened` broke outright (`AnchorNotFoundError` against a task
that genuinely still exists, just not in the one file this module used
to read). Fixed at the source: `find_wip_opened` now also searches every
`ROADMAP-ARCHIVE-*.md` sibling in the same directory as `roadmap_path`.
These cases prove that fallback against fixtures, not just the live
checkout's own current archive layout (which will itself keep changing).
"""
import datetime
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    spec = importlib.util.spec_from_file_location(
        "roadmap_dry_streak", os.path.join(ROOT, "tools", "roadmap_dry_streak.py")
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class FixtureCase(unittest.TestCase):
    def setUp(self):
        self.mod = _load()
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        )
        self.addCleanup(lambda: os.unlink(self.tmp.name))

    def _write(self, text: str) -> None:
        self.tmp.write(text)
        self.tmp.flush()

    def test_parses_real_marker(self):
        self._write(
            "| 1911 | DONE | off-by-one | <!-- wip-opened: 1911 2026-10-02T17:23:51Z --> "
            "some row text | done when text |\n"
        )
        opened = self.mod.find_wip_opened(1911, self.tmp.name)
        self.assertEqual(
            opened,
            datetime.datetime(2026, 10, 2, 17, 23, 51, tzinfo=datetime.timezone.utc),
        )

    def test_hours_since_is_exact(self):
        self._write(
            "| 1911 | DONE | off-by-one | <!-- wip-opened: 1911 2026-10-02T17:23:51Z --> x |\n"
        )
        now = datetime.datetime(2026, 10, 3, 17, 23, 51, tzinfo=datetime.timezone.utc)
        self.assertAlmostEqual(self.mod.hours_since(1911, now, self.tmp.name), 24.0)

    def test_ignores_other_tasks_marker(self):
        self._write(
            "| 1900 | DONE | nisaba | <!-- wip-opened: 1900 2026-09-01T00:00:00Z --> x |\n"
            "| 1911 | DONE | off-by-one | <!-- wip-opened: 1911 2026-10-02T17:23:51Z --> x |\n"
        )
        opened = self.mod.find_wip_opened(1911, self.tmp.name)
        self.assertEqual(opened.year, 2026)
        self.assertEqual(opened.month, 10)

    def test_unknown_anchor_raises(self):
        self._write(
            "| 1911 | DONE | off-by-one | <!-- wip-opened: 1911 2026-10-02T17:23:51Z --> x |\n"
        )
        with self.assertRaises(self.mod.AnchorNotFoundError):
            self.mod.find_wip_opened(9999, self.tmp.name)

    def test_format_status_mentions_task_and_hours(self):
        self._write(
            "| 1911 | DONE | off-by-one | <!-- wip-opened: 1911 2026-10-02T17:23:51Z --> x |\n"
        )
        now = datetime.datetime(2026, 10, 3, 17, 23, 51, tzinfo=datetime.timezone.utc)
        text = self.mod.format_status(1911, now, self.tmp.name)
        self.assertIn("1911", text)
        self.assertIn("24.0", text)


class ArchiveFallbackCase(unittest.TestCase):
    """Proves `find_wip_opened` falls back to a `ROADMAP-ARCHIVE-*.md`
    sibling when the anchor task has been cut out of the live file."""

    def setUp(self):
        self.mod = _load()
        self.dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.dir, ignore_errors=True))
        self.live_path = os.path.join(self.dir, "ROADMAP.md")

    def _write(self, path: str, text: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def test_finds_anchor_only_in_archive_sibling(self):
        self._write(self.live_path, "| 2000 | DONE | nisaba | <!-- wip-opened: 2000 2026-11-02T00:00:00Z --> x |\n")
        self._write(
            os.path.join(self.dir, "ROADMAP-ARCHIVE-009-1768-2374.md"),
            "| 1911 | DONE | off-by-one | <!-- wip-opened: 1911 2026-10-02T17:23:51Z --> x |\n",
        )
        opened = self.mod.find_wip_opened(1911, self.live_path)
        self.assertEqual(
            opened,
            datetime.datetime(2026, 10, 2, 17, 23, 51, tzinfo=datetime.timezone.utc),
        )

    def test_live_file_still_wins_when_anchor_present_in_both(self):
        self._write(self.live_path, "| 1911 | DONE | nisaba | <!-- wip-opened: 1911 2026-11-02T20:00:00Z --> x |\n")
        self._write(
            os.path.join(self.dir, "ROADMAP-ARCHIVE-001-x.md"),
            "| 1911 | DONE | off-by-one | <!-- wip-opened: 1911 2026-10-02T17:23:51Z --> x |\n",
        )
        opened = self.mod.find_wip_opened(1911, self.live_path)
        self.assertEqual(opened.day, 2)
        self.assertEqual(opened.hour, 20)

    def test_still_raises_when_anchor_in_neither(self):
        self._write(self.live_path, "| 2000 | DONE | nisaba | <!-- wip-opened: 2000 2026-11-02T00:00:00Z --> x |\n")
        self._write(
            os.path.join(self.dir, "ROADMAP-ARCHIVE-001-x.md"),
            "| 1900 | DONE | off-by-one | <!-- wip-opened: 1900 2026-09-01T00:00:00Z --> x |\n",
        )
        with self.assertRaises(self.mod.AnchorNotFoundError):
            self.mod.find_wip_opened(1911, self.live_path)


class RealCheckoutCase(unittest.TestCase):
    """Proves the live checkout's own task 1911 marker parses cleanly and
    anchors to the real, known timestamp -- not a fixture's stand-in."""

    def test_live_roadmap_anchor_is_real(self):
        mod = _load()
        opened = mod.find_wip_opened(1911)
        self.assertEqual(
            opened,
            datetime.datetime(2026, 10, 2, 17, 23, 51, tzinfo=datetime.timezone.utc),
        )

    def test_live_hours_since_exceeds_prior_hand_estimates(self):
        """The hand-typed estimates in recent BUILDLOG.md rows/journals
        sat in the 330-370 range; the real figure (computed here) is well
        past that -- the whole point of this module existing."""
        mod = _load()
        now = datetime.datetime.now(datetime.timezone.utc)
        hours = mod.hours_since(1911, now)
        self.assertGreater(hours, 400.0)


if __name__ == "__main__":
    unittest.main()
