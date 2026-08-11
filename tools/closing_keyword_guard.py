#!/usr/bin/env python3
"""Task 184. Nisaba's own commit closed the door on the way out.

Task 183's commit message, discussing a bug where a *different* module
("merged-pr-issue-still-open") only ever caught the first GitHub closing
keyword in a PR body, quoted a worked example inline: "closes #1 and
fixes #2". GitHub does not parse commit messages as markdown and does not
know a citation from a command -- it reads every commit pushed to the
default branch for its own closing-keyword grammar (close/closes/closed,
fix/fixes/fixed, resolve/resolves/resolved, each followed by `#<number>`)
and closes whatever issue that number names, in this repo, no vote, no
decree. Issues #1 and #2 -- Off-By-One's "this issue stays open forever"
and Nyx's "we will not close this issue" -- closed themselves at
2026-07-20T19:23:1{2,3}Z, the exact same minute as that commit's push and
the dawn-run it triggered. Reopened and corrected the same hour this was
found (see the issue #1/#2 comment threads); this module is the guard so
it does not happen twice.

`find_closing_refs` mirrors GitHub's real closing-keyword grammar exactly
(9 keywords, not the narrower `closes?|fixes?|resolves?` the
merged-pr-issue-still-open recipe uses for its own different job of
reading PR bodies for promised closes -- that module's incompleteness is
a separate, pre-existing gap out of this task's scope). `dangerous_refs`
narrows those matches to numbers that were open at write time -- a
message that names #9999 (never existed) or a real but already-closed
number is not a live risk to anything. No markdown-fence or quote-mark
exemption is applied on purpose: GitHub's own commit-message parser does
not respect backticks either, so a check that trusted them would give
false confidence about the exact failure mode that caused this incident.
The only real fix is: do not write the live keyword-plus-number pattern
in a commit message at all, for any reason, even a citation -- describe
it in prose instead (exactly what this module's own docstring just did,
three paragraphs up, using "closing #1 and fixing #2" -- present participles,
outside the grammar -- rather than the imperative forms GitHub parses).

Task 684: widened to GitHub's `owner/repo#N` closing-keyword form. Every
prior version of this grammar (here and its `tools/duplicate_regex_check.
py`-tracked mirror in `seam_engine/closing_keywords.py`) only ever matched
a bare `#N` -- but GitHub's own docs ("Linking a pull request to an
issue") document a second, equally real form: "if the issue is in a
different repository, you can use the owner/repository#issue-number
syntax ... This closes octo-org/octo-repo#100." That form is not limited
to cross-repo use -- writing this repo's own `thierrypdamiba/orita#5`
closes issue #5 here exactly as `#5` alone would, and the pre-widening
regex was silently blind to it. Reproduced live before fixing:
`find_closing_refs("This closes thierrypdamiba/orita#5")` returned `[]`.
The same docs also settle a second, previously-unverified question this
task first suspected might be a companion gap: "you must use the keyword
before each issue you reference for the keyword to work" -- so "closes
#1, #2" does NOT close #2 (only #1, the keyword-adjacent one), confirming
the existing one-keyword-one-number matching was already correct there;
no comma-list widening was needed.

`owner/repo#N` is now recognized and compared case-insensitively against
`repo` (default `"thierrypdamiba/orita"`, this town's own repo -- every
call site in this codebase). A reference qualified with a DIFFERENT
owner/repo closes an issue in THAT repo instead, whose open-issue list
this module has no visibility into (it is only ever handed this repo's
own `<open-issues-csv>`/`<square-state.json>`) -- correctly left
unflagged as out of scope, not silently treated as safe. Widening the
nine `fencepost/RECIPES/*/detector.py` consumers of `seam_engine.
closing_keywords.CLOSING_KEYWORD_RE` (a deliberately separate, narrower
mirror serving a different job -- detecting a commit/PR's own CLAIM that
an issue closed, not guarding against a live accidental self-close) the
same way is a real, plausible follow-on gap, left explicitly named and
NOT attempted here -- it touches nine already-tested recipes' fixtures
for a job this module does not do, the same "named, not silently folded
in" discipline `tithe_check.py`'s live-issue-thread widening already
held (task 678). Because the two files' pattern text now genuinely
diverges, `tools/duplicate_regex_check.py`'s seeded exception for that
pair (task 418) no longer describes a real duplicate and is trimmed in
the same commit -- the identical "seed a stale allowlist, then trim it in
the same fix" shape ROADMAP.md #543 already used for `_CLOSES_RE`.

Usage:
    python3 tools/closing_keyword_guard.py check <message-file> <open-issues-csv>
    python3 tools/closing_keyword_guard.py check-live <message-file> <square-state.json>

<square-state.json> is the same shape square_check.py already takes:
{"issues": [{"number": 1, ...}, ...], "prs": [...]}. Only issue numbers
are consulted -- a PR number is never closed by this grammar.
"""
from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable

# GitHub's real closing-keyword grammar: exactly these 9 forms, each
# optionally followed by a colon, then whitespace, then either a bare
# #<digits> or an owner/repo#<digits> cross-repo (or self-repo) reference
# -- GitHub's own docs name both the colon form explicitly ("Closes: #10"
# closes on push exactly like "Closes #10") and the owner/repo#N form
# explicitly ("Closes octo-org/octo-repo#100"; docs.github.com, "Linking a
# pull request to an issue"). Deliberately wider than fencepost/RECIPES/
# merged-pr-issue-still-open/detector.py's own `closes?|fixes?|resolves?`
# (that module never needed the past tense, this one must, because
# "closed #1" and "fixed #2" both close on push exactly as their
# present-tense siblings do).
CLOSING_KEYWORD_RE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?):?\s+"
    r"(?:(?P<owner_repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#|#)(?P<num>\d+)\b",
    re.IGNORECASE,
)

# The one repo every real call site in this codebase guards -- see
# TOWN-OPERATIONS.md's Repos section. An `owner/repo#N` reference
# qualified with this name (case-insensitively) is exactly as dangerous
# as a bare `#N`; any other owner/repo is a different repo's namespace,
# out of this module's scope (see module docstring).
SELF_REPO = "thierrypdamiba/orita"


def find_closing_refs(text: str, repo: str = SELF_REPO) -> list[int]:
    """Every issue/PR number a GitHub-recognized closing keyword names in
    `text` against `repo` (bare `#N`, or `owner/repo#N` qualified with
    `repo` itself, case-insensitively), in first-seen order,
    de-duplicated. An `owner/repo#N` reference naming a DIFFERENT repo is
    not `repo`'s problem and is not returned -- see module docstring. No
    other exemptions -- see the module docstring for why quotes/backticks
    are not treated as safe."""
    seen: list[int] = []
    for m in CLOSING_KEYWORD_RE.finditer(text):
        owner_repo = m.group("owner_repo")
        if owner_repo is not None and owner_repo.lower() != repo.lower():
            continue
        n = int(m.group("num"))
        if n not in seen:
            seen.append(n)
    return seen


def dangerous_refs(
    text: str, open_issue_numbers: Iterable[int], repo: str = SELF_REPO
) -> list[int]:
    """The subset of `find_closing_refs(text, repo)` that names a number
    currently open in the repo -- the only refs GitHub can actually act
    on. A closing-keyword phrase naming an already-closed or nonexistent
    number is inert; not flagged."""
    open_set = set(open_issue_numbers)
    return [n for n in find_closing_refs(text, repo=repo) if n in open_set]


def check_message(
    message: str, open_issue_numbers: Iterable[int], repo: str = SELF_REPO
) -> tuple[bool, list[int]]:
    """Returns (ok: bool, dangerous: list[int]). ok is False iff pushing
    `message` to the default branch would auto-close a live open issue."""
    refs = dangerous_refs(message, open_issue_numbers, repo=repo)
    return (not refs, refs)


def format_result(ok: bool, dangerous: list[int], message_path: str) -> str:
    if ok:
        return f"closing keyword guard: clean -- {message_path} names no open issue via a real closing keyword"
    return (
        f"closing keyword guard: DANGEROUS -- {message_path} would close "
        f"open issue(s) {dangerous} on push. Rewrite: describe the pattern "
        f"in prose (e.g. 'closing #{dangerous[0]}') instead of the live "
        f"imperative form GitHub parses."
    )


class ClosingKeywordArgError(ValueError):
    """check-live's <state.json> parsed as valid JSON but not into a dict --
    the same valid-JSON-wrong-shape crash class task 364 fixed for
    ritual_check.py's own CLI, here at closing_keyword_guard.py's own
    check-live mode (a bare list or scalar reaching `state.get("issues",
    [])` unguarded crashes with a bare AttributeError instead of naming the
    real problem)."""


if __name__ == "__main__":
    argv = sys.argv[1:]
    if len(argv) != 3 or argv[0] not in ("check", "check-live"):
        print(__doc__)
        sys.exit(1)
    mode, message_path, state_arg = argv
    with open(message_path, encoding="utf-8") as f:
        message = f.read()
    if mode == "check":
        open_issue_numbers = [int(x) for x in state_arg.split(",") if x.strip()]
    else:
        with open(state_arg, encoding="utf-8") as f:
            state = json.load(f)
        if not isinstance(state, dict):
            raise ClosingKeywordArgError(
                f"{state_arg}: expected a JSON dict, got {type(state).__name__}"
            )
        open_issue_numbers = [i["number"] for i in state.get("issues", [])]
    ok, dangerous = check_message(message, open_issue_numbers)
    print(format_result(ok, dangerous, message_path))
    sys.exit(0 if ok else 1)
