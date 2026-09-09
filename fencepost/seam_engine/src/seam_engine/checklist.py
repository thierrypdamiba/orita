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

Pure, no I/O, no seam-engine imports of its own besides `references` --
same shape as `closing_keywords.py`, `milestone_claims.py`, and
`pr_claims.py`.

Task 1359 (Off-By-One): the original `CHECKLIST_RE` required the `#N` to
sit IMMEDIATELY after the checkbox mark
(`^\\s*-\\s*\\[([ xX])\\]\\s*#(\\d+)`), with nothing but whitespace
allowed in between. Reproduced live before
touching anything: `checklist_targets("- [ ] Fix the login bug #12")` and
`checklist_targets("- [ ] Sub-task: #12")` both returned `[]` -- a real,
common GitHub task-list shape (a human-written label in front of the
reference, or GitHub's own auto-generated sub-issue line, which often
carries a title after the number) silently dropped the target entirely,
the same "false negative" shape task 693's `negation.py` fix and task
1357's `report.py` default-move sweep both found elsewhere in this
package this week. Both real fixture files (`issues.json` for
`issue-closed-subissue-still-open`, and its sibling for
`issue-checklist-complete-still-open`) only ever use the bare `- [ ] #N`
form, so neither recipe's own test suite could have caught this -- the gap
was in the shared grammar, never exercised by either consumer's own data.

The blast radius is a missed sub-issue-still-open or missed-still-
incomplete gap, not a false positive: a labeled checklist item is a real,
declared sub-task exactly the same as a bare one, and Ogun's law is about
never SURFACING a junk gap, not about being conservative to the point of
missing a real one silently.

Fixed by splitting the grammar in two, the same "checkbox line, then reuse
the shared `#N` law for what's on it" shape `references.py` already owns
for cross-repo exclusion, rather than retype that lookbehind a second time
here: `_CHECKLIST_LINE_RE` now finds the checkbox mark and captures
everything else on the line; `checklist_targets` then runs
`references.REF_RE` (task 368's shared same-repo-only `#N` law, negative
lookbehind against `owner/repo#N`/`repo#N` and all) against that remainder,
so a labeled item now yields its target while a genuinely cross-repo
reference (`- [ ] owner/repo#12`) still correctly yields nothing -- the
same exclusion `references.py`'s own docstring already reasons through,
now actually shared instead of silently re-derived by a narrower regex
that happened to also exclude it, for the wrong reason (adjacency, not
repo scope). `CHECKLIST_RE` keeps its old name and its old bare-adjacent
shape for the one caller that still wants exactly that (this module's own
direct-regex test); `checklist_targets` no longer uses it.
"""
from __future__ import annotations

import re

from seam_engine.references import REF_RE

# GitHub's own task-list checkbox syntax: "- [ ] #N" / "- [x] #N", `#N`
# immediately after the mark. Kept for the one direct regex test below;
# `checklist_targets` itself no longer uses this narrow shape -- see
# `_CHECKLIST_LINE_RE` and the module docstring's task 1359 note.
CHECKLIST_RE = re.compile(r"^\s*-\s*\[([ xX])\]\s*#(\d+)", re.MULTILINE)

# A real task-list checkbox line, capturing everything after the mark --
# a bare "#N", a labeled "Fix the bug #N", or a cross-repo "owner/repo#N"
# alike. Which of those actually names a same-repo target is `references.
# REF_RE`'s law to apply, not this line-level regex's.
_CHECKLIST_LINE_RE = re.compile(r"^\s*-\s*\[([ xX])\]\s*(.*)$", re.MULTILINE)


def checklist_targets(body: str) -> list[int]:
    """Every same-repo `#N` named on a real task-list checkbox line in
    `body`, in the order it appears. Duplicates kept -- see module
    docstring. A bare `#N` mention with no checkbox in front of it never
    matches -- that is a dangling-reference recipe's own seam, not this
    grammar's. A cross-repo `owner/repo#N`/`repo#N` reference never matches
    either, checkbox or not -- see `references.REF_RE`'s own docstring for
    why (task 1359)."""
    targets: list[int] = []
    for _mark, rest in _CHECKLIST_LINE_RE.findall(body):
        targets.extend(int(n) for n in REF_RE.findall(rest))
    return targets
