"""The shared "duplicate of #N" marker law.

`duplicate-issue-still-open/detector.py` (task 373-area, the seventh real
recipe) first wrote the regex that reads an issue's own body for a
"duplicate of #N" / "dup of #N" marker -- pure prose, no GitHub auto-close
mechanism behind it at all. `duplicate-pr-still-open/detector.py` (task 400)
needs the identical grammar for a second data source (a pull request's body
instead of an issue's) -- the exact "second file, second hand-typed copy"
shape `tools/duplicate_regex_check.py` (task 397) now exists specifically to
catch, having already found it five times by hand across other recipe
families (tasks 389/390/393/394/396) before this pattern ever got a chance
to add a sixth instance.

This module is the one real place the marker grammar lives. Both recipes'
detectors import `DUPLICATE_MARKER_RE`/`named_duplicate_of` from here and
bind them to their own module-level `_DUP_RE`/`_named_duplicate_of` names,
so neither recipe's own code, its `recipe.json`, nor its existing tests --
which call `detector._named_duplicate_of(...)` directly -- have to change
shape.

Pure, no I/O, no seam-engine imports of its own -- the same
small-boring-depended-on-by-everything shape as `references.py` and
`pr_claims.py`.
"""
from __future__ import annotations

import re

# "Duplicate of #700" / "dup of #703" / "Duplicate: #705" / "duplicate #705"
# all match. A `\b` boundary right after "dup" rules out "dupe"/"duping" so
# ordinary prose never becomes a false candidate.
DUPLICATE_MARKER_RE = re.compile(r"\bdup(?:licate)?\s*(?:of|:)?\s+#(\d+)\b", re.IGNORECASE)


def named_duplicate_of(body: str) -> int | None:
    """The number named as this body's original, or None if it names no
    duplicate marker at all."""
    match = DUPLICATE_MARKER_RE.search(body)
    return int(match.group(1)) if match else None
