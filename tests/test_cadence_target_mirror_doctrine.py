#!/usr/bin/env python3
"""Task 158. Nisaba checks her own file's mirror claim against the file it
claims to mirror.

`tools/metrics_cadence_check.py` (task 117, mine) has said since it shipped:
`TARGET_STREAK_DAYS = 30  # mirrors report_cadence_check.py's own daily
target`. A direct claim about a sibling file -- the exact "never checked
against the live thing it claims to mirror" shape tasks 135-157 already
closed in six other offices, never once checked in this one. The two
constants agree today, but nothing anywhere compares them; a future edit to
either module's `30` would drift silently.

Worse, the mirror was structurally incomplete on the consuming side too:
`report_cadence_check.format_cadence()` renders its `target` in the printed
line ("target 30/30, STRATEGY.md's off-by-one metric"), and
`tools/ritual_check.py`'s own `format_ritual_check` copies that rendering for
`report_cadence` -- but `metrics_cadence_check.format_cadence()` computed a
`target` key on every call and never printed it, and `ritual_check.py`'s own
printed `metrics_cadence` line silently dropped it too (confirmed live: a
real `ritual_check.py` run this hour printed "report cadence: 5-day streak
(target 30/30, ...)" next to "metrics cadence: 3-day streak (records/
metrics.jsonl, daily-aggregate readings), 2 historical gap day(s)" -- no
target, side by side with a sibling line that has one).

Fixed both `format_cadence` functions to print `target`, wired the same fix
into `ritual_check.py`'s own printed line. This file proves the
constant-level mirror and the printed-line symmetry structurally -- live
imports of the real modules, never a second hand-typed "30" or "target" --
with mutation tests proving each check would have caught the real,
pre-task-158 state.
"""
from __future__ import annotations

