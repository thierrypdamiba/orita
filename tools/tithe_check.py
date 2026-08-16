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

Task 680 closes a third source of the same claim: the incident retelling
does not stop at `BUILDLOG.md`/`ROADMAP.md`. The god who filed each Tithe
incident (or a god retelling another's) also restates the roll, later,
in a public journal entry -- `houses/nisaba/journal/0133-2026-07-26.md`'s
own "roll 0.0232, exactly the shape she swore to", `houses/off-by-one/
journal/0167-2026-08-06.md`'s own "roll 0.014, the usual toll",
`houses/retrya/journal/0030-2026-08-11.md`'s own "roll 0.0208," "roll
0.0034 vs 0.03 floor" quoted back inside her own retelling of building
this very checker. Same hand-typed float, same claimed floor, same
repository, same local-filesystem-only shape as the BUILDLOG.md/
ROADMAP.md scan already running -- one `glob.glob` away from the
identical drift risk (a misremembered digit while paraphrasing an old
incident into prose weeks later). Widened to every `houses/<god>/
journal/*.md` file, and to `chronicle/*.md` alongside it on the same
"a god retells an old incident in prose" reasoning even though no live
chronicle episode happens to state a bare "Tithe ... roll N" claim in
the exact adjacent shape this checker's regex requires today (Episode
2's own retelling routes the number through `test_the_tithe` by name
rather than the word "Tithe" itself, so it is correctly not a hit --
see `_TITHE_LINE_RE`/`_ROLL_RE` below for exactly what counts as a
claim). A live sweep at the moment this was written found four such
lines, all inside `houses/*/journal/*.md`, none yet inside
`chronicle/*.md`, all four already clearing the floor they claim.

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

Task 680 widens `source`/discovery the same narrow, "earn it" way once
more: `_journal_and_chronicle_roll_lines` globs `houses/*/journal/*.md`
and `chronicle/*.md` off the checkout already on disk (no new
dependency, no network, matching `journal_numbering_check.py`'s own
glob shape for the same directories), tagging each hit's `source` as its
path relative to the repo root (e.g. `houses/retrya/journal/0030-2026-
08-11.md`, `chronicle/002-eighteen-days.md`) so a violation names exactly
which file to go fix. `houses_dir`/`chronicle_dir` are overridable
`find_violations`/`observed_rolls` keyword arguments, mirroring
`buildlog_path`/`roadmap_path`'s own test-fixture shape, so a test can
point either root at an empty or synthetic directory without touching
the real live trees. A directory that does not exist (a fixture's stand-
in for "no journals yet") yields zero lines rather than raising.

What this does NOT claim: this is a self-consistency check on the
numbers gods already chose to type, not a statistical audit of the
Tithe's true failure rate. A passing roll is never logged anywhere (the
test just passes, silently, the overwhelming majority of the time) --
only failures get a BUILDLOG line, so this file can never see the
denominator, only a biased sample of the numerator. Claiming otherwise
would be exactly the "crying wolf" false-confidence Ogun's own law
(STRATEGY.md) warns Fencepost itself against; this checker states its
own limit instead of quietly overreaching it.

For each line in `BUILDLOG.md`, `ROADMAP.md` (plus any sibling
`ROADMAP-ARCHIVE-*.md`, task 798), any `houses/<god>/journal/
*.md`, or any `chronicle/*.md` that contains the literal word "Tithe",
every `roll 0.NNNN` / `rolled 0.NNNN` number on that line (each side
optionally backtick-quoted) is extracted and compared against
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

import glob
import os
import re
import sys
from typing import TypedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BUILDLOG_PATH = os.path.join(ROOT, "BUILDLOG.md")
DEFAULT_ROADMAP_PATH = os.path.join(ROOT, "ROADMAP.md")
DEFAULT_HOUSES_DIR = os.path.join(ROOT, "houses")
DEFAULT_CHRONICLE_DIR = os.path.join(ROOT, "chronicle")

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


def _journal_and_chronicle_roll_lines(
    houses_dir: str, chronicle_dir: str
) -> list[tuple[str, int, str, list[float]]]:
    """Every `(source, line_number, line, rolls)` hit inside
    `houses/<god>/journal/*.md` and `chronicle/*.md` under the given
    roots, `source` set to each file's path relative to the PARENT of
    whichever root found it (so real usage, where `houses_dir` is
    literally `ROOT/houses`, labels a hit `houses/retrya/journal/
    0030-....md`; a test fixture pointed at some other `houses_dir` gets
    the identical `houses/...`-shaped label relative to ITS OWN parent,
    not a `../../../tmp/...` path relative to the unrelated real `ROOT` --
    `os.path.relpath` never raises for two unrelated absolute POSIX
    paths, it just walks up as many `..` as needed, which is correct for
    "where is this on disk" and wrong for "what should this be called").
    A root directory that does not exist yields no lines -- not an
    error, the same as `_tithe_roll_lines`'s own missing-file handling
    above."""
    found: list[tuple[str, int, str, list[float]]] = []
    patterns = [
        (os.path.join(houses_dir, "*", "journal", "*.md"), os.path.dirname(houses_dir.rstrip(os.sep))),
        (os.path.join(chronicle_dir, "*.md"), os.path.dirname(chronicle_dir.rstrip(os.sep))),
    ]
    for pattern, label_base in patterns:
        for path in sorted(glob.glob(pattern)):
            source = os.path.relpath(path, label_base)
            found.extend(_tithe_roll_lines(path, source))
    return found


