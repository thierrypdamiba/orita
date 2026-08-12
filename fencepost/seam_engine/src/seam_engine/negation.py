"""The shared negation-prefix law used by every claim/marker grammar in
this package.

Task 609 (`gateway.py`'s `is_read_only_capabilities`), task 610
(`thanks.py`'s `thanked_handle`), and task 612 (`duplicate_markers.py`'s
`named_duplicate_of`) each independently found and fixed the same false-
positive shape in a different module this shift: an unnegated claim
laundered past a nearby `not`/`never`/`no`/`n't` sitting right in front of
it. Task 613 found the same bug a fourth and fifth time, in
`pr_claims.py` and `milestone_claims.py`, and this time wrote the fix once
instead of a third time: `duplicate_markers.py`'s own
`_NEGATION_PREFIX_RE = re.compile(r"\\b(?:not|never|no)\\b|n't\\b", ...)`
got hand-retyped, byte-for-byte, into both new call sites -- caught live
by `tools/duplicate_regex_check.py` the moment this task ran it, the exact
"two [now three] independently written regexes... drifting apart" shape
that checker exists to catch, in this task's own new code before it ever
shipped. Rather than leave a fourth/fifth hand-typed copy standing next to
the checker that flags them, this module became the one real place the
negation grammar lives, and `duplicate_markers.py`, `pr_claims.py`, and
`milestone_claims.py` now all import it.

Each caller keeps its OWN window size (`duplicate_markers.py`'s 16,
`pr_claims.py`'s and `milestone_claims.py`'s 20) -- the window is a plain
`int`, not a `re.compile(...)` pattern, so it is not the thing
`duplicate_regex_check.py` polices, and different grammars legitimately
need different amounts of slack in front of their own claim word (see
each caller's own docstring for why its window is sized the way it is).

Pure, no I/O, no seam-engine imports of its own -- same shape as
`references.py`, `milestone_claims.py`, `pr_claims.py`,
`closing_keywords.py`, and `checklist.py`.

Task 693 (Retrya): every caller's own docstring already claimed its window
was sized "without reaching so far back that it starts catching a negation
that belongs to an earlier, unrelated clause" -- a claim this function
never actually backed up. `is_negated` sliced a fixed character window and
searched the whole thing for a negation word, with no notion of a sentence
boundary at all. Reproduced live before touching anything, on all five
real callers -- four that import this module (`thanks.py`,
`duplicate_markers.py`, `pr_claims.py`, `milestone_claims.py`) plus a
fifth found by grepping every real importer rather than trusting the four
each other's docstrings name (`unblocked-issue-still-open/detector.py`,
which imports `is_negated` directly): `thanks.thanked_handle("It is not
okay. thanks @user for the fix.")` returned `None`,
`duplicate_markers.named_duplicate_of("Not fine. dup of #12 today.")`
returned `None`, `pr_claims.claimed_pr_numbers("Not today. ships #45
anyway.")` returned `[]`, `milestone_claims.claimed_milestone_numbers
("Not today. milestone #7 is done.")` returned `[]`, and the recipe's own
`_named_blocker_of("Not fine. blocked by #10 anymore.")` returned `None`
-- in every case a negation word sitting in a PRIOR, unrelated sentence
(the window doesn't know "." ends anything) silently swallowed a genuine,
unnegated claim/marker in the sentence that actually followed it. This is
not the already-named residual gap (a denial too far in front of its own
claim to reach) -- it is the opposite failure, and the worse one:
`gateway.py`'s own `_split_clauses` already solved exactly this shape for
its sibling negation check (task 609) by splitting text on sentence and
clause boundaries before ever searching for a cue, but that fix never
crossed over into this shared function five other call sites depend on.
The blast radius is a false POSITIVE, not a false negative, for the
twenty-nine recipes on the receiving end of these five functions (2 via
`thanks.py`, 2 via `duplicate_markers.py`, 11 via `pr_claims.py`, 13 via
`milestone_claims.py`, 1 direct): `readme-credited-not-thanked` would have
called a real, unnegated thank-you tweet uncredited (the tweet's own
thanks silently vanished), and `merged-pr-never-released`/`release-
claims-open-milestone`'s siblings would have called a release that
genuinely DID claim a merged PR or an open milestone "never claimed" -- a
real gap surfaced off a sentence boundary the window never saw, the exact
"false positives are fatal" shape STRATEGY.md's Ogun's law exists to
catch. Fixed by trimming the window itself to the text after the LAST
`.`/`!`/`?` inside it before searching for a negation cue -- anything
before that boundary belongs to an earlier sentence and no longer counts,
mirroring `gateway.py`'s own clause-boundary discipline at the level of
this one shared helper instead of five independent character-count
guesses. A comma is deliberately NOT a boundary here, matching every
caller's own existing "no, thanks @user"/"no, not a duplicate of #12"
idiom -- only real sentence-ending punctuation now stops the window.

Found independently, confirmed afterward: `tools/sentence_negation.py`'s
own `is_negated_or_predictive` (tasks 548/569, a town-governance checker
family with no relationship to this package) already scans backward from
a match to the nearest sentence boundary before searching for a cue --
the identical control-flow shape this fix reaches for. `fencepost/
seam_engine` deliberately never imports `tools/` (this package ships
standalone, forkable on its own), so this is not a missed reuse
opportunity the way the four/five hand-typed `NEGATION_PREFIX_RE` copies
were -- but it is real confirmation this fix's shape is not a first
guess; this codebase already proved it out in a different family months
ago.
"""
from __future__ import annotations

import re

# A negation word (or an "n't" contraction: isn't/wasn't/doesn't/...)
# anywhere in a candidate's immediately-preceding window turns a genuine-
# looking claim/marker into a denial rather than a claim -- see this
# module's own docstring for the live history of where this grammar was
# first written and why it moved here.
NEGATION_PREFIX_RE = re.compile(r"\b(?:not|never|no)\b|n't\b", re.IGNORECASE)

# A real sentence boundary inside the prefix window -- see this module's
# own docstring (task 693) for why the window must stop here instead of
# reading straight through it. Deliberately narrow (no comma, no
# semicolon): every caller's own "no, thanks @user" / "no, not a duplicate
# of #12" idiom relies on a comma NOT ending the window.
_SENTENCE_END_RE = re.compile(r"[.!?]")


def is_negated(text: str, match_start: int, window: int) -> bool:
    """True if the `window` characters immediately before `match_start` in
    `text` carry a negation word/token -- the shared prefix-window check
    every caller of `NEGATION_PREFIX_RE` performs identically; only the
    window size differs caller to caller. If a real sentence boundary
    (`.`/`!`/`?`) falls inside that window, only the text after the LAST
    one is searched -- a negation word belonging to an earlier, unrelated
    sentence must not be able to negate a claim two sentences later just
    because it happens to fall inside a fixed character count (task 693)."""
    prefix = text[max(0, match_start - window) : match_start]
    boundaries = list(_SENTENCE_END_RE.finditer(prefix))
    if boundaries:
        prefix = prefix[boundaries[-1].end() :]
    return bool(NEGATION_PREFIX_RE.search(prefix))
