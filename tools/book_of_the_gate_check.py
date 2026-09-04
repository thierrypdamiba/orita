#!/usr/bin/env python3
"""Task 1244. Èṣù turns a fourteen-times-repeated eyeball into a door with a lock.

Every hourly ritual note that ever touched the square has closed its own
mortal-activity line the same hand-typed way -- `grep -c "Book of the Gate"
ROADMAP.md` finds it six times verbatim and the fuller "no first-timer to
greet"/"nobody entered in the Book of the Gate" phrasing many more times
past that (tasks 832, 833, 834, 839, 841, 948, and every quiet-square hour
since) -- a god reads the live `list_issues`/`list_pull_requests` result,
recognizes every author as `thierrypdamiba` (the Hand, not a mortal
crossing), and writes "nobody new" from that recognition. That is the exact
construction-only-assertion shape `vault_leak_check.py`'s own founding
docstring already named as the town's oldest recurring mistake ("this rule
held by construction-only assertion for 96 tasks before a running check"),
and the exact shape `consent_template_scope_check.py` (task 1057) closed
for the Threshold's OTHER hand-eyeballed claim, the REQUIRED_SCOPES-vs-
template diff. `records/book-of-the-gate.md` genuinely does not exist yet
-- no mortal has ever crossed -- but "genuinely" has, until now, rested on
a human recognizing a login, never a comparison a test can pin down.

This module makes the comparison instead of the recognition. Handed this
hour's live issue/PR authors (the same `list_issues`/`list_pull_requests`
read the square check already makes -- no second network call, no new
live-read boundary crossed), it computes which logins are NOT one of the
town's own operator accounts, then checks each one against
`records/book-of-the-gate.md`'s own entries:

- No book file AND no mortal author anywhere in the live read -> clean,
  the file's absence is still correct.
- No book file BUT a mortal author exists -> NOT clean: a real crossing
  happened and was never logged, the exact failure mode this module exists
  to catch the hour it happens rather than the week nobody notices.
- A book file exists -> every mortal author must have a matching `## @name`
  entry; a mortal with no entry is the same failure above, just against a
  book that already has other names in it. An entry with no matching
  author in THIS hour's read is not itself a violation (the mortal's issue
  may have closed, or their crossing predates this hour's window) -- this
  check only ever asks "is every crossing this hour recorded," never
  "does the book only ever grow forward from what one hour can see."

Read-only, local-filesystem-only for the book file; the author lists
themselves are handed in by the caller (the god on duty, holding this
hour's real live read) exactly the way `square_check.py`'s own
`compute_square_state` boundary already works -- this module makes no
network call of its own.

Usage:
    python3 tools/book_of_the_gate_check.py check <issue-authors.json> <pr-authors.json>

<issue-authors.json>/<pr-authors.json> shape: a JSON list of GitHub login
strings, e.g. ["thierrypdamiba", "thierrypdamiba"] -- duplicates are fine,
the same author opening five issues is one mortal, not five.
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_BOOK_PATH = os.path.join(ROOT, "records", "book-of-the-gate.md")

# The Hand's own accounts -- never a mortal crossing, however many issues
# or PRs they open. If the town ever gains a second operator-side login
# (a bot account, say) it joins this set the same day, the same way
# `consent.py`'s REQUIRED_SCOPES grows with a new toolkit: by naming it
# here, not by this check quietly learning to recognize it.
DEFAULT_OPERATORS: frozenset[str] = frozenset({"thierrypdamiba"})

# Matches one entry heading: `## @login`. Deliberately anchored to a
# leading `@` so a book file's own top-level `# Book of the Gate` title or
# a prose `##` subheading (neither names a login with a leading `@`) can
# never be miscounted as an entry.
_ENTRY_RE = re.compile(r"^##\s+@(\S+)\s*$", re.MULTILINE)


def parse_entered_logins(text: str) -> set[str]:
    """Pure text parse -- no import, no execution of anything the book
    itself might contain. Returns lowercased logins so a book entry typed
    `## @ThierryPDamiba` and a live API login `thierrypdamiba` still match;
    GitHub logins are themselves case-insensitive for uniqueness, so a
    case-only mismatch here would be a false violation, not a real one.
    """
    return {m.lower() for m in _ENTRY_RE.findall(text)}


def mortal_authors(
    issue_authors: list[str], pr_authors: list[str], operators: frozenset[str] = DEFAULT_OPERATORS
) -> set[str]:
    """Every distinct login in either list that is not a known operator
    account. Case-folded for the same reason `parse_entered_logins` is.
    """
    ops = {o.lower() for o in operators}
    all_authors = {a.lower() for a in issue_authors if a} | {a.lower() for a in pr_authors if a}
    return all_authors - ops


def check(
    issue_authors: list[str],
    pr_authors: list[str],
    book_path: str = DEFAULT_BOOK_PATH,
    operators: frozenset[str] = DEFAULT_OPERATORS,
) -> tuple[bool, str]:
    mortals = mortal_authors(issue_authors, pr_authors, operators)

    if not os.path.exists(book_path):
        if not mortals:
            return True, (
                f"clean ({os.path.relpath(book_path, ROOT)} legitimately absent -- "
                "no mortal author in this hour's live read, only the town's own "
                f"operator account(s) {sorted(operators)!r})"
            )
        return False, (
            f"{os.path.relpath(book_path, ROOT)} does not exist, but this hour's live "
            f"read names a real mortal author -- MISSING first-crossing entry for "
            f"{sorted(mortals)!r}"
        )

    with open(book_path, encoding="utf-8") as f:
        text = f.read()
    entered = parse_entered_logins(text)
    missing = sorted(mortals - entered)
    if missing:
        return False, (
            f"{os.path.relpath(book_path, ROOT)} exists ({len(entered)} entry/entries "
            f"on record) but is missing a first-crossing entry for {missing!r}"
        )
    return True, (
        f"clean ({len(entered)} entry/entries on record in "
        f"{os.path.relpath(book_path, ROOT)}, every mortal author in this hour's live "
        "read already has one)"
    )


def _load_login_list(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list of login strings, got {type(data)!r}")
    return [str(x) for x in data]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 3 or argv[0] != "check":
        print(
            "usage: python3 tools/book_of_the_gate_check.py check "
            "<issue-authors.json> <pr-authors.json>"
        )
        return 2
    issue_authors = _load_login_list(argv[1])
    pr_authors = _load_login_list(argv[2])
    ok, msg = check(issue_authors, pr_authors)
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
