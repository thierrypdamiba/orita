#!/usr/bin/env python3
"""Task 782. Retrya audits the one hand-off he leads for real, not on faith.

STRATEGY.md names retrya's own remit plainly: "The One Action, Left to
You ... every report ends with exactly one suggested final action,
phrased as the human's and never executed." `fencepost/README.md` repeats
the identical promise in its own voice, as the second of the three
promises on iron: "The last step is always yours. Every report ends with
exactly one suggested action. Fencepost never takes it. You do."

`seam_engine/report.py`'s `suggest_move`/`render_report` carry the law in
code, and `seam_engine/tests/test_report.py` (1017 lines) proves it
thoroughly -- but only ever against hand-built `sealed` dicts and
fixture-generated recipe gaps, entirely in memory. Nothing, anywhere in
this tree, had ever swept the real, sealed `fencepost/REPORTS/*.md`
tablets this town actually publishes every day and checked the promise
held THERE -- a doctrine test against the live artifact, not just the
generator function that produces it. That is the exact shape of gap task
779's own Wall sweep found and closed for `connect.html` against
`gateway.py`'s `READ_ONLY_CAPABILITIES` (`test_connect_doctrine.py`), and
task 773/report_regression_check.py found and closed for the milestone
count inside those same tablets.

An own-remit sweep of every one of the sealed reports on disk (this
task) found the invariant genuinely holding: every tablet from
2026-07-12 through today carries exactly one `**Your move.**` line, and
every one of them is phrased as the reader's own verb ("Post about it
yourself", "Add it to your Calendar yourself", "Correct or delete it
yourself", "Check back tomorrow") -- never Fencepost's ("I posted",
"we've added", "Fencepost will..."). That is a correct, honest state --
but until this module existed it was true by convention and unit-test
coverage of the generator alone, never checked against what actually got
written to disk. Nothing stood between a future report (hand-edited, a
future `render_report` regression, a manually stitched tablet during an
outage) and the invariant silently breaking in the one place a mortal
reader would ever actually see it.

This module closes that gap the same shape `report_regression_check.py`
(task 773) and `report_accuracy_check.py` (task 679) already established
for this exact directory: local-filesystem-only (reads every already-
sealed `fencepost/REPORTS/*.md`, no network call of its own), returns a
`check_*`-shaped result dict (`clean`/`reason` plus the specific detail),
and is wired into `tools/ritual_check.py`'s hourly block so a future
violation is caught the hour it ships, not the next time a god happens to
go looking.

Two checks, per sealed tablet:

1. Exactly one `**Your move.**` line. Zero (the hand-off silently
   dropped) or two-or-more (a second hand-off competing with the first --
   the exact failure STRATEGY.md's own law forbids by naming "exactly
   one") both flip `broken`.
2. The move line's own text never carries a first-person-executed verb
   naming something Fencepost (or "I"/"we") already did or is about to
   do -- "i posted", "i've posted", "i will ...", "we posted", "we've
   ...", "fencepost posted", "fencepost has ...", "fencepost will ..."
   -- checked against the single matched line's own text. (A tablet that
   already fails check 1 has no single line to check here, so it is
   skipped for this half rather than double-counted.)

Usage:
    python3 tools/one_action_check.py check
"""
from __future__ import annotations

import glob
import os
import re
import sys
from typing import cast

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import text_patterns  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REPORTS_DIR = os.path.join(ROOT, "fencepost", "REPORTS")

# The shared "YYYY-MM-DD.md" tablet-name pattern -- `report_cadence_check.py`
# and `petition_cadence_check.py` already import this same constant rather
# than hand-typing their own copy; a hand-typed local copy here would be the
# exact duplicate `duplicate_regex_check.py` exists to catch (confirmed live:
# an earlier draft of this module's own local `_DATE_RE` duplicated
# `report_regression_check.py`'s identical hand-typed pattern verbatim,
# flagged the moment it existed).
_DATE_NAME = text_patterns.DATE_NAME_MD
_MOVE_LINE_RE = re.compile(r"^\*\*Your move\.\*\*\s*(.*)$", re.MULTILINE)

