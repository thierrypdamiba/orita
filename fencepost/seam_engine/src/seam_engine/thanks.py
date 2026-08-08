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

Task 610 (Kwaku Ananse): `thanked_handle` used to be `THANKS_RE.search`
alone -- the *first* "thanks...@handle" span in the text, full stop.
Reproduced live before touching anything: `thanked_handle("no thanks
@user, wrong fix")` returned `"user"` -- a genuine false positive, the
exact shape STRATEGY.md's Ogun's law exists to catch ("false-positive
rate is the whole ballgame... surface one junk gap in public and trust is
gone"). "No thanks" and "not thanks" are declines, not credit -- a real
mortal tweet phrased that way about a real handle would have made
`contributor-thanked-not-credited` claim a thank-you that never happened.
Same family as task 609's `gateway.py` fix (an unnegated claim must not
survive across a nearby negation) but the mirror shape: here the negation
sits BEFORE the claim word, not after it in a later clause. Fixed by
walking every "thanks...@handle" candidate (`finditer`, not `search`) and
skipping any whose immediately preceding few words carry `no`/`not`/
`never` as a whole word, falling through to the next candidate rather
than giving up outright -- so `"thanks @first-one and also thanks
@second-one"` still returns the genuine first thanks even though a later,
unrelated candidate exists, and `"no thanks @user, wrong fix"` now
correctly returns `None`. Deliberately narrow: the negation check only
looks at the words immediately in front of "thanks" itself, not the whole
gap up to the handle -- a broader scan (checking the entire matched span
for any `no`/`not`/`never`) was tried and rejected live, because it also
flagged `"thanks for the no-brainer fix, @user"` as negated (the `no` in
`no-brainer` is its own whole word, hyphen-bounded) -- a real, ordinary
phrase turned into a false NEGATIVE, trading one failure mode for a worse
one. The prefix-only check catches the two idioms mortals actually type
("no thanks", "not thanks", "no, thanks") and does not reach past the
word "thanks" into unrelated prose. Named, not hidden: a thanks-phrase
separated from its own negation by more than a few words in front of it
("there's no need, but thanks @user" with a wide gap) can still slip
through -- narrower than before, not zero, the same residual-limit
discipline `_QUOTED_SPAN_RE`'s own comment in `report.py` already keeps
(task 605).
"""
from __future__ import annotations

import re

# Requires "thank(s)" or "thank you", loosely followed by an @handle, in
# the same tweet. Deliberately its own grammar, distinct from the #N
# claim-phrase families the issue/PR/milestone-side recipes reuse -- a
# thank-you names a person, not a numbered record.
THANKS_RE = re.compile(r"thanks?(?:\s+you)?\b.{0,40}?@(\w[\w-]*)", re.IGNORECASE | re.DOTALL)

# A negation word sitting immediately in front of "thanks" turns a
# genuine thank-you into a decline -- "no thanks", "not thanks", "no,
# thanks" -- see this module's own docstring (task 610) for the live
# reproduction and why the check is scoped to the words right before
# "thanks" rather than the whole span up to the handle.
_NEGATION_PREFIX_RE = re.compile(r"\b(?:no|not|never)\b", re.IGNORECASE)

# "never " is the longest of the three negation words plus its own
# trailing space; a couple of extra characters of slack covers a comma
# ("no, thanks @user") without reaching so far back that it starts
# catching negations that belong to an earlier, unrelated clause.
_NEGATION_PREFIX_WINDOW = 10


def thanked_handle(text: str) -> str | None:
    """The first genuinely-thanking handle `text` names via a thanks/
    thank-you phrase, or `None` if no such (unnegated) phrase appears. A
    bare `@handle` with no preceding thanks-shaped language never matches
    -- see `THANKS_RE`'s own comment for why. A thanks-shaped phrase whose
    immediately preceding words negate it ("no thanks @user", "not thanks
    @user") is skipped, and the search continues to the next candidate --
    see this module's own docstring (task 610) for the live reproduction.
    """
    for match in THANKS_RE.finditer(text):
        prefix = text[max(0, match.start() - _NEGATION_PREFIX_WINDOW) : match.start()]
        if _NEGATION_PREFIX_RE.search(prefix):
            continue
        return match.group(1)
    return None
