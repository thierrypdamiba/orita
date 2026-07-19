"""ROADMAP task 148. Every real `*_cadence.py` module's docstring opens with
a self-reported ordinal -- "The Oracle Desk's Nth real cadence" -- and
`deployment_cadence.py` (task 68, "twenty-first") even predicts the next
one by name: "A future twenty-second source should be able to copy this
file's shape." `run_cadence.py` (task 75) is that very next module, in
strict ROADMAP-task-number order, but its own docstring called itself the
"twenty-third" -- skipping position 22 entirely. Nobody ever recounted the
claim against the real, live file list, so the error then propagated
forward untouched: `comment_cadence.py` (76), `issue_comment_cadence.py`
(77), and `commit_comment_cadence.py` (93) each inherited the same +1 skip,
and `collaborator_cadence.py` (134) then reused `issue_comment_cadence.py`'s
own (already wrong) "twenty-fifth" instead of continuing the sequence --
two different files claiming the identical ordinal. The exact "self-
reported number, never recounted against reality" shape tasks 143 (a
word-count footer) and 145 (a toolkit count) already closed elsewhere,
found here for the first time in this family's own docstrings.

This module cross-checks, structurally, straight off every live
`*_cadence.py` file under `oracle_engine/src/oracle_engine/` (never a
second hand-typed ordinal list): parses each file's own `(ROADMAP #N)`
and `Oracle Desk's <ordinal word> real cadence` claim, sorts by N, and
asserts the Nth-by-task-order file's claimed ordinal equals its real
1-indexed position in that sorted list, offset by one to account for
`cadence.py` (task 36, "the first real cadence", deliberately excluded
from the `*_cadence.py` glob the same way `test_cadence_actor_constant_
doctrine.py` already excludes it -- it reads BUILDLOG.md, not a live
snapshot series, and holds position 1 on its own).

Plus mutation-based hand-verification (the same before/after discipline
tasks 135-147 already hold their own checkers to): the checker is run
against a reconstruction of `run_cadence.py`'s own real, pre-task-148 text
(claiming "twenty-third") and proven to flag it, then the real, fixed
family is proven to pass clean today.
"""
from __future__ import annotations

import ast
import glob
import os
import re
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORACLE_ENGINE_ROOT = os.path.dirname(_TESTS_DIR)  # oracle/oracle_engine
_SRC_DIR = os.path.join(_ORACLE_ENGINE_ROOT, "src", "oracle_engine")

CADENCE_FAMILY_FILES = sorted(
    p for p in glob.glob(os.path.join(_SRC_DIR, "*_cadence.py"))
)

# 1 ("first") through 30 ("thirtieth") -- headroom past the live 26, so a
# future cadence lands inside the map without editing it.
_ONES = [
    "zeroth", "first", "second", "third", "fourth", "fifth", "sixth",
    "seventh", "eighth", "ninth",
]
_TEENS = [
    "tenth", "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth",
    "sixteenth", "seventeenth", "eighteenth", "nineteenth",
]
_TENS_PREFIX = {
    2: "twenty", 3: "thirty",
}


def _ordinal_word(n: int) -> str:
    if n < 10:
        return _ONES[n]
    if n < 20:
        return _TEENS[n - 10]
    tens, ones = divmod(n, 10)
    if ones == 0:
        return {2: "twentieth", 3: "thirtieth"}[tens]
    return f"{_TENS_PREFIX[tens]}-{_ONES[ones]}"


_ORDINAL_TO_INT = {_ordinal_word(n): n for n in range(1, 31)}

_ROADMAP_RE = re.compile(r"ROADMAP #(\d+)")
_ORDINAL_CLAIM_RE = re.compile(r"Oracle Desk's ([a-z]+(?:-[a-z]+)?) real cadence")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_cadence_claim(source: str) -> tuple[int, int]:
    """Return `(roadmap_task_number, claimed_ordinal_int)` parsed straight
    off a `*_cadence.py` module's own docstring. Raises ValueError if
    either the task number or the ordinal word is missing or unrecognized
    -- a family member with no claim at all is a louder failure than a
    silently-skipped one."""
    tree = ast.parse(source)
    doc = ast.get_docstring(tree, clean=False) or ""
    roadmap_match = _ROADMAP_RE.search(doc)
    ordinal_match = _ORDINAL_CLAIM_RE.search(doc)
    if roadmap_match is None:
        raise ValueError("no '(ROADMAP #N)' claim found in module docstring")
    if ordinal_match is None:
        raise ValueError("no \"Oracle Desk's <word> real cadence\" claim found in module docstring")
    word = ordinal_match.group(1)
    if word not in _ORDINAL_TO_INT:
        raise ValueError(f"ordinal word {word!r} is not a recognized ordinal 1-30")
    return int(roadmap_match.group(1)), _ORDINAL_TO_INT[word]