# A first-person-executed verb naming something Fencepost, "I", or "we"
# already did or is about to do -- the exact thing STRATEGY.md's law
# forbids ("phrased as the human's and never executed"). Matched against
# the move line's own text, lowercased first, so phrasing case never
# matters. Deliberately phrase-level (not bare topic words) so an
# innocent reader-verb sentence that merely mentions Fencepost by name
# ("Fencepost only found the seam; it does not cross it" -- every real
# rule's own trailing sentence) never false-positives; every entry below
# is an executed-action verb paired with its own subject, not a bare noun.
_FORBIDDEN_EXECUTED_PHRASES: tuple[str, ...] = (
    "i posted",
    "i've posted",
    "i will post",
    "i'll post",
    "i added",
    "i've added",
    "i closed",
    "i've closed",
    "we posted",
    "we've posted",
    "we will post",
    "we'll post",
    "we added",
    "we've added",
    "we closed",
    "fencepost posted",
    "fencepost has posted",
    "fencepost will",
    "fencepost has added",
    "fencepost added",
    "fencepost closed",
    "fencepost has closed",
    "fencepost is posting",
)


def _sealed_report_dates_and_paths(reports_dir: str) -> list[tuple[str, str]]:
    """Every real, dated `fencepost/REPORTS/<date>.md` tablet as
    `(date, path)` pairs, sorted chronologically. `README.md` (and any
    other non-dated file that might someday sit in the directory) is
    silently skipped -- the same "ignore what doesn't conform" discipline
    `report_regression_check.read_report_counts` already holds for the
    identical directory."""
    out: list[tuple[str, str]] = []
    for path in sorted(glob.glob(os.path.join(reports_dir, "*.md"))):
        m = _DATE_NAME.match(os.path.basename(path))
        if m is not None:
            out.append(("-".join(m.groups()), path))
    return out


def _move_lines(text: str) -> list[str]:
    """Every `**Your move.** ...` line's own trailing text, in document
    order. Empty list if the marker never appears at all."""
    return [m.group(1).strip() for m in _MOVE_LINE_RE.finditer(text)]


def _first_person_violation(move_text: str) -> str | None:
    """The first forbidden executed-verb phrase found inside one move
    line's own text, or None if it reads clean."""
    lowered = move_text.lower()
    for phrase in _FORBIDDEN_EXECUTED_PHRASES:
        if phrase in lowered:
            return phrase
    return None


def check_one_action_invariant(reports_dir: str = DEFAULT_REPORTS_DIR) -> dict[str, object]:
    """Sweep every sealed report tablet in `reports_dir` for STRATEGY.md's
    "The One Action, Left to You" law. Returns `clean: True` with the
    checked count when every tablet holds; otherwise `clean: False` and
    the specific date(s)/reason(s) that broke it -- never a bare
    pass/fail."""
    dated_paths = _sealed_report_dates_and_paths(reports_dir)
    wrong_count: list[dict[str, object]] = []
    first_person: list[dict[str, object]] = []
    for date, path in dated_paths:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        moves = _move_lines(text)
        if len(moves) != 1:
            wrong_count.append({"date": date, "count": len(moves), "path": path})
            continue
        phrase = _first_person_violation(moves[0])
        if phrase is not None:
            first_person.append({"date": date, "phrase": phrase, "line": moves[0], "path": path})
    clean = not wrong_count and not first_person
    if clean:
        return {
            "clean": True,
            "reason": (
                f"{len(dated_paths)} sealed report(s), each carries exactly one "
                f"reader-phrased 'Your move' line"
            ),
            "checked": len(dated_paths),
            "wrong_count": wrong_count,
            "first_person": first_person,
        }
    parts = []
    if wrong_count:
        detail = ", ".join(f"{e['date']} ({e['count']})" for e in wrong_count)
        plural = "" if len(wrong_count) == 1 else "s"
        parts.append(f"{len(wrong_count)} report{plural} with != 1 'Your move' line: {detail}")
    if first_person:
        detail = ", ".join(f"{e['date']} ({e['phrase']!r})" for e in first_person)
        plural = "" if len(first_person) == 1 else "s"
        parts.append(f"{len(first_person)} report{plural} whose move line reads as Fencepost's own action: {detail}")
    return {
        "clean": False,
        "reason": "; ".join(parts),
        "checked": len(dated_paths),
        "wrong_count": wrong_count,
        "first_person": first_person,
    }


def format_result(result: dict[str, object]) -> str:
    status = "clean" if result["clean"] else "BROKEN"
    return f"one action invariant: {status} -- {cast(str, result['reason'])}"


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(1)
    out = check_one_action_invariant()
    print(format_result(out))
    sys.exit(0 if out["clean"] else 1)
