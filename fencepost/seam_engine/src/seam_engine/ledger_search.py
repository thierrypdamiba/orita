"""Searching the tablet — the Ledger kept a year, not just written once.

`ledger.py`'s own module docstring makes the promise: a sealed gap is "a
fact the town keeps and searches a year later," not a rumour that lives
only in a daily tweet (Nisaba's law, `STRATEGY.md`'s "Standing laws from
the dissents": *"the Gap Ledger is written back to a place the user owns —
a first-class, durable, you-own-it record, never just a diff"*). Until this
module, that promise had no instrument behind it: `ledger.read_records`
loads every sealed entry in chain order, but finding one entry among
hundreds — "what did the ledger say about `milestone-unannounced` back in
August," "show me every day a different gap led" — meant grepping raw
markdown fences by hand, the exact kind of un-instrumented claim
(`ritual_check.py`'s own genealogy of "claims a boundary, never checked
against it") this codebase has closed everywhere else it was found. A
record that can only be found by someone who already knows which file to
grep is not meaningfully "searchable."

This is a pure, read-only filter over what `ledger.read_records` already
returns — no new state, no new file, nothing that can drift from the
Ledger it reads. `search()` matches on the sealed entry's `date` (exact, or
a `since`/`until` range, inclusive on both ends — plain ISO `YYYY-MM-DD`
string comparison, which is correct because every tablet date is already
written in that form) and/or `slug` (checked against the primary gap AND
every tail candidate that scan run also recorded, so "when did
`coincidence-automatic` ever even place" is answerable, not only "when was
the primary"). All filters given must hold (AND, not OR) — an empty filter
set matches everything, chain order, oldest first.

A malformed tablet entry (`ledger.read_records`'s own `_malformed`
sentinel — a hand-edited fence that no longer parses) cannot be matched
against anything (no `sealed` dict to read); `search()` skips it rather
than raising, but `search()` never pretends the ledger is intact either —
`verify()` is still the one place that promise gets checked, and this
module's own docstring is not the place to repeat work it already does.
Skipped malformed entries are counted and returned alongside the hits, so
a search run against a genuinely tampered ledger is visibly incomplete
rather than silently confident.

Read-only, like everything in Fencepost: this module writes nothing,
sends nothing, calls nothing beyond the local filesystem `ledger.py`
already reads.

Recorded, then found again. — Nisaba
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from seam_engine import ledger


def _sealed_slugs(sealed: dict[str, Any]) -> set[str]:
    """Every gap slug a sealed entry ever named: the primary, plus its tail."""
    slugs: set[str] = set()
    primary = sealed.get("primary_gap")
    if primary:
        slugs.add(primary["slug"])
    for t in sealed.get("tail", []):
        slugs.add(t["slug"])
    return slugs


def matches(
    sealed: dict[str, Any],
    *,
    slug: str | None = None,
    date: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> bool:
    """True iff this one sealed entry clears every filter given.

    `date`/`since`/`until` compare against the sealed entry's own `date`
    field (`YYYY-MM-DD`), not `generated_at` — the date a tablet was opened
    under, matching how `ledger.gaps_dir`'s own `<date>.md` naming works.
    """
    entry_date = sealed.get("date", "")
    if date is not None and entry_date != date:
        return False
    if since is not None and entry_date < since:
        return False
    if until is not None and entry_date > until:
        return False
    if slug is not None and slug not in _sealed_slugs(sealed):
        return False
    return True


def search(
    records: list[dict[str, Any]],
    *,
    slug: str | None = None,
    date: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Filter `ledger.read_records`'s own output; never re-reads the ledger.

    Returns `(hits, skipped_malformed_count)` — chain order preserved,
    oldest first, same as `read_records` itself.
    """
    hits: list[dict[str, Any]] = []
    skipped = 0
    for rec in records:
        if rec.get("_malformed"):
            skipped += 1
            continue
        sealed = rec.get("sealed")
        if not isinstance(sealed, dict):
            skipped += 1
            continue
        if matches(sealed, slug=slug, date=date, since=since, until=until):
            hits.append(rec)
    return hits, skipped


def format_hit(rec: dict[str, Any]) -> str:
    """One readable line per hit: seq, date, matched slug(s), confidence."""
    sealed = rec["sealed"]
    primary = sealed.get("primary_gap")
    if primary:
        headline = f"{primary['slug']} ({primary['confidence']}) — {primary['headline']}"
    else:
        headline = "(no primary gap cleared the bar this run)"
    tail_slugs = sorted(t["slug"] for t in sealed.get("tail", []))
    tail_note = f"; tail: {', '.join(tail_slugs)}" if tail_slugs else ""
    return f"seq {rec['seq']:>5} | {sealed.get('date', '?')} | {headline}{tail_note}"


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    def _take(flag: str) -> str | None:
        if flag not in argv:
            return None
        i = argv.index(flag)
        if i + 1 >= len(argv):
            print(f"{flag} needs a value.")
            raise SystemExit(2)
        val = argv[i + 1]
        del argv[i : i + 2]
        return val

    base: Path | None = None
    base_arg = _take("--base")
    if base_arg is not None:
        base = Path(base_arg)
    slug = _take("--slug")
    date = _take("--date")
    since = _take("--since")
    until = _take("--until")

    if argv:
        print(f"unrecognized argument(s): {argv}")
        print(
            "usage: python -m seam_engine.ledger_search "
            "[--slug SLUG] [--date YYYY-MM-DD] [--since YYYY-MM-DD] "
            "[--until YYYY-MM-DD] [--base DIR]"
        )
        return 2

    records = ledger.read_records(base)
    hits, skipped = search(records, slug=slug, date=date, since=since, until=until)

    for rec in hits:
        print(format_hit(rec))
    if not hits:
        print("no matching entries sealed")
    print(f"\n{len(hits)} of {len(records)} sealed entries matched.", file=sys.stderr)
    if skipped:
        print(
            f"warning: {skipped} tablet entry/entries were malformed and "
            "could not be searched — run `python -m seam_engine.ledger verify` "
            "to see which.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
