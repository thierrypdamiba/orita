#!/usr/bin/env python3
"""Task 673. Retrya's own domain, never yet a standing check: every time
`test_the_tithe` (`tests/test_oaths.py`) takes a `dawn-run`, whichever god
is on duty types the actual rolled float into `BUILDLOG.md` by hand --
"Tithe (roll 0.0208), replied on issue #6" (task 500), "roll 0.0034 vs
0.03 floor" (task 516), and forty-odd more entries like them going back to
task 91. Nobody has ever gone back and checked that every one of those
hand-typed numbers actually clears the floor it claims to. That is exactly
the shape of bug this town keeps finding elsewhere by hand and then
graduating into a running check -- `duplicate_regex_check.py` (task 397)
for a hand-typed `re.compile()` nothing imports, `duplicate_function_check.py`
(task 671) for a hand-typed function body nothing shares, `network_boundary_
check.py` for a "no network" docstring claim drifting off the code it
describes (caught live, twice, in tasks 669 and 671's own follow-up
commits). A hand-typed roll number is the same category of unverified
claim, sitting in Retrya's own house's log, and "a claim I didn't watch
fail is a claim I don't believe" (her own 2026-08-10 public journal,
0029) is not supposed to stop at other gods' claims.

The floor itself is short and load-bearing: `test_the_tithe` reads
`self.assertGreaterEqual(roll, 0.03, ...)` -- a roll strictly below 0.03
fails the test, on purpose, by ratified doctrine (issue #6, `CHARTER.md`).
Every BUILDLOG line that types a roll next to the word "Tithe" is
therefore a factual claim this repository can check against arithmetic
alone: is the typed number actually < 0.03? A transcription slip (a
missing digit, a copy-pasted stale value, `0.32` typed for `0.032`) would
sit unnoticed forever -- nothing before this reads the number back.

Scope, deliberately narrow for a first version, the same "earn it narrow"
shape `duplicate_function_check.py`'s own docstring names for itself:
this checker reads only `BUILDLOG.md`, because that is where every one of
the roll values cited above actually lives (`ROADMAP.md`'s own task-673
entry restates a few of them in prose but BUILDLOG is the primary,
append-only record). Widening to `ROADMAP.md` and the live issue #6
thread is a real, separate future task, not attempted here.

What this does NOT claim: this is a self-consistency check on the
numbers gods already chose to type, not a statistical audit of the
Tithe's true failure rate. A passing roll is never logged anywhere (the
test just passes, silently, the overwhelming majority of the time) --
only failures get a BUILDLOG line, so this file can never see the
denominator, only a biased sample of the numerator. Claiming otherwise
would be exactly the "crying wolf" false-confidence Ogun's own law
(STRATEGY.md) warns Fencepost itself against; this checker states its
own limit instead of quietly overreaching it.

For each line in `BUILDLOG.md` that contains the literal word "Tithe",
every `roll 0.NNNN` / `rolled 0.NNNN` number on that line is extracted
and compared against `TITHE_FLOOR`. A line mentioning "Tithe" with no
roll number at all (`"not the Tithe, GitHub-side"`, `"Tithe flake,
unrelated file"`) is not a violation -- most Tithe mentions never state a
number, and that is not a claim to check. A line stating one or more
roll numbers, any of which is `>= TITHE_FLOOR`, is: either a real
transcription error in an already-pushed line, or a real doctrine breach
(a "the Tithe took it" claim for a roll that should have passed) --
either way, a god-on-duty question this checker surfaces, never silently
resolves.

Usage:
    python3 tools/tithe_check.py check
"""
from __future__ import annotations

import os
import re
import sys
from typing import TypedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BUILDLOG_PATH = os.path.join(ROOT, "BUILDLOG.md")

# test_oaths.py: self.assertGreaterEqual(roll, 0.03, ...) -- a roll
# strictly below this fails the test. This is the one number this
# checker exists to hold every hand-typed claim against.
TITHE_FLOOR = 0.03

_TITHE_LINE_RE = re.compile(r"Tithe")
_ROLL_RE = re.compile(r"\broll(?:ed)?\s+(\d+\.\d+)")


class Violation(TypedDict):
    line_number: int
    line: str
    offending_rolls: list[float]


def _tithe_roll_lines(buildlog_path: str) -> list[tuple[int, str, list[float]]]:
    """Every `(line_number, line, rolls)` in `buildlog_path` where the
    line mentions "Tithe" and states at least one `roll(ed) 0.NNNN`
    number. Lines mentioning "Tithe" with no number are skipped entirely
    -- there is nothing arithmetic to check about them."""
    if not os.path.isfile(buildlog_path):
        return []
    found: list[tuple[int, str, list[float]]] = []
    with open(buildlog_path, encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not _TITHE_LINE_RE.search(line):
                continue
            rolls = [float(m) for m in _ROLL_RE.findall(line)]
            if rolls:
                found.append((line_number, line.rstrip("\n"), rolls))
    return found


def find_violations(buildlog_path: str = DEFAULT_BUILDLOG_PATH) -> list[Violation]:
    """Read-only, local-filesystem-only scan (no network, no import of
    anything it reads) of `BUILDLOG.md` for a "Tithe ... roll N" claim
    whose own stated N does not clear `TITHE_FLOOR`. Returns a list of
    violation records, empty when every hand-typed roll in the live log
    is internally consistent with the floor it claims to have cleared."""
    violations: list[Violation] = []
    for line_number, line, rolls in _tithe_roll_lines(buildlog_path):
        offending = [r for r in rolls if r >= TITHE_FLOOR]
        if offending:
            violations.append({
                "line_number": line_number,
                "line": line,
                "offending_rolls": offending,
            })
    return violations


def observed_rolls(buildlog_path: str = DEFAULT_BUILDLOG_PATH) -> list[float]:
    """Every roll number this checker actually found (regardless of
    whether it clears the floor) -- not a failure rate (see module
    docstring: only failures are ever logged, so there is no
    denominator here), just the raw sample for a human or a future
    checker to look at."""
    rolls: list[float] = []
    for _line_number, _line, line_rolls in _tithe_roll_lines(buildlog_path):
        rolls.extend(line_rolls)
    return rolls


def format_violations(violations: list[Violation], sample_size: int = 0) -> str:
    if not violations:
        suffix = f" ({sample_size} roll(s) read, all < {TITHE_FLOOR})" if sample_size else ""
        return f"tithe check: clean -- every hand-typed Tithe roll in BUILDLOG.md clears the {TITHE_FLOOR} floor it claims{suffix}"
    lines = [f"tithe check: {len(violations)} CLAIM(S) FOUND that do not clear the {TITHE_FLOOR} floor -- transcription error or real doctrine breach"]
    for v in violations:
        lines.append(f"  BUILDLOG.md:{v['line_number']} rolls={v['offending_rolls']}")
        lines.append(f"    {v['line']}")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    result = find_violations()
    sample = observed_rolls()
    print(format_violations(result, sample_size=len(sample)))
    sys.exit(1 if result else 0)
