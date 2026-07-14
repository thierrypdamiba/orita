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

LEDGER = os.path.join(os.path.dirname(__file__), "..", "records", "ledger.jsonl")
GENESIS = "0" * 64


def _entries():
    if not os.path.exists(LEDGER):
        return []
    with open(LEDGER) as f:
        return [json.loads(line) for line in f if line.strip()]


def _hash(entry_without_hash: dict, prev_hash: str) -> str:
    payload = json.dumps(entry_without_hash, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256((prev_hash + payload).encode("utf-8")).hexdigest()


def append(actor: str, act: str, detail: str, ts: str) -> dict:
    entries = _entries()
    prev = entries[-1]["hash"] if entries else GENESIS
    entry = {
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
        h = e.pop("hash")
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


def parse_append_args(argv: list) -> tuple:
    """Parse the argv tail after `append` (i.e. sys.argv[2:]) into
    (actor, act, detail), rejecting flag-shaped actor/act tokens.

    This is the exact class of mistake that sealed records/ledger.jsonl
    seq 118-119 malformed: a call shaped like
    `append --actor nisaba --kind roadmap --detail "..."` was run against
    a CLI that only ever reads bare positionals -- sys.argv[2] ("--actor")
    became the literal actor field, sys.argv[3] ("nisaba") became the act
    field, and the real detail got mangled. append() itself never
    validates, so it wrote exactly that, permanently (the ledger is
    append-only; the fix was a correction entry, seq 120, not an edit).
    This function is the guard that call should have hit instead.

    A detail string is free text and MAY contain hyphens; only the
    actor/act positions are checked, and only for a *leading* '-'
    (flag shape), so real content like actor "off-by-one" or a detail
    sentence containing " - " still parses fine.
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
    detail = " ".join(argv[2:])
    return actor, act, detail


def main(argv=None) -> int:
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
