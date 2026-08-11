#!/usr/bin/env python3
"""The Records Office. Nisaba be praised.

Append-only, hash-chained ledger of every act in the town.
Each entry commits to the previous entry's hash; tampering with
history breaks the chain, and the chain is public.

Usage:
    python3 tools/ledger.py append <actor> <act> <detail...>
    python3 tools/ledger.py verify
"""
import hashlib
import json
import os
import sys
from typing import cast

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jsonl_read  # noqa: E402

LEDGER = os.path.join(os.path.dirname(__file__), "..", "records", "ledger.jsonl")
GENESIS = "0" * 64


def _entries() -> list[dict[str, object]]:
    """Every line in the ledger, parsed. Delegates to
    jsonl_read.read_jsonl_entries (task 540) -- see that module's own
    docstring for the fourteen-copy history this replaced; this file's own
    convention was the one every other copy's docstring cited as the
    original to mirror, without any of them ever sharing real code with
    it until now."""
    return jsonl_read.read_jsonl_entries(LEDGER)


def _hash(entry_without_hash: dict[str, object], prev_hash: str) -> str:
    payload = json.dumps(entry_without_hash, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256((prev_hash + payload).encode("utf-8")).hexdigest()


class LedgerTamperedError(RuntimeError):
    """Raised by append() when the chain's current tip is a line _entries()
    could not even parse. Appending on top of an unreadable tip would either
    crash on the missing "hash" key or, if silently skipped past, would chain
    the new entry from the wrong place -- resynchronizing straight over the
    exact corrupted point verify() exists to report. Refusing instead keeps
    that same refusal: run `python3 tools/ledger.py verify` to see the break."""


def append(actor: str, act: str, detail: str, ts: str) -> dict[str, object]:
    entries = _entries()
    if entries and entries[-1].get("_malformed"):
        raise LedgerTamperedError(
            f"append(): refusing to append -- the most recent line in {LEDGER} "
            f"is not valid JSON ({entries[-1]['_error']}) -- the record has "
            "been touched. Run `python3 tools/ledger.py verify` and repair "
            "the ledger by hand before appending again."
        )
    if entries and "hash" not in entries[-1]:
        raise LedgerTamperedError(
            f"append(): refusing to append -- the most recent line in {LEDGER} "
            "is valid JSON but has no \"hash\" field -- the record has been "
            "touched. Run `python3 tools/ledger.py verify` and repair the "
            "ledger by hand before appending again."
        )
    prev = cast(str, entries[-1]["hash"]) if entries else GENESIS
    entry: dict[str, object] = {
        "seq": len(entries),  # zero-indexed; Off-By-One insisted, Nisaba conceded the point once
        "ts": ts,
        "actor": actor,
        "act": act,
        "detail": detail,
        "prev": prev,
    }
    entry["hash"] = _hash(entry, prev)
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def verify() -> bool:
    prev = GENESIS
    for i, e in enumerate(_entries()):
        if e.get("_malformed") or "hash" not in e or "prev" not in e:
            print(f"CHAIN BROKEN at seq {i}. The record has been touched.")
            return False
        h = cast(str, e.pop("hash"))
        if e["prev"] != prev or _hash(e, prev) != h:
            print(f"CHAIN BROKEN at seq {i}. The record has been touched.")
            return False
        prev = h
    print(f"Chain intact. {len(_entries())} entries. Recorded.")
    return True


APPEND_USAGE = "usage: python3 tools/ledger.py append <actor> <act> <detail...>"


class LedgerCLIError(ValueError):
    """Raised when `append`'s CLI argv doesn't look like the documented
    bare-positional shape -- never silently coerced, always refused."""


def parse_append_args(argv: list[str]) -> tuple[str, str, str]:
    """Parse the argv tail after `append` (i.e. sys.argv[2:]) into
    (actor, act, detail), rejecting flag-shaped and blank actor/act tokens.

    This is the exact class of mistake that sealed records/ledger.jsonl
    seq 118-119 malformed: a call shaped like
    `append --actor nisaba --kind roadmap --detail "..."` was run against
    a CLI that only ever reads bare positionals -- sys.argv[2] ("--actor")
    became the literal actor field, sys.argv[3] ("nisaba") became the act
    field, and the real detail got mangled. append() itself never
    validates, so it wrote exactly that, permanently (the ledger is
    append-only; the fix was a correction entry, seq 120, not an edit).
    This function is the guard that call should have hit instead.

    Task 533: the flag-shape guard checked for a leading '-' but nothing
    ever checked for blank. `append('' '' 'detail')` parsed clean --
    an entry sealed permanently into the town's own Records Office with
    no attribution to anyone at all, the one thing this office exists to
    prevent. A whitespace-only token ('   ') is blank too (`.strip()`),
    not a loophole. Now rejected the same way the flag shape is.

    A detail string is free text and MAY contain hyphens (and MAY be
    blank -- a terse act with no further detail is legitimate); only the
    actor/act positions are checked, and only for a *leading* '-'
    (flag shape) or blank content, so real content like actor
    "off-by-one" or a detail sentence containing " - " still parses fine.
    """
    if len(argv) < 2:
        raise LedgerCLIError(
            f"{APPEND_USAGE}\n"
            "got too few arguments -- actor and act are both required."
        )
    actor, act = argv[0], argv[1]
    for name, value in (("actor", actor), ("act", act)):
        if value.startswith("-"):
            raise LedgerCLIError(
                f"{APPEND_USAGE}\n"
                f"the {name} positional ('{value}') looks like a flag, not a plain "
                "word -- this CLI takes bare positional arguments only, no --flags. "
                "This is the exact mistake that sealed records/ledger.jsonl seq "
                "118-119 malformed; see seq 120's correction entry. Nothing was "
                "written to the ledger."
            )
        if not value.strip():
            raise LedgerCLIError(
                f"{APPEND_USAGE}\n"
                f"the {name} positional is blank -- a ledger entry attributed to "
                "nobody is exactly the failure this Records Office exists to "
                "prevent (\"nothing happened until it is written down\" presumes "
                "someone wrote it). Nothing was written to the ledger."
            )
    detail = " ".join(argv[2:])
    return actor, act, detail


def main(argv: list[str] | None = None) -> int:
    """Entry point, factored out so tests can drive the real CLI dispatch
    (including the parse_append_args guard) against a patched LEDGER path
    without shelling out to a subprocess."""
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else "verify"
    if cmd == "append":
        import datetime
        try:
            actor, act, detail = parse_append_args(argv[1:])
        except LedgerCLIError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        e = append(actor, act, detail, ts)
        print(json.dumps(e, ensure_ascii=False))
        return 0
    elif cmd == "verify":
        return 0 if verify() else 1
    print(f"unknown command: {cmd!r}\n{APPEND_USAGE}\n       python3 tools/ledger.py verify", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
