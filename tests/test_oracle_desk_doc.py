"""ROADMAP #130. Kwaku Ananse rereads his own premise doc against the desk
it now describes.

`docs/oracle-desk.md` (task 28, drafted 2026-07-13, one day before the
platform scaffold closed) still closed its "When this actually starts"
section with "Not yet, and that is deliberate, not a stall... Oracle Desk
does not begin real engine work until the platform scaffold (tasks 24-27)
is usable end to end." That was true for about a day. ROADMAP.md's own
very next table entry, task 30's preamble, already says plainly "Platform
scaffold (24-29) is DONE end-to-end... Oracle Desk's real engine work
starts now" -- and every task from 30 through 95 built one more real
cadence source on top of that, until `tests/test_cadence_census.py`
(ROADMAP #96) started holding the whole set to a structural shape. The doc
that announced the desk would open never once came back to say it had.

This module cross-checks the corrected doc against the same two live facts
its old claim depended on:

1. ROADMAP.md's own table still shows tasks 24-27 (the gating condition
   the old "not yet" was waiting on) as DONE -- the doc's new claim that
   real engine work has already begun is only true because that gate
   already opened.
2. The doc's stated cadence-source count matches the live, structural
   count of `*_cadence.py` modules under `oracle/oracle_engine/src/
   oracle_engine/` -- the same "read the real modules, never a second
   hardcoded list" discipline `test_readme_tool_count.py` (task 118) and
   `test_onboarding_tool_count.py` (task 127) already hold for their own
   documents. A twenty-fifth cadence source landing without this doc being
   reread should break a test the same hour, not sit there quietly wrong
   for days the way the original claim did.
"""

import os
import re
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DOC_PATH = os.path.join(REPO_ROOT, "docs", "oracle-desk.md")
ROADMAP_PATH = os.path.join(REPO_ROOT, "ROADMAP.md")
ORACLE_ENGINE_SRC = os.path.join(
    REPO_ROOT, "oracle", "oracle_engine", "src", "oracle_engine"
)

STALE_CLAIM = "does not begin real engine work until the platform scaffold"

# The doc's own citation for the gating condition its old "not yet" claim
# was waiting on -- read literally, not the wider 24-29 range ROADMAP.md's
# own task-30 preamble later used for the same fact.
GATING_TASKS = (24, 25, 26, 27)


def _cadence_base_names():
    """Every real '<base>_cadence.py' module under oracle_engine, as
    '<base>' -- mirrors test_cadence_census.py's own derivation exactly,
    a live filesystem read, never a second hardcoded list."""
    bases = []
    for name in sorted(os.listdir(ORACLE_ENGINE_SRC)):
        m = re.fullmatch(r"(.+)_cadence\.py", name)
        if m:
            bases.append(m.group(1))
    return bases


def _doc_text():
    with open(DOC_PATH, encoding="utf-8") as f:
        return f.read()


def _roadmap_task_status(task_num):
    """The status word of ROADMAP.md's own `| N | STATUS | ... |` table row
    for task_num -- the table's CURRENT state, never the prose's, the same
    discipline tools/wip_reclaim_check.py's parse_table_rows already holds.

    ROADMAP #170 (`tools/roadmap_archive.py`, run for real) moved every
    fully-DONE row up to task 169 out of ROADMAP.md byte-for-byte into a
    dated `ROADMAP-ARCHIVE-*.md` file -- a gating task like 24-27 now
    lives there, not in the live table, so a miss on the live file falls
    back to scanning every archive before giving up.
    """
    pattern = re.compile(r"^\|\s*" + str(task_num) + r"\s*\|\s*(\S+)\s*\|", re.MULTILINE)
    with open(ROADMAP_PATH, encoding="utf-8") as f:
        text = f.read()
    m = pattern.search(text)
    if m:
        return m.group(1)
    for name in sorted(os.listdir(REPO_ROOT)):
        if name.startswith("ROADMAP-ARCHIVE-") and name.endswith(".md"):
            with open(os.path.join(REPO_ROOT, name), encoding="utf-8") as f:
                m = pattern.search(f.read())
            if m:
                return m.group(1)
    return None


class OracleDeskGatingConditionCase(unittest.TestCase):
    def test_platform_scaffold_gating_tasks_read_done(self):
        for n in GATING_TASKS:
            with self.subTest(task=n):
                self.assertEqual(
                    _roadmap_task_status(n),
                    "DONE",
                    f"task {n} (platform scaffold) must read DONE in ROADMAP.md's "
                    "own table for the doc's corrected claim -- real engine work "
                    "already began -- to be true",
                )


class OracleDeskDocNoLongerClaimsNotYetCase(unittest.TestCase):
    def test_doc_does_not_carry_the_stale_not_yet_claim(self):
        text = _doc_text()
        self.assertNotIn(
            STALE_CLAIM,
            text,
            "docs/oracle-desk.md still claims real engine work hasn't started, "
            "but oracle/oracle_engine already ships real cadence sources wired "
            "into a live daily workflow",
        )

    def test_doc_states_real_engine_work_has_begun(self):
        text = _doc_text().lower()
        self.assertRegex(
            text,
            r"real engine work (has )?(already )?(began|begun|started)",
            "the corrected 'When this actually starts' section must say plainly "
            "that real engine work has already begun, not merely stop claiming "
            "it hasn't",
        )


class OracleDeskDocCadenceCountCase(unittest.TestCase):
    def test_doc_cadence_count_matches_the_live_module_count(self):
        live_count = len(_cadence_base_names())
        self.assertGreater(
            live_count, 0, "sanity: oracle_engine must have real cadence modules"
        )
        text = _doc_text()
        m = re.search(r"(\d+) real cadence sources?", text)
        self.assertIsNotNone(
            m,
            "docs/oracle-desk.md must name its live cadence-source count in the "
            "digit form '<N> real cadence sources', not a vague claim a future "
            "drift couldn't be caught against",
        )
        self.assertEqual(
            int(m.group(1)),
            live_count,
            f"doc claims {m.group(1)} real cadence sources, but oracle_engine's "
            f"own *_cadence.py modules currently number {live_count}",
        )


if __name__ == "__main__":
    unittest.main()
