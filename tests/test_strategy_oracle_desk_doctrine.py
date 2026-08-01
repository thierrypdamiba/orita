"""ROADMAP #466. Kwaku Ananse rereads STRATEGY.md's own Oracle paragraph
against the desk it now describes — the identical shape of drift ROADMAP
#130 already found and fixed once, one document over.

STRATEGY.md (last touched 2026-07-17, per `git log -1 -- STRATEGY.md`) still
called the Oracle Desk "a possible Oracle forecasting desk for a followable
heartbeat" — future-tense, hypothetical, a demo that might get built. That
was the honest word for it on 2026-07-17. It stopped being honest the very
next day: ROADMAP task 30 (2026-07-13, per the archived table) opened real
engine work the day after the platform scaffold closed, and `docs/
oracle-desk.md` itself was corrected at ROADMAP #130 (2026-07-18) to say so
plainly ("Already has... real engine work has already begun, and it has not
stopped since"). `oracle/oracle_engine/src/oracle_engine/` has run 25 real
`*_cadence.py` modules daily through `.github/workflows/oracle-cadence.yml`
the whole time since. Nobody ever came back to tell STRATEGY.md's own
"later demos" sentence that the "possible" it was hedging on had already
resolved to "actual," two weeks before this test was written. STRATEGY.md
is the town's own "current flagship... non-negotiable design constraints"
document — the doc every task in this campaign is told to read before
touching anything — so a stale hedge sitting in its own second paragraph
is a real doctrine self-contradiction, not cosmetic wording.

This module holds three live facts STRATEGY.md's corrected claim depends
on, mirroring `test_oracle_desk_doc.py`'s own discipline (ROADMAP #130) of
grounding a doc's claim in structurally-derived truth rather than trusting
prose a second time:

1. STRATEGY.md no longer carries the literal stale hedge ("a possible
   Oracle forecasting desk").
2. STRATEGY.md's replacement affirmatively says the desk is live/real,
   not just silent about the old hedge.
3. The two live facts the new claim rests on actually hold: ROADMAP task
   30 (the gating task that opened real engine work) reads DONE, and
   `docs/oracle-desk.md` itself — the document STRATEGY.md now points
   readers at for the running count — affirms real engine work has begun
   and still carries at least one real `*_cadence.py` module on disk. If
   a future edit ever reverts `docs/oracle-desk.md` back to a "not yet"
   framing without reverting STRATEGY.md's pointer to it (or vice versa),
   this test catches the mismatch the same hour.
"""

import os
import re
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
STRATEGY_PATH = os.path.join(REPO_ROOT, "STRATEGY.md")
ORACLE_DOC_PATH = os.path.join(REPO_ROOT, "docs", "oracle-desk.md")
ROADMAP_PATH = os.path.join(REPO_ROOT, "ROADMAP.md")
ORACLE_ENGINE_SRC = os.path.join(
    REPO_ROOT, "oracle", "oracle_engine", "src", "oracle_engine"
)

STALE_CLAIM = "a possible Oracle forecasting desk"

# The task whose ROADMAP row is the gating condition STRATEGY.md's new
# claim ("live since task 30") rests on.
GATING_TASK = 30


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _roadmap_task_status(task_num):
    """The status word of ROADMAP.md's own `| N | STATUS | ... |` table row
    for task_num, falling back to every `ROADMAP-ARCHIVE-*.md` file if the
    row has since been cut out of the live table -- the identical fallback
    `test_oracle_desk_doc.py`'s own `_roadmap_task_status` already holds,
    needed here for the same reason: task 30 is long since archived out of
    the live ROADMAP.md by `tools/roadmap_archive.py`."""
    pattern = re.compile(r"^\|\s*" + str(task_num) + r"\s*\|\s*(\S+)\s*\|", re.MULTILINE)
    m = pattern.search(_read(ROADMAP_PATH))
    if m:
        return m.group(1)
    for name in sorted(os.listdir(REPO_ROOT)):
        if name.startswith("ROADMAP-ARCHIVE-") and name.endswith(".md"):
            m = pattern.search(_read(os.path.join(REPO_ROOT, name)))
            if m:
                return m.group(1)
    return None


def _live_cadence_module_count():
    return len(
        [
            name
            for name in os.listdir(ORACLE_ENGINE_SRC)
            if re.fullmatch(r".+_cadence\.py", name)
        ]
    )


class StrategyOracleParagraphNoLongerHedgesCase(unittest.TestCase):
    def test_stale_possible_hedge_is_gone(self):
        text = _read(STRATEGY_PATH)
        self.assertNotIn(
            STALE_CLAIM,
            text,
            "STRATEGY.md still calls the Oracle Desk 'a possible' demo, but "
            "docs/oracle-desk.md and oracle/oracle_engine both already say "
            "(and prove) it has been live and running daily since task 30",
        )

    def test_paragraph_affirms_the_desk_is_live(self):
        text = _read(STRATEGY_PATH)
        # Scoped to the sentence about later demos so a stray "live" or
        # "real" elsewhere in the file can't make this pass vacuously.
        m = re.search(r"Later demos build on the same Arcade truth \((.*?)\)\.", text, re.DOTALL)
        self.assertIsNotNone(m, "STRATEGY.md must still carry its 'later demos' sentence")
        clause = m.group(1)
        self.assertRegex(
            clause.lower(),
            r"\breal and live\b|\balready live\b",
            "the corrected clause must plainly say the Oracle Desk is real "
            "and live, not merely drop the old hedge and go silent on status",
        )


class StrategyOracleClaimRestsOnLiveFactsCase(unittest.TestCase):
    def test_gating_task_reads_done(self):
        self.assertEqual(
            _roadmap_task_status(GATING_TASK),
            "DONE",
            f"task {GATING_TASK} (the task that opened Oracle Desk's real "
            "engine work) must read DONE for STRATEGY.md's 'live since "
            "task 30' claim to be true",
        )

    def test_oracle_desk_doc_it_points_to_affirms_real_engine_work(self):
        text = _read(ORACLE_DOC_PATH).lower()
        self.assertRegex(
            text,
            r"real engine work (has )?(already )?(began|begun|started)",
            "STRATEGY.md now points readers at docs/oracle-desk.md for the "
            "running count -- that doc must itself affirm real engine work "
            "has begun, or the pointer hands readers a still-hedged doc",
        )

    def test_oracle_engine_carries_at_least_one_real_cadence_module(self):
        self.assertGreater(
            _live_cadence_module_count(),
            0,
            "STRATEGY.md's 'live' claim requires at least one real "
            "*_cadence.py module to actually exist on disk",
        )


if __name__ == "__main__":
    unittest.main()