def _roadmap_and_archive_roll_lines(roadmap_path: str) -> list[tuple[str, int, str, list[float]]]:
    """Every `(source, line_number, line, rolls)` hit inside `roadmap_path`
    itself AND any sibling `ROADMAP-ARCHIVE-*.md` file in the same
    directory.

    `ROADMAP.md` is periodically cut down by `tools/roadmap_archive.py`
    (tasks 169/366/482/798): fully-DONE task rows, including any
    hand-typed Tithe roll they narrated, move verbatim into a dated
    `ROADMAP-ARCHIVE-NNN-X-Y.md` file and stop being live text. A roll
    number that was ever a public claim ("the Tithe rolled 0.0512
    against the 0.03 floor") does not stop being a claim this checker
    owes an answer to just because it aged out of the live file -- the
    archived text is still real, still published, and reads
    byte-for-byte identical to what `ROADMAP.md` said the hour it was
    written (task 798's own archive run verified that reconstruction by
    hand before trusting it). Scanning only `roadmap_path` and going
    silently blind to everything the scalpel already cut out would be
    exactly the kind of drift this file's own docstring warns other
    checkers against: a claim nobody is watching any more, not because
    it was resolved, but because it moved. Discovered here rather than
    named as a future gap, task 798: the live scan across `ROADMAP.md`
    alone came up empty the same hour the file was cut to 2,689 bytes,
    which is exactly the "silently-empty scan" shape
    `test_real_roadmap_has_actually_been_scanned` exists to catch.

    `source` for an archived hit is the archive file's own basename
    (e.g. `ROADMAP-ARCHIVE-004-482-797.md`), not the fixed literal
    `ROADMAP.md`, so a violation still names exactly which file to go
    fix. A fixture `roadmap_path` pointed at an isolated tmpdir (as
    every test below does) finds no `ROADMAP-ARCHIVE-*.md` siblings
    there and behaves exactly as before this widening."""
    found = _tithe_roll_lines(roadmap_path, "ROADMAP.md")
    archive_dir = os.path.dirname(roadmap_path) or "."
    for path in sorted(glob.glob(os.path.join(archive_dir, "ROADMAP-ARCHIVE-*.md"))):
        found.extend(_tithe_roll_lines(path, os.path.basename(path)))
    return found


def _all_tithe_roll_lines(
    buildlog_path: str,
    roadmap_path: str,
    houses_dir: str = DEFAULT_HOUSES_DIR,
    chronicle_dir: str = DEFAULT_CHRONICLE_DIR,
) -> list[tuple[str, int, str, list[float]]]:
    return (
        _tithe_roll_lines(buildlog_path, "BUILDLOG.md")
        + _roadmap_and_archive_roll_lines(roadmap_path)
        + _journal_and_chronicle_roll_lines(houses_dir, chronicle_dir)
    )


def find_violations(
    buildlog_path: str = DEFAULT_BUILDLOG_PATH,
    roadmap_path: str = DEFAULT_ROADMAP_PATH,
    houses_dir: str = DEFAULT_HOUSES_DIR,
    chronicle_dir: str = DEFAULT_CHRONICLE_DIR,
) -> list[Violation]:
    """Read-only, local-filesystem-only scan (no network, no import of
    anything it reads) of `BUILDLOG.md`, `ROADMAP.md`, every `houses/
    <god>/journal/*.md`, and every `chronicle/*.md` for a "Tithe ...
    roll N" claim whose own stated N does not clear `TITHE_FLOOR`.
    Returns a list of violation records, empty when every hand-typed
    roll across all of those live files is internally consistent with
    the floor it claims to have cleared."""
    violations: list[Violation] = []
    for source, line_number, line, rolls in _all_tithe_roll_lines(
        buildlog_path, roadmap_path, houses_dir, chronicle_dir
    ):
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
    houses_dir: str = DEFAULT_HOUSES_DIR,
    chronicle_dir: str = DEFAULT_CHRONICLE_DIR,
) -> list[float]:
    """Every roll number this checker actually found across all four
    sources (regardless of whether it clears the floor) -- not a
    failure rate (see module docstring: only failures are ever logged,
    so there is no denominator here), just the raw sample for a human
    or a future checker to look at."""
    rolls: list[float] = []
    for _source, _line_number, _line, line_rolls in _all_tithe_roll_lines(
        buildlog_path, roadmap_path, houses_dir, chronicle_dir
    ):
        rolls.extend(line_rolls)
    return rolls


def format_violations(violations: list[Violation], sample_size: int = 0) -> str:
    if not violations:
        suffix = f" ({sample_size} roll(s) read across BUILDLOG.md + ROADMAP.md + houses/*/journal/*.md + chronicle/*.md, all < {TITHE_FLOOR})" if sample_size else ""
        return f"tithe check: clean -- every hand-typed Tithe roll across BUILDLOG.md, ROADMAP.md, houses/*/journal/*.md, and chronicle/*.md clears the {TITHE_FLOOR} floor it claims{suffix}"
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
