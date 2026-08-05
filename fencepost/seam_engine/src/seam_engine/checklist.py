"""The shared GitHub task-list checkbox ("- [ ] #N" / "- [x] #N") law.

`issue-closed-subissue-still-open/detector.py` (task 530) first wrote
`_CHECKLIST_RE` and `_checklist_targets` to read a real GitHub task-list
checkbox line. `issue-checklist-complete-still-open/detector.py` (task 558)
needed the identical grammar for the mirror-image seam one quadrant over —
an open parent whose checklist is all closed, instead of a closed parent
whose checklist still has an open item — and retyped both a second time,
the exact "two independently written regexes... drifting apart" shape
`closing_keywords.py` already named for the closing-keyword family
(commit-closes-keyword-issue-still-open, issue-closed-never-released,
release-claims-unfixed-issue), caught here before a third recipe could ever
retype it a third time.

This module is now the one real source. Both recipes import
`checklist_targets` from here, binding it to their own existing
`_checklist_targets` module-level name so neither recipe's own
`recipe.json`, fixture, or existing tests has to change shape. Any future
recipe that needs the same task-list grammar reuses this module too, rather
than writing its own copy.

Deliberately returns every match, duplicates kept — the same checklist item
referenced twice is two real matches, not one deduplicated fact, mirroring
`closing_keywords.closing_keyword_numbers`'s own "duplicates kept" rule
exactly. A caller that wants distinct targets dedupes at its own call
site — both real callers do, each in the shape its own seam needs
(`issue-closed-subissue-still-open` dedupes with a `seen` set inside its
per-target loop; `issue-checklist-complete-still-open` dedupes before
resolving targets to their own live state, since its completeness check
needs the distinct set, not the raw occurrence count).

Pure, no I/O, no seam-engine imports of its own — same shape as
`closing_keywords.py`, `references.py`, `milestone_claims.py`, and
`pr_claims.py`.
"""
from __future__ import annotations

import re

# GitHub's own task-list checkbox syntax: "- [ ] #N" / "- [x] #N", one per
# line, optionally indented. The checked/unchecked mark itself is captured
# but unused by either real caller's own gap decision -- only the named
# target's own live state decides that, in each recipe's own module.
CHECKLIST_RE = re.compile(r"^\s*-\s*\[([ xX])\]\s*#(\d+)", re.MULTILINE)


def checklist_targets(body: str) -> list[int]:
    """Every `#N` named by a real task-list checkbox line in `body`, in the
    order it appears. Duplicates kept -- see module docstring. A bare `#N`
    mention with no checkbox in front of it never matches -- that is a
    dangling-reference recipe's own seam, not this grammar's."""
    return [int(n) for _mark, n in CHECKLIST_RE.findall(body)]
