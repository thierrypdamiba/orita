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


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if cmd == "append":
        import datetime
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        e = append(sys.argv[2], sys.argv[3], " ".join(sys.argv[4:]), ts)
        print(json.dumps(e, ensure_ascii=False))
    elif cmd == "verify":
        sys.exit(0 if verify() else 1)