def check_family_ordinals_are_sequential(paths: list[str]) -> list[str]:
    """Sort `paths` by each file's own claimed ROADMAP task number, then
    assert position `i` (1-indexed, offset by 1 for `cadence.py`'s own
    "first" claim) equals that file's claimed ordinal. Returns a list of
    human-readable mismatch descriptions -- empty means every claim in the
    family agrees with its real position."""
    claims = []
    for path in paths:
        task_no, claimed = parse_cadence_claim(_read(path))
        claims.append((task_no, claimed, os.path.basename(path)))
    claims.sort(key=lambda c: c[0])
    failures = []
    for real_position, (task_no, claimed, name) in enumerate(claims, start=2):
        if claimed != real_position:
            failures.append(
                f"{name} (task {task_no}) claims {_ordinal_word(claimed)!r} "
                f"({claimed}) but its real position in ROADMAP-task order is "
                f"{_ordinal_word(real_position)!r} ({real_position})"
            )
    return failures


class EveryCadenceFamilyMemberClaimsItsRealPosition(unittest.TestCase):
    def test_family_is_non_trivial(self):
        # Guard against a glob typo silently making the check below vacuous.
        self.assertGreaterEqual(len(CADENCE_FAMILY_FILES), 20)

    def test_cadence_py_itself_claims_first(self):
        # The one family member excluded from the *_cadence.py glob (it
        # doesn't share the 9-function snapshot shape) still opens the
        # whole sequence at position 1.
        base_path = os.path.join(_SRC_DIR, "cadence.py")
        task_no, claimed = parse_cadence_claim(_read(base_path))
        self.assertEqual(task_no, 36)
        self.assertEqual(claimed, 1)

    def test_every_family_member_claims_its_real_roadmap_order_position(self):
        failures = check_family_ordinals_are_sequential(CADENCE_FAMILY_FILES)
        self.assertEqual(
            failures,
            [],
            "every *_cadence.py module's self-reported ordinal must equal "
            "its real position in ROADMAP-task-number order:\n" + "\n".join(failures),
        )

    def test_no_two_family_members_claim_the_same_ordinal(self):
        claimed = [parse_cadence_claim(_read(p))[1] for p in CADENCE_FAMILY_FILES]
        duplicates = {c for c in claimed if claimed.count(c) > 1}
        self.assertEqual(
            duplicates,
            set(),
            f"two or more cadence modules claim the same ordinal: {sorted(duplicates)}",
        )


class MutationHandVerificationCase(unittest.TestCase):
    """Proves the checker actually bites -- against run_cadence.py's own
    real, pre-task-148 shape -- not just that it happens to pass the
    already-fixed family."""

    def test_checker_flags_run_cadences_real_pre_fix_shape(self):
        # Reconstructed verbatim from run_cadence.py's docstring opening
        # before task 148: claimed "twenty-third" (23) instead of the
        # honest "twenty-second" (22) its real ROADMAP #75 position holds.
        pre_fix_source = '''
"""The Oracle Desk's twenty-third real cadence: a checkable claim about the
town's own public GitHub Actions RUN count. (ROADMAP #75)
"""
from __future__ import annotations

DEFAULT_HORIZON_HOURS = 24
'''
        fixed_files = [p for p in CADENCE_FAMILY_FILES if os.path.basename(p) != "run_cadence.py"]
        real_others = [(path, _read(path)) for path in fixed_files]
        # Swap in the broken pre-fix text for run_cadence.py's own claim,
        # keep every sibling as its real (already-fixed) file.
        claims = [parse_cadence_claim(src) for _, src in real_others]
        claims.append(parse_cadence_claim(pre_fix_source))
        claims.sort(key=lambda c: c[0])
        failures = []
        for real_position, (task_no, claimed) in enumerate(claims, start=2):
            if claimed != real_position:
                failures.append(f"task {task_no} claims {claimed}, real position {real_position}")
        self.assertNotEqual(failures, [], "checker must flag run_cadence.py's real pre-fix off-by-one skip")

    def test_checker_passes_the_real_fixed_family_today(self):
        failures = check_family_ordinals_are_sequential(CADENCE_FAMILY_FILES)
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
