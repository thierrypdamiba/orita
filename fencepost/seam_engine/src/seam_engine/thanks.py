"""The shared "thanks/thank you @handle" tweet-grammar law.

`contributor-thanked-not-credited/detector.py` (task 371) first wrote the
regex that recognizes a tweet thanking a handle. `readme-credited-not-
thanked/detector.py` (task 385) needed the identical grammar for the
inverse check and said so plainly in its own comment -- "identical grammar
to contributor-thanked-not-credited's own `_THANKS_RE`, reused verbatim
since it answers the same question" -- but that comment was never backed
by an import: the regex was retyped a second time in the second file, with
nothing connecting either copy to the other.

This is the exact "two independently written regexes... drifting apart"
shape task 389 found and fixed for `#N` extraction (`references.py`), task
390 found and fixed a second time for the "milestone #N" claim phrase
(`milestone_claims.py`), task 393 found and fixed a third time for the
"ships/includes/merges/via #N" claim phrase (`pr_claims.py`), and task 394
found and fixed a fourth time for the GitHub closing-keyword grammar
(`closing_keywords.py`) -- found here a fifth time (task 396), by reading
both thanks-shaped detectors side by side rather than trusting either
one's own comment about itself.

This module is the one real place the grammar now lives. Both recipes
that read a "thanks @handle" tweet -- `contributor-thanked-not-credited`
and `readme-credited-not-thanked` -- import `THANKS_RE`/`thanked_handle`
from here and bind them to their own existing module-level
`_THANKS_RE`/`_thanked_handle` names, so neither `recipe.json`, fixture,
nor existing test (which call `detector._thanked_handle(...)` or search
`detector._THANKS_RE` directly) has to change shape.

Pure, no I/O, no seam-engine imports of its own -- same shape as
`references.py`, `milestone_claims.py`, `pr_claims.py`, and
`closing_keywords.py`.
"""
from __future__ import annotations

import re

# Requires "thank(s)" or "thank you", loosely followed by an @handle, in
# the same tweet. Deliberately its own grammar, distinct from the #N
# claim-phrase families the issue/PR/milestone-side recipes reuse -- a
# thank-you names a person, not a numbered record.
THANKS_RE = re.compile(r"thanks?(?:\s+you)?\b.{0,40}?@(\w[\w-]*)", re.IGNORECASE | re.DOTALL)


def thanked_handle(text: str) -> str | None:
    """The first handle `text` thanks via a thanks/thank-you phrase, or
    `None` if no such phrase appears. A bare `@handle` with no preceding
    thanks-shaped language never matches -- see `THANKS_RE`'s own
    comment for why."""
    match = THANKS_RE.search(text)
    return match.group(1) if match else None
