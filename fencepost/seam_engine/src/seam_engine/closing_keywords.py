"""The shared GitHub closing-keyword ("closes/fixes/resolves #N") law.

`commit-closes-keyword-issue-still-open/detector.py` (task 388) first wrote
`CLOSING_KEYWORD_RE`, its own comment saying it "mirrors
`tools/closing_keyword_guard.py`'s CLOSING_KEYWORD_RE verbatim". Two more
recipes needed the identical grammar and said the same thing in their own
comments -- `issue-closed-never-released/detector.py` (as `CLAIM_RE`) and
`release-claims-unfixed-issue/detector.py` (as a second `CLOSING_KEYWORD_RE`)
-- but neither comment was ever backed by an import: the regex was retyped
a third time, with nothing connecting any of the three copies to each
other. This is the exact "two [now three] independently written regexes...
drifting apart" shape task 389 found and fixed for `#N` extraction
(`references.py`), task 390 found and fixed a second time for the
"milestone #N" claim phrase (`milestone_claims.py`), and task 393 found and
fixed a third time for the "ships/includes/merges/via #N" claim phrase
(`pr_claims.py`) -- found here a fourth time, in the one family none of
those three sweeps touched, by grepping every `_RE = re.compile`/
`RE = re.compile` line across all nineteen recipes rather than trusting any
one recipe's own comment about itself.

Ruled out one lookalike while doing that sweep, but NOT ruled out for
good: `_CLOSES_RE` in `issue-closed-pr-still-open` and
`merged-pr-issue-still-open` was textually identical between those two
files, and was a deliberately DIFFERENT, narrower grammar
(`closes?|fixes?|resolves?`, present tense only) at the time this module
was first written -- `tools/closing_keyword_guard.py`'s own module
docstring already said so explicitly, by name, and this task's own commit
left that pair alone as "a real working two-copy law already
cross-referenced in prose," not this bug. ROADMAP.md #543 came back to it:
"declares exactly what it actually matches, not the full spec it doesn't
yet implement" (both recipes' own comments, verbatim) was an honest
admission of an incomplete grammar, not a closed design decision -- and
`commit-closes-keyword-issue-still-open` had already proven, live, on this
repo's own history (task 184), that GitHub's real grammar fires on past
tense exactly as readily as present tense, the exact form this pair could
never see. Both now import `CLOSING_KEYWORD_RE` from here too, closing the
false-negative rather than leaving it as a documented gap.

This module is now the one real source. Fifteen recipes import
`CLOSING_KEYWORD_RE`/`CLAIM_RE` directly (the five named above,
`commit-closes-keyword-pr-still-open`, `merged-pr-pr-still-open`,
`tweet-claims-unfixed-issue`, and `milestone-claims-unfixed-issue` from
ROADMAP.md #544, plus `commit-closes-keyword-issue-closed-not-planned`,
`issue-comment-claims-unfixed-issue`, `linear-comment-claims-unfixed-issue`,
`mention-claims-unfixed-issue`, `review-comment-claims-unfixed-issue`, and
`slack-message-claims-unfixed-issue` from ROADMAP.md #686 -- each
correctly wired from birth, never a live bug, just this docstring's own
count never caught up with them until each sweep fixed both the count
here and `tests/test_closing_keywords.py`'s own `_CASES`, which had the
identical stale-count shape both times). Four more (`good-first-issue-
never-referenced`, `readme-claims-unfixed-issue`,
`draft-pr-closes-keyword-issue`, `issue-assignee-never-opened-pr` -- two
more than ROADMAP.md #544's count named) import the
`closing_keyword_numbers` wrapper function instead. Each binds the import
to its own existing module-level name (`CLOSING_KEYWORD_RE` or
`CLAIM_RE`), so none of their `recipe.json`s, fixtures, or existing tests
have to change shape. Any future recipe that needs the same
closing-keyword grammar reuses this module too, rather than writing its
own copy.

Deliberately does NOT import `tools/closing_keyword_guard.py` (the real
canonical, safety-critical source of this grammar, guarding Iron Rule #8
against a live GitHub auto-close on push): `seam_engine` is the portable,
forkable package (STRATEGY.md -- "fork the town, point it at your own
accounts") and must not depend on this parent repo's own `tools/`
directory. This module re-states the same law as a documented, intentional
mirror instead -- exactly what all three recipes already claimed to do in
prose before this task made it real.

Pure, no I/O, no seam-engine imports of its own -- same shape as
`references.py`, `milestone_claims.py`, and `pr_claims.py`.
"""
from __future__ import annotations

import re

# GitHub's real closing-keyword grammar (see `tools/closing_keyword_guard.
# py`'s own docstring for the citation): close/closes/closed, fix/fixes/
# fixed, resolve/resolves/resolved, each optionally followed by a colon,
# then whitespace, then #<digits>. Both tenses are live triggers -- task
# 184's own incident (issues #1 and #2 closing themselves on a past-tense
# "closed #1"/"fixes #2" push) proved that on this repo's real history, not
# just in a spec. "closing #N" (present participle) does not match either
# form -- Iron Rule #8's prescribed safe phrasing.
CLOSING_KEYWORD_RE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?):?\s+#(\d+)\b",
    re.IGNORECASE,
)


def closing_keyword_numbers(text: str) -> list[int]:
    """Every issue/PR number `text` names via a real GitHub closing keyword,
    in the order they appear (duplicates kept -- the same number named
    twice is two real matches, not one deduplicated fact)."""
    return [int(n) for n in CLOSING_KEYWORD_RE.findall(text)]
