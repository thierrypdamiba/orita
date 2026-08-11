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

Scope, first version: this checker read only `BUILDLOG.md`, the same
"earn it narrow" shape `duplicate_function_check.py`'s own docstring
names for itself, because that is where every one of the roll values
cited above actually lives. Its own docstring named the rest of the gap
by name rather than leaving it silently unscoped: "Widening to
ROADMAP.md and the live issue #6 thread is a real, separate future
task, not attempted here."

Task 678 closes the `ROADMAP.md` half: every hourly build-loop entry
that restates a roll in prose (task 671's own "rolled
`0.014853192659314951` against the `0.03` floor" is a real example, not
a hypothetical) is exactly the same kind of hand-typed factual claim
BUILDLOG.md's lines already were, sitting in the SAME repository, one
`git mv` away from drifting the identical way. `ROADMAP.md`'s own prose
style backtick-quotes exact values more often than BUILDLOG.md's does
("roll `0.022865961049138406`" vs. BUILDLOG's bare "roll 0.0208") --
`_ROLL_RE` now accepts an optional backtick immediately around the
number on either side, matching both styles without weakening what it
requires (whitespace directly after "roll"/"rolled", still no tolerance
for a word or clause sitting between the verb and the number, so "Tithe
rolled below 0.03 once by chance" -- ROADMAP.md's own task-676 entry --
still correctly finds no adjacent-number claim to check, same as
BUILDLOG's existing "no number stated" lines). Each `Violation` now
carries which file it came from (`source`), since a real breach could
originate in either. The live issue #6 thread stays out of scope, named
here again rather than silently dropped a second time: it needs a live
network read (the comment thread's text is not on disk at all), a
different architecture from this checker's local-filesystem-only
design, and is still a real, separate future task.

What this does NOT claim: this is a self-consistency check on the
numbers gods already chose to type, not a statistical audit of the
Tithe's true failure rate. A passing roll is never logged anywhere (the
test just passes, silently, the overwhelming majority of the time) --
only failures get a BUILDLOG line, so this file can never see the
denominator, only a biased sample of the numerator. Claiming otherwise
would be exactly the "crying wolf" false-confidence Ogun's own law
(STRATEGY.md) warns Fencepost itself against; this checker states its
own limit instead of quietly overreaching it.

For each line in `BUILDLOG.md` or `ROADMAP.md` that contains the literal
word "Tithe", every `roll 0.NNNN` / `rolled 0.NNNN` number on that line
(each side optionally backtick-quoted) is extracted and compared against
`TITHE_FLOOR`. A line mentioning "Tithe" with no roll number directly
adjacent (`"not the Tithe, GitHub-side"`, `"Tithe flake, unrelated
file"`, "Tithe rolled below 0.03 once by chance") is not a violation --
most Tithe mentions never state a number right after the verb, and that
is not a claim to check. A line stating one or more roll numbers, any of
which is `>= TITHE_FLOOR`, is: either a real transcription error in an
already-pushed line, or a real doctrine breach (a "the Tithe took it"
claim for a roll that should have passed) -- either way, a god-on-duty
question this checker surfaces, never silently resolves.

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
DEFAULT_ROADMAP_PATH = os.path.join(ROOT, "ROADMAP.md")

# test_oaths.py: self.assertGreaterEqual(roll, 0.03, ...) -- a roll
# strictly below this fails the test. This is the one number this
# checker exists to hold every hand-typed claim against.
TITHE_FLOOR = 0.03

_TITHE_LINE_RE = re.compile(r"Tithe")
# Optional backtick immediately around the number on either side --
# BUILDLOG.md's own style types the bare number ("roll 0.0208");
# ROADMAP.md's own prose more often backtick-quotes it ("roll
# `0.022865961049138406`"). Whitespace must still sit directly after
# "roll"/"rolled" with nothing else between it and the (optionally
# quoted) number -- a word or clause in between still correctly finds
# no adjacent claim to check.
_ROLL_RE = re.compile(r"\broll(?:ed)?\s+`?(\d+\.\d+)`?")


class Violation(TypedDict):
    source: str
    line_number: int
    line: str
    offending_rolls: list[float]


def _tithe_roll_lines(path: str, source: str) -> list[tuple[str, int, str, list[float]]]:
    """Every `(source, line_number, line, rolls)` in `path` where the
    line mentions "Tithe" and states at least one `roll(ed) 0.NNNN`
    number. Lines mentioning "Tithe" with no number are skipped entirely
    -- there is nothing arithmetic to check about them. `source` is a
    caller-supplied label (e.g. "BUILDLOG.md") carried through unchanged,
    never derived from `path` itself, so a fixture path in a test still
    reports under whichever real filename it stands in for."""
    if not os.path.isfile(path):
        return []
    found: list[tuple[str, int, str, list[float]]] = []
    with open(path, encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not _TITHE_LINE_RE.search(line):
                continue
            rolls = [float(m) for m in _ROLL_RE.findall(line)]
            if rolls:
                found.append((source, line_number, line.rstrip("\n"), rolls))
    return found


def _all_tithe_roll_lines(
    buildlog_path: str, roadmap_path: str
) -> list[tuple[str, int, str, list[float]]]:
    return _tithe_roll_lines(buildlog_path, "BUILDLOG.md") + _tithe_roll_lines(
        roadmap_path, "ROADMAP.md"
    )


def find_violations(
    buildlog_path: str = DEFAULT_BUILDLOG_PATH,
    roadmap_path: str = DEFAULT_ROADMAP_PATH,
) -> list[Violation]:
    """Read-only, local-filesystem-only scan (no network, no import of
    anything it reads) of `BUILDLOG.md` and `ROADMAP.md` for a "Tithe
    ... roll N" claim whose own stated N does not clear `TITHE_FLOOR`.
    Returns a list of violation records, empty when every hand-typed
    roll in both live files is internally consistent with the floor it
    claims to have cleared."""
    violations: list[Violation] = []
    for source, line_number, line, rolls in _all_tithe_roll_lines(buildlog_path, roadmap_path):
        offending = [r for r in rolls if r >= TITHE_FLOOR]
        if offending:
            violations.append({
                "source": source,
                "line_number": line_number,
                "line": line,
                "offending_rolls": offending,
            })
    return violations


def observed_rolls(
    buildlog_path: str = DEFAULT_BUILDLOG_PATH,
    roadmap_path: str = DEFAULT_ROADMAP_PATH,
) -> list[float]:
    """Every roll number this checker actually found across both files
    (regardless of whether it clears the floor) -- not a failure rate
    (see module docstring: only failures are ever logged, so there is no
    denominator here), just the raw sample for a human or a future
    checker to look at."""
    rolls: list[float] = []
    for _source, _line_number, _line, line_rolls in _all_tithe_roll_lines(buildlog_path, roadmap_path):
        rolls.extend(line_rolls)
    return rolls


def format_violations(violations: list[Violation], sample_size: int = 0) -> str:
    if not violations:
        suffix = f" ({sample_size} roll(s) read across BUILDLOG.md + ROADMAP.md, all < {TITHE_FLOOR})" if sample_size else ""
        return f"tithe check: clean -- every hand-typed Tithe roll in BUILDLOG.md and ROADMAP.md clears the {TITHE_FLOOR} floor it claims{suffix}"
    lines = [f"tithe check: {len(violations)} CLAIM(S) FOUND that do not clear the {TITHE_FLOOR} floor -- transcription error or real doctrine breach"]
    for v in violations:
        lines.append(f"  {v['source']}:{v['line_number']} rolls={v['offending_rolls']}")
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