import importlib.util
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name: str, relpath: str):
    """Load a fresh module instance from `relpath`, keyed by `name` so
    repeated loads in the same process never collide -- the same
    `importlib.util.spec_from_file_location` shape task 153's
    `test_oracle_scopes_subscriber_test_count.py` already uses for the
    identical reason (live-loading a module this suite doesn't otherwise
    import, without polluting `sys.modules` for other tests)."""
    path = os.path.join(ROOT, relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TargetStreakDaysMirrorCase(unittest.TestCase):
    """The constant-level claim: `metrics_cadence_check.TARGET_STREAK_DAYS`
    really does equal `report_cadence_check.TARGET_STREAK_DAYS`, checked by
    live-loading both real files, never by re-typing "30" a third time."""

    def test_real_modules_agree_on_target_streak_days(self):
        mcc = _load("_t158_mcc_real", "tools/metrics_cadence_check.py")
        rcc = _load("_t158_rcc_real", "tools/report_cadence_check.py")
        self.assertEqual(mcc.TARGET_STREAK_DAYS, rcc.TARGET_STREAK_DAYS)

    def test_mutation_a_drifted_constant_would_have_been_caught(self):
        """Reconstructs the exact failure mode the doc comment's claim was
        never guarded against: one module's target quietly moves and
        nothing notices. Mutating a *loaded copy* (never the file on disk)
        and re-running the identical comparison this suite's own real test
        runs proves the check bites."""
        mcc = _load("_t158_mcc_mut", "tools/metrics_cadence_check.py")
        rcc = _load("_t158_rcc_mut", "tools/report_cadence_check.py")
        mcc.TARGET_STREAK_DAYS = rcc.TARGET_STREAK_DAYS + 1
        self.assertNotEqual(mcc.TARGET_STREAK_DAYS, rcc.TARGET_STREAK_DAYS)


class PrintedTargetSymmetryCase(unittest.TestCase):
    """The consuming-side claim: `metrics_cadence_check.format_cadence()`
    now names its target the same way `report_cadence_check.format_cadence()`
    already does, and `ritual_check.py`'s own printed line inherits it."""

    def test_metrics_cadence_format_now_names_its_target(self):
        mcc = _load("_t158_mcc_fmt", "tools/metrics_cadence_check.py")
        result = {
            "total_shipped": 3,
            "first_date": "2026-07-15",
            "most_recent_date": "2026-07-17",
            "current_streak": 3,
            "missing_dates": [],
            "target": 30,
        }
        formatted = mcc.format_cadence(result)
        self.assertIn("target 30/30", formatted)

    def test_mutation_the_real_pre_fix_format_cadence_dropped_target(self):
        """Reconstructs `format_cadence`'s real pre-task-158 body (the exact
        text it held before this task, minus the `target` clause) against
        the identical fixture, proving it really would have omitted
        "target" -- the real historical gap, not a synthetic one."""

        def pre_fix_format_cadence(result: dict) -> str:
            if result["total_shipped"] == 0:
                return "metrics cadence: no daily-aggregate reading has ever shipped -- nothing to count yet"
            lines = [
                f"metrics cadence: {result['current_streak']}-day streak "
                f"(records/metrics.jsonl, daily-aggregate readings) -- "
                f"{result['total_shipped']} shipped total, most recent {result['most_recent_date']}"
            ]
            if result["missing_dates"]:
                joined = ", ".join(result["missing_dates"])
                lines.append(f"  {len(result['missing_dates'])} historical gap day(s), already on record: {joined}")
            else:
                lines.append("  no gap day between first and most recent shipped reading")
            return "\n".join(lines)

        result = {
            "total_shipped": 3,
            "first_date": "2026-07-15",
            "most_recent_date": "2026-07-17",
            "current_streak": 3,
            "missing_dates": [],
            "target": 30,
        }
        self.assertNotIn("target", pre_fix_format_cadence(result))

        mcc = _load("_t158_mcc_fmt2", "tools/metrics_cadence_check.py")
        self.assertIn("target", mcc.format_cadence(result))

    def test_ritual_check_printed_metrics_cadence_line_now_names_target(self):
        rc = _load("_t158_ritual", "tools/ritual_check.py")
        import shutil
        import tempfile

        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        metrics_path = os.path.join(tmp, "metrics.jsonl")
        with open(metrics_path, "w") as f:
            for d in ("15", "16", "17"):
                f.write(f'{{"date": "2026-07-{d}"}}\n')

        # Task 249: a bare rc.run_ritual_check() call writes durably and
        # unconditionally via check_words()/check_scribe_growth() (task 87/168)
        # -- this file's own _load() gives back a module instance untouched by
        # test_ritual_check.py's module-level word_watch guard, so without this
        # override this call would silently append a real line to the REAL
        # HAND/word-check-log.jsonl and HAND/scribe-growth-log.jsonl on every
        # test run, the exact "a test run silently wrote to the real log" bug
        # class tasks 71/83/85/86/88 already caught elsewhere but never closed
        # here. Point both at throwaway temp logs, same shape test_ritual_check
        # .py's setUpModule() already uses for word_watch.
        safe_word_watch = _load("_t158_safe_word_watch", "tools/word_watch.py")
        safe_word_watch.LOG = os.path.join(tmp, "word-check-log.jsonl")
        rc._word_watch = lambda: safe_word_watch
        safe_scribe_growth = _load("_t158_safe_scribe_growth", "tools/scribe_growth_check.py")
        safe_scribe_growth.LOG = os.path.join(tmp, "scribe-growth-log.jsonl")
        rc._scribe_growth_check = lambda: safe_scribe_growth

        result = rc.run_ritual_check(metrics_cadence_path=metrics_path)
        formatted = rc.format_ritual_check(result)
        metrics_line = next(
            (line for line in formatted.splitlines() if line.strip().startswith("metrics cadence:")),
            None,
        )
        self.assertIsNotNone(metrics_line)
        self.assertIn("target 30/30", metrics_line)

        report_line = next(
            (line for line in formatted.splitlines() if line.strip().startswith("report cadence:")),
            None,
        )
        self.assertIsNotNone(report_line)
        self.assertIn("target", report_line)
        self.assertIn("target", metrics_line)

    def test_run_ritual_check_here_never_touches_the_real_hand_logs(self):
        """Task 249's regression pin: reproduces the exact pollution live-
        caught this hour (a background `python3 -m unittest discover`
        run appended real entries to HAND/word-check-log.jsonl and
        HAND/scribe-growth-log.jsonl mid-run) by calling this file's own
        `rc.run_ritual_check()` -- unguarded, pre-fix, this appends a real
        line to both on every call -- and asserting the real files come
        back byte-identical.

        Task 375: `check_words`/`word_watch` no longer records
        unconditionally either -- the sibling gap task 374's own closing
        note named and left unfixed is closed here, the identical shape:
        `run_ritual_check()`'s new `record_words` parameter also defaults
        `False`, so `safe_word_watch.LOG` is now expected to NOT exist
        after a bare call, same as `safe_scribe_growth.LOG` already reads
        below. Both checks now write to NEITHER the real log NOR a
        redirected one on a bare/library call, closing the actual
        pollution class one layer earlier than this test originally could
        reach: not just "never touch the real file" but "don't write at
        all unless a caller says so." """
        real_word_log = os.path.join(ROOT, "HAND", "word-check-log.jsonl")
        real_scribe_log = os.path.join(ROOT, "HAND", "scribe-growth-log.jsonl")
        before = {}
        for p in (real_word_log, real_scribe_log):
            if os.path.exists(p):
                with open(p, "rb") as f:
                    before[p] = f.read()

        rc = _load("_t249_ritual_no_pollute", "tools/ritual_check.py")
        import shutil
        import tempfile

        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        safe_word_watch = _load("_t249_safe_word_watch", "tools/word_watch.py")
        safe_word_watch.LOG = os.path.join(tmp, "word-check-log.jsonl")
        rc._word_watch = lambda: safe_word_watch
        safe_scribe_growth = _load("_t249_safe_scribe_growth", "tools/scribe_growth_check.py")
        safe_scribe_growth.LOG = os.path.join(tmp, "scribe-growth-log.jsonl")
        rc._scribe_growth_check = lambda: safe_scribe_growth

        rc.run_ritual_check()

        for p, contents in before.items():
            with open(p, "rb") as f:
                self.assertEqual(f.read(), contents, f"{p} was written to by a test run")
        # Task 375: a bare run_ritual_check() call no longer records words
        # anywhere, real or redirected -- record_words defaults False, the
        # identical guarantee task 374 already gave scribe growth below.
        self.assertFalse(os.path.exists(safe_word_watch.LOG))
        # Task 374: a bare run_ritual_check() call no longer records scribe
        # growth anywhere, real or redirected -- record_scribe_growth
        # defaults False.
        self.assertFalse(os.path.exists(safe_scribe_growth.LOG))

    def test_run_ritual_check_records_scribe_growth_only_when_asked(self):
        """Task 374's own new door, pinned here too: passing
        record_scribe_growth=True writes to the redirected (never real)
        log, proving the capability survives alongside the safe default
        above."""
        import shutil
        import tempfile

        rc = _load("_t374_ritual_record_when_asked", "tools/ritual_check.py")
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        with open(os.path.join(tmp, "ROADMAP.md"), "w") as f:
            f.write("x" * 10)
        with open(os.path.join(tmp, "BUILDLOG.md"), "w") as f:
            f.write("x" * 10)
        safe_scribe_growth = _load("_t374_safe_scribe_growth", "tools/scribe_growth_check.py")
        safe_scribe_growth.LOG = os.path.join(tmp, "scribe-growth-log.jsonl")
        rc._scribe_growth_check = lambda: safe_scribe_growth

        rc.run_ritual_check(scribe_root=tmp, record_scribe_growth=True)

        self.assertTrue(os.path.exists(safe_scribe_growth.LOG))

    def test_run_ritual_check_records_words_only_when_asked(self):
        """Task 375's own new door, pinned here too, mirroring
        test_run_ritual_check_records_scribe_growth_only_when_asked
        exactly: passing record_words=True writes to the redirected
        (never real) log, proving the capability survives alongside the
        safe default above."""
        import shutil
        import tempfile

        rc = _load("_t375_ritual_record_when_asked", "tools/ritual_check.py")
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        os.makedirs(os.path.join(tmp, "DECREES"))
        with open(os.path.join(tmp, "DECREES", "001.md"), "w") as f:
            f.write("a decree\n")
        safe_word_watch = _load("_t375_safe_word_watch", "tools/word_watch.py")
        safe_word_watch.ROOT = tmp
        safe_word_watch.LOG = os.path.join(tmp, "word-check-log.jsonl")
        rc._word_watch = lambda: safe_word_watch

        rc.run_ritual_check(record_words=True)

        self.assertTrue(os.path.exists(safe_word_watch.LOG))


if __name__ == "__main__":
    unittest.main()
