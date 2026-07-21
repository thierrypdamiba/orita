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

# GitHub's real closing-keyword grammar: exactly these 9 forms, each
# optionally followed by a colon, then whitespace, then #<digits> --
# GitHub's own docs name the colon form explicitly ("Closes: #10" closes
# on push exactly like "Closes #10"; docs.github.com, "Using keywords in
# issues and pull requests"). Deliberately wider than
# fencepost/RECIPES/merged-pr-issue-still-open/detector.py's own
# `closes?|fixes?|resolves?` (that module never needed the past tense,
# this one must, because "closed #1" and "fixed #2" both close on push
# exactly as their present-tense siblings do).
CLOSING_KEYWORD_RE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?):?\s+#(\d+)\b",
    re.IGNORECASE,
)


def find_closing_refs(text: str) -> list:
    """Every issue/PR number a GitHub-recognized closing keyword names in
    `text`, in first-seen order, de-duplicated. No exemptions -- see the
    module docstring for why quotes/backticks are not treated as safe."""
    seen = []
    for m in CLOSING_KEYWORD_RE.finditer(text):
        n = int(m.group(1))
        if n not in seen:
            seen.append(n)
    return seen


def dangerous_refs(text: str, open_issue_numbers) -> list:
    """The subset of `find_closing_refs(text)` that names a number
    currently open in the repo -- the only refs GitHub can actually act
    on. A closing-keyword phrase naming an already-closed or nonexistent
    number is inert; not flagged."""
    open_set = set(open_issue_numbers)
    return [n for n in find_closing_refs(text) if n in open_set]


def check_message(message: str, open_issue_numbers) -> tuple:
    """Returns (ok: bool, dangerous: list[int]). ok is False iff pushing
    `message` to the default branch would auto-close a live open issue."""
    refs = dangerous_refs(message, open_issue_numbers)
    return (not refs, refs)


def format_result(ok: bool, dangerous: list, message_path: str) -> str:
    if ok:
        return f"closing keyword guard: clean -- {message_path} names no open issue via a real closing keyword"
    return (
        f"closing keyword guard: DANGEROUS -- {message_path} would close "
        f"open issue(s) {dangerous} on push. Rewrite: describe the pattern "
        f"in prose (e.g. 'closing #{dangerous[0]}') instead of the live "
        f"imperative form GitHub parses."
    )


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
        open_issue_numbers = [i["number"] for i in state.get("issues", [])]
    ok, dangerous = check_message(message, open_issue_numbers)
    print(format_result(ok, dangerous, message_path))
    sys.exit(0 if ok else 1)
