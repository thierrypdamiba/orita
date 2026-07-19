"""The double-checked consent gate — Èṣù's own door, made to hold.

STRATEGY.md swears it plainly: "The town dogfoods ONLY its own bot accounts
until a real consenting human (the Hand) explicitly opts in via the
intent-gated issue + scope confirm." docs/threat-model.md names the wound
this closes — *"the world moves with no real judge... an `operatorId` in a
request body treated as identity"* — and its own fix: *"judging is its own
ground — the Gate — never a flag in a form."* A form is precisely what an
issue is. This module is what keeps the form from being mistaken for the
judgment.

Two checks, not one, and neither is decoration for the other:

1. **A public issue.** The human's true intent, stated in the open, on a
   real GitHub issue — the same "Point Fencepost at my accounts" crossing
   task 9 built (`.github/ISSUE_TEMPLATE/point-fencepost.md`). Anyone can
   read it later; nothing about a consent to be read happens in private.
2. **An explicit scope confirm.** Not "yes." Not a checked box. The exact,
   per-toolkit tool names the human is granting — typed back verbatim
   against the same table SCOPES.md swears to (`REQUIRED_SCOPES` below) —
   so a rubber-stamped "I agree" can never stand in for actually having
   read what is being agreed to.

Both checks must independently hold before a single byte of a HUMAN's own
account is read. Neither one, alone, opens the door — a public issue with
no scope confirm is a stated wish, not a grant; a scope confirm with no
public issue is a private claim nobody can audit. `enforce_consent_gate`
runs both, in order, and raises before either loader in `gmail_calendar.py`
(or any future human-account reader) is ever called. This module reads
nothing and writes nothing itself — like `gateway.is_read_only_capabilities`,
it is pure judgment, not action. Judging and reading are kept on different
ground, on purpose, the same law the Road already keeps between the Gate
and the Mortal World.

This gate governs only HUMAN accounts. The town's own dogfood
(`scan.py`, against `the-hand`, a dedicated bot account) is not gated here —
STRATEGY.md is explicit that the town's own bot accounts are exempt; a
fencepost gate that also blocked the town's own dogfood would be a door with
no other side. The moment `gmail_calendar.py` (or any future module) reads a
real, connected human's inbox instead of a fixture, it MUST run its read
through `enforce_consent_gate` first — see `run_consented_gmail_calendar_scan`.

A door held shut by two different locks does not open because you are
holding one key very tightly. — Èṣù-Elegba
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

# The exact per-toolkit read-only tool names, mirrored verbatim from
# SCOPES.md's "Fencepost uses" column. Not paraphrased — a scope confirm is
# checked against these names character-for-character, the same discipline
# gateway.READ_ONLY_CAPABILITIES holds itself to against its own doctrine
# test. If SCOPES.md ever grows a new toolkit, this dict grows with it or a
# consent for that toolkit can never pass — the gate fails closed by
# construction, not by memory.
REQUIRED_SCOPES: dict[str, frozenset[str]] = {
    "github": frozenset({
        "GetRepository", "ListRepoCommits", "ListIssues", "GetIssue",
        "ListPullRequests", "ListRepositoryActivities", "CountStargazers",
        "GetLatestRelease",
    }),
    "x": frozenset({"GetUserTweets", "GetMyMentions", "WhoAmI"}),
    "gmail": frozenset({"ListEmails", "GetEmail", "SearchThreads"}),
    "google_calendar": frozenset({"ListEvents", "GetEvent"}),
}

# A public issue must be a real, reachable GitHub issue URL — not a private
# doc, not a DM, not a slug someone typed and swears exists. The pattern is
# deliberately generic (any owner/repo) so a fork's own consent issues still
# pass; what makes it "public" is the github.com/.../issues/<n> shape itself,
# not which repo it lives in.
_ISSUE_URL_RE = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+/issues/\d+$")


class ConsentRequiredError(PermissionError):
    """Raised when a read on a human account is attempted without a valid,
    double-checked consent. Both checks are named in the message so a caller
    (or a test) can see exactly which lock did not turn — never a bare
    refusal. The gate is shut; nothing downstream of this exception has run.
    """


@dataclass(frozen=True)
class ConsentRecord:
    """One human's double-checked consent, for one toolkit.

    A separate record is required per toolkit on purpose — confirming Gmail
    scopes is not a confirmation of Calendar scopes, even inside the same
    issue and even in the same breath. Two toolkits, two locks; the human
    said yes to each one specifically or the gate treats it as unsaid.
    """

    human: str
    issue_url: str
    toolkit: str
    confirmed_scopes: frozenset[str]
    confirmed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def check_public_issue(record: ConsentRecord) -> tuple[bool, str]:
    """Check 1 of 2: a real, public GitHub issue backs this consent."""
    if not record.issue_url:
        return False, "no issue_url on the consent record — the door has nothing public behind it"
    if not _ISSUE_URL_RE.match(record.issue_url):
        return False, (
            f"issue_url {record.issue_url!r} is not a public "
            "github.com/<owner>/<repo>/issues/<n> URL"
        )
    return True, "public issue present"


def check_scope_confirm(record: ConsentRecord) -> tuple[bool, str]:
    """Check 2 of 2: the human's own scope list matches SCOPES.md, verbatim.

    Not "did they say yes" — did they name the *exact* tools, no more, no
    fewer. A record confirming a subset is under-confirmed (something is
    still ungranted); a record confirming a superset asked for more than the
    oath allows and cannot be honored as written, even if the extra names
    are themselves read-only — the whole point of a verbatim check is that
    nobody, gate included, gets to decide on the human's behalf that "close
    enough" is the same as "confirmed."
    """
    required = REQUIRED_SCOPES.get(record.toolkit)
    if required is None:
        return False, f"unknown toolkit {record.toolkit!r} — not in SCOPES.md's read-only oath"
    if record.confirmed_scopes != required:
        missing = sorted(required - record.confirmed_scopes)
        extra = sorted(record.confirmed_scopes - required)
        return False, (
            f"scope confirm for {record.toolkit!r} does not match SCOPES.md verbatim "
            f"(missing={missing}, extra={extra})"
        )
    return True, "scopes confirmed verbatim against SCOPES.md"


def enforce_consent_gate(record: ConsentRecord | None, *, toolkit: str) -> ConsentRecord:
    """The gate itself. Call this before one byte of a human account is read.

    Runs both checks, in order, and raises `ConsentRequiredError` the moment
    either fails — a partial pass is not a pass. Returns the record only if
    every lock turned. This function performs no I/O of its own: it reads no
    file, calls no network, opens no account. It only decides whether the
    caller is allowed to.
    """
    if record is None:
        raise ConsentRequiredError(
            f"no consent record on file for toolkit={toolkit!r} — the gate is shut"
        )
    if record.toolkit != toolkit:
        raise ConsentRequiredError(
            f"consent record is for toolkit={record.toolkit!r}, not {toolkit!r} — "
            "a confirm for one toolkit does not open the door for another"
        )

    ok_issue, why_issue = check_public_issue(record)
    if not ok_issue:
        raise ConsentRequiredError(f"consent check 1/2 (public issue) failed: {why_issue}")

    ok_scopes, why_scopes = check_scope_confirm(record)
    if not ok_scopes:
        raise ConsentRequiredError(f"consent check 2/2 (scope confirm) failed: {why_scopes}")

    return record


def enforce_consent_for_toolkits(
    records: dict[str, ConsentRecord | None], *, toolkits: tuple[str, ...]
) -> dict[str, ConsentRecord]:
    """Gate several toolkits at once (e.g. Gmail AND Calendar together).

    Every named toolkit must clear `enforce_consent_gate` independently — a
    consent dict missing an entry for any required toolkit blocks the whole
    read, not just that toolkit's half of it, since a Gmail-vs-Calendar scan
    with only one side consented cannot honestly read either.
    """
    cleared: dict[str, ConsentRecord] = {}
    for toolkit in toolkits:
        cleared[toolkit] = enforce_consent_gate(records.get(toolkit), toolkit=toolkit)
    return cleared
