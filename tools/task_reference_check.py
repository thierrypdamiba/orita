#!/usr/bin/env python3
"""Task 1372. A stale task-number cross-reference, found in the wild.

`fencepost/ONBOARDING.md`'s "the honest boundary, today" section pointed a
reader at "(row 16 of `ROADMAP.md`)" for the Gmail-vs-Calendar seam. Task 16
is real and DONE (`seam_engine/gmail_calendar.py`'s own docstring cites it
by the same number) -- but `tools/roadmap_archive.py` has since cut the
live `ROADMAP.md` down to its still-open tail four times (tasks 169, 365,
481, 797, 1332 were the archiving hours). Row 16 has lived in
`ROADMAP-ARCHIVE-001-169.md` since the very first cut. A reader who
followed the link and searched the live file for row 16, the way the
sentence told them to, would have found nothing -- the exact "claims a
mirror, nothing checks it" shape `draftback_freshness_check.py` (task 1367)
and `badge_freshness_check.py` (task 425/574) already closed for a computed
value, here showing up instead as a hand-written prose citation nobody
re-checks after an archiving cut moves the ground under it.

Fixed the one instance found (`ONBOARDING.md`, corrected to name the real
archive file and note the row is DONE-but-fixture-only). This module closes
the recurrence: it greps a small set of town-authored docs for the
`(task N` / `(row N of ROADMAP.md` citation shape and confirms every N it
finds resolves to a real row -- in the live `ROADMAP.md` OR in any
`ROADMAP-ARCHIVE-*.md` sibling, reusing `roadmap_archive.ROW_RE` rather
than re-deriving the same regex a second time (the shape
`duplicate_regex_check.py` exists to catch). A citation whose number
resolves nowhere is reported STALE by name and file.

Deliberately NOT wired into `ritual_check.py` this hour -- that file's own
loader/check_*/broken-condition/result-dict/format wiring touches five
separate insertion points across 3000+ lines of a heavily cross-tested
module, and a documentation-citation checker is not urgent enough to risk
an integration mistake in that file under one hour's review. Real,
out-of-scope follow-on, named plainly rather than attempted rushed.

Usage:
    python3 tools/task_reference_check.py check
"""
from __future__ import annotations

import glob
import importlib.util
import os
import re
import sys
from typing import cast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The doc files this checker actually scans for a task/row citation of the
# shape this module guards. Small and explicit on purpose -- widening this
# list is a deliberate future act, not something to infer.
_SCANNED_DOCS = [
    os.path.join(ROOT, "fencepost", "ONBOARDING.md"),
    os.path.join(ROOT, "fencepost", "README.md"),
    os.path.join(ROOT, "STRATEGY.md"),
    os.path.join(ROOT, "CHARTER.md"),
]

# "(task 16" / "(row 16 of" -- deliberately anchored on the opening paren
# so a bare "task 16" inside ordinary prose (not a cross-reference) never
# matches; every real citation in this codebase opens a parenthetical.
_CITATION_RE = re.compile(r"\((?:task|row)\s+(\d+)\b")


def _roadmap_archive() -> object:
    spec = importlib.util.spec_from_file_location(
        "_task_reference_roadmap_archive", os.path.join(ROOT, "tools", "roadmap_archive.py")
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def known_task_numbers(root: str = ROOT) -> set[int]:
    """Every task/row number found in the live ROADMAP.md plus every
    ROADMAP-ARCHIVE-*.md sibling -- the full, real set a citation can
    honestly point at, archived or not.
    """
    mod = _roadmap_archive()
    row_re = cast(re.Pattern[str], mod.ROW_RE)  # type: ignore[attr-defined]
    numbers: set[int] = set()
    paths = [os.path.join(root, "ROADMAP.md")] + sorted(glob.glob(os.path.join(root, "ROADMAP-ARCHIVE-*.md")))
    for path in paths:
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for n, _status in row_re.findall(text):
            numbers.add(int(n))
    return numbers


def check_task_references(root: str = ROOT, docs: list[str] | None = None) -> dict[str, object]:
    """Scan `docs` (default `_SCANNED_DOCS`) for `(task N` / `(row N of`
    citations and confirm each N resolves in `known_task_numbers()`.

    Returns {"clean": bool, "citations": [...], "stale": [...]}. A file
    that doesn't exist is skipped, not an error -- the same "can't find it
    here must never mean broken" discipline this town's other freshness
    checks already hold.
    """
    doc_paths = docs if docs is not None else _SCANNED_DOCS
    known = known_task_numbers(root)
    citations: list[dict[str, object]] = []
    stale: list[dict[str, object]] = []
    for path in doc_paths:
        if not os.path.isfile(path):
            continue
        rel = os.path.relpath(path, root)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for lineno, line in enumerate(text.splitlines(), start=1):
            for m in _CITATION_RE.finditer(line):
                n = int(m.group(1))
                entry = {"file": rel, "line": lineno, "task": n}
                citations.append(entry)
                if n not in known:
                    stale.append(entry)
    return {"clean": not stale, "citations": citations, "stale": stale}


def format_task_references(result: dict[str, object]) -> str:
    citations = cast(list, result["citations"])
    if result["clean"]:
        return f"task references: clean ({len(citations)} citation(s), every task number resolves live or archived)"
    stale = cast(list, result["stale"])
    detail = "; ".join(f"{s['file']}:{s['line']} cites task {s['task']} (not found)" for s in stale)
    return f"task references: STALE -- {detail}"


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "check":
        print(__doc__)
        sys.exit(2)
    outcome = check_task_references()
    print(format_task_references(outcome))
    sys.exit(0 if outcome["clean"] else 1)
