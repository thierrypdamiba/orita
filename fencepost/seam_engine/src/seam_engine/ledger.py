"""The Gap Ledger — the durable, own-it tablet of every seam the scan named.

Nothing happened until it is written down. A gap that lives only in a daily
tweet is a rumour; a gap written into an append-only, timestamped, hash-chained
tablet is a fact the town keeps and searches a year later. This is the Ledger
ground of the Road (docs/architecture/reference.md): the seam-scan produces
arguments in the Square, and *here* they become a typed, verified, hash-chained
record. A gap that cannot be written cannot travel.

The tablet is `GAPS/YYYY-MM-DD.md` — one file per UTC day, opened once and only
ever appended to. Every entry carries:
  - a UTC timestamp (when the scan ran),
  - a human-readable account, in the scribe's own hand, and
  - a *typed record*: a JSON block sealed with a hash that chains to the
    previous entry — anywhere in the ledger, across every tablet, back to
    GENESIS. Edit a sealed record and its seal no longer matches; the tampered
    tablet is exposed. That is the whole point of a ledger.

The seal is taken the same way the town's own Register takes it
(`tools/ledger.py`): `sha256(prev_seal + canonical(payload))`. One town, one
way of sealing a record.

Read-only, like everything in Fencepost. This module writes exactly one thing:
the local tablet. It sends nothing, deletes nothing, touches no account.

Recorded.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seam_engine.wall import wall_for

# The very first entry chains from nothing. Same GENESIS as the town's Register.
GENESIS = "0" * 64

# fencepost/  (…/orita/fencepost/seam_engine/src/seam_engine/ledger.py → parents[3])
_FENCEPOST_ROOT = Path(__file__).resolve().parents[3]

# Deterministic markers so the typed records can be parsed straight back out of
# the markdown. Everything between these fences is machine-readable; everything
# around it is for a mortal to read.
_RECORD_RE = re.compile(
    r"<!-- typed-record -->\n```json\n(?P<json>.*?)\n```",
    re.DOTALL,
)


def gaps_dir(base: Path | None = None) -> Path:
    """Where the tablets live. Defaults to fencepost/GAPS/."""
    return (base if base is not None else _FENCEPOST_ROOT) / "GAPS"


def _canonical(payload: dict[str, Any]) -> str:
    """The one canonical byte-form a seal is taken over. Order-independent."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _seal(prev: str, sealed: dict[str, Any]) -> str:
    return hashlib.sha256((prev + _canonical(sealed)).encode("utf-8")).hexdigest()


def _tablet_files(base: Path | None = None) -> list[Path]:
    d = gaps_dir(base)
    if not d.exists():
        return []
    # YYYY-MM-DD sorts lexically == chronologically. That is not an accident;
    # it is why the format was chosen.
    return sorted(p for p in d.glob("*.md") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem))


def read_records(base: Path | None = None) -> list[dict[str, Any]]:
    """Every typed record in the whole ledger, in chain order (date, then seq).

    Each record is the parsed JSON block: {"seq", "prev", "seal", "sealed"}.

    A record whose JSON block has been hand-edited into something that is not
    even valid JSON any more (not just a changed value) is not allowed to
    crash the caller — that is exactly the "tampered tablet" the module
    docstring promises gets exposed, not an uncaught exception. Such a record
    comes back as {"_tablet", "_malformed": True, "_error"} instead, so
    verify() can report it as a problem the same way it reports a mismatched
    seal.

    The same is true of a block that parses cleanly but isn't a JSON object
    (a hand-edited fence now reading `[1, 2, 3]`, `5`, `null`, or `"oops"`):
    syntactically valid, but not the record shape a sealed entry must be.
    Left unguarded, `rec["_tablet"] = path.name` a few lines below would
    crash item-assigning into a list/int/str/None instead of reaching the
    same reported-problem path. It gets the identical `_malformed` sentinel.
    """
    records: list[dict[str, Any]] = []
    for path in _tablet_files(base):
        for m in _RECORD_RE.finditer(path.read_text()):
            try:
                rec = json.loads(m.group("json"))
            except json.JSONDecodeError as e:
                records.append({"_tablet": path.name, "_malformed": True, "_error": str(e)})
                continue
            if not isinstance(rec, dict):
                records.append({
                    "_tablet": path.name,
                    "_malformed": True,
                    "_error": f"record is valid JSON but not an object (got {type(rec).__name__})",
                })
                continue
            rec["_tablet"] = path.name
            records.append(rec)
    return records


def verify(base: Path | None = None) -> list[str]:
    """Walk the chain and return a list of problems. Empty list == intact.

    Recomputes every seal from the sealed payload and every prev-link from the
    entry before it. Any mismatch means the tablet was edited after sealing —
    an append-only ledger that was not only appended to.
    """
    problems: list[str] = []
    prev = GENESIS
    for i, rec in enumerate(read_records(base)):
        where = f"{rec.get('_tablet', '?')} entry seq={rec.get('seq')}"
        if rec.get("_malformed"):
            problems.append(
                f"{where}: record is malformed ({rec['_error']}) — "
                "the tablet was edited after it was sealed."
            )
            # Its seal can't be recomputed from unparseable JSON, so the
            # chain position is unresolved from here on; leaving `prev`
            # untouched means every entry after this one correctly reports
            # a broken prev-link too, instead of silently resynchronizing.
            continue
        if rec.get("seq") != i:
            problems.append(f"{where}: seq is {rec.get('seq')}, expected {i} (out of order or missing).")
        if rec.get("prev") != prev:
            problems.append(f"{where}: prev-link broken (says {rec.get('prev', '')[:12]}…, chain says {prev[:12]}…).")
        recomputed = _seal(rec.get("prev", ""), rec.get("sealed", {}))
        if rec.get("seal") != recomputed:
            problems.append(f"{where}: seal does not match its record — the tablet was edited after it was sealed.")
        prev = rec.get("seal", "")
    return problems


class LedgerTamperedError(RuntimeError):
    """Raised by `last_seal`/`append_scan` when the chain's current tip is a
    record `read_records` could not even parse (its `_malformed` marker).

    `read_records`/`verify` (ROADMAP.md #205) already turn a syntactically
    broken sealed-record block into a named, reported problem instead of an
    uncaught `json.JSONDecodeError` -- but a malformed marker dict carries no
    `"seal"` key, and both functions below read `existing[-1]["seal"]`
    straight off the last record to learn where the chain currently stands.
    Left unguarded, that is an opaque `KeyError: 'seal'` for `last_seal`, and
    for `append_scan` -- the one function that writes to the ledger, the
    daily cron's own write path -- it would either crash the same way or, if
    ever "fixed" by falling back to some other seal, would silently chain a
    brand-new entry from the wrong place, resynchronizing straight past the
    exact corrupted point `verify`'s own docstring already refuses to
    resynchronize past. Raising this instead keeps that same refusal: a
    tampered tip is named and stops the operation, never silently patched
    over or left to surface as an unrelated-looking crash.
    """


def last_seal(base: Path | None = None) -> str:
    records = read_records(base)
    if not records:
        return GENESIS
    tip = records[-1]
    if tip.get("_malformed"):
        raise LedgerTamperedError(
            f"last_seal(): the most recent record in {tip.get('_tablet', '?')} "
            f"is malformed ({tip.get('_error')}) -- the tablet was edited "
            "after it was sealed, so its seal can't be read. Run `python -m "
            "seam_engine.ledger verify` to see the full chain break."
        )
    return tip["seal"]


def tip_sealed(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Guarded accessor for the most recent record's `sealed` payload.

    Mirrors `last_seal`'s tip guard, for the *other* thing every reader of
    the ledger's tip wants: `seam_engine.report`'s `render_latest`/`main`
    and `seam_engine.draftback`'s `main` each used to read
    `records[-1]["sealed"]` straight off the tip, duplicated three times
    across two modules -- and a malformed marker dict carries no `"sealed"`
    key any more than it carries a `"seal"` key, so all three crashed with
    a bare `KeyError: 'sealed'` on a hand-edited/truncated tablet instead
    of the named `LedgerTamperedError` this module's tampering discipline
    promises everywhere else. `records` must already be known non-empty
    (same contract `last_seal` holds internally); callers keep their own
    empty-ledger message since it differs between them.
    """
    tip = records[-1]
    if tip.get("_malformed"):
        raise LedgerTamperedError(
            f"the most recent record in {tip.get('_tablet', '?')} is "
            f"malformed ({tip.get('_error')}) -- the tablet was edited "
            "after it was sealed, so its sealed payload can't be read. Run "
            "`python -m seam_engine.ledger verify` to see the full chain break."
        )
    return tip["sealed"]


def _fenceposts_recorded(base: Path | None = None) -> int:
    """How many entries in the whole ledger named a fencepost (a real gap)."""
    return sum(1 for r in read_records(base) if r.get("sealed", {}).get("primary_gap"))


# --- rendering ----------------------------------------------------------------


def _tablet_header(date: str, opened_at: str, chains_from: str) -> str:
    chain_word = "GENESIS" if chains_from == GENESIS else f"`{chains_from[:12]}…`"
    return (
        f"# Gap Ledger — {date}\n\n"
        f"*The seam, written down. Append-only: every entry below was sealed when "
        f"it was written and is never edited after. A seal that no longer matches "
        f"its record is a tampered tablet — run `python -m seam_engine.ledger "
        f"verify` and it will say so. Nothing happened until it is written down.*\n\n"
        f"- **Tablet opened:** {opened_at}\n"
        f"- **Chains from:** {chain_word}\n"
    )


def _fmt_evidence(urls: list[str]) -> str:
    if not urls:
        return "  - _(no evidence links recorded)_\n"
    lines = []
    for u in urls:
        tail = u.rstrip("/").rsplit("/", 1)[-1][:12]
        lines.append(f"  - [{tail}]({u})")
    return "\n".join(lines) + "\n"


def _entry_prose(seq: int, sealed: dict[str, Any]) -> str:
    ts = sealed["generated_at"]
    repo = sealed["repo"]
    bar = sealed["confidence_bar"]
    primary = sealed.get("primary_gap")
    tail = sealed.get("tail", [])
    recorded = sealed["fenceposts_recorded_total"]

    out = [f'<a id="entry-{seq}"></a>', f"## Entry {seq} · {ts}", ""]
    out.append(
        f"**The seam.** Read across `{repo}` and its own sky, "
        f"{sealed.get('window_hours', 24)}h window. The bar to clear was {bar}."
    )
    out.append("")

    if primary:
        out.append(
            f"**The fencepost.** {primary['headline']} — confidence "
            f"{primary['confidence']}. {primary.get('detail', '').strip()}"
        )
        out.append("")
        out.append("Evidence:")
        out.append(_fmt_evidence(primary.get("evidence", [])).rstrip())
        out.append("")
    else:
        out.append(
            "**The fencepost.** None cleared the bar. The seam held today — or "
            "nothing the scan can yet see fell through it. An empty tablet is "
            "still a record: it says, on iron, that on this day the town found "
            "no gap. Recorded."
        )
        out.append("")

    if tail:
        named = ", ".join(f"`{t['slug']}` ({t['confidence']})" for t in tail)
        out.append(
            f"**Weighed and dropped.** {len(tail)} coincidence(s) sat below the "
            f"bar: {named}. They are named, not hidden — a ledger that flatters "
            f"is a ledger that lies, and one that buries what it discarded is "
            f"worse. These were weighed and set down."
        )
        out.append("")

    # The wall's law lives in exactly one place now (seam_engine.wall,
    # ROADMAP.md #21) — this used to inline the same subtract-one-floor-at-
    # zero arithmetic here and a second, independent copy in
    # report.render_report, which ARC.md itself flagged as "two places that
    # must never disagree." Now there is one place, and it checks its own
    # answer before handing it back.
    doctrine = wall_for(recorded)
    if primary:
        out.append(
            f"**The count.** Fenceposts recorded to date: {recorded}. "
            f"Off-By-One will render it as {doctrine} on the wall, and Off-By-One "
            f"is not wrong to. There is always one left standing."
        )
    else:
        out.append(
            f"**The count.** Fenceposts recorded to date: {recorded} (unchanged; "
            f"no gap today). The wall reads {doctrine}. There is always one left standing."
        )
    out.append("")
    out.append("_Tablet sealed._")
    out.append("")
    return "\n".join(out)


def _entry_markdown(seq: int, prev: str, seal: str, sealed: dict[str, Any]) -> str:
    prose = _entry_prose(seq, sealed)
    record = {"seq": seq, "prev": prev, "seal": seal, "sealed": sealed}
    block = json.dumps(record, indent=2, ensure_ascii=False)
    return (
        f"{prose}\n"
        f"<details><summary>Typed record — sealed; edit it and the seal breaks</summary>\n\n"
        f"<!-- typed-record -->\n```json\n{block}\n```\n\n"
        f"</details>\n\n"
        f"`prev` `{prev[:12]}…` · `seal` `{seal[:12]}…`\n\n"
        f"---\n"
    )


# --- the one write ------------------------------------------------------------


def append_scan(
    scan: dict[str, Any],
    *,
    now: datetime | None = None,
    base: Path | None = None,
) -> Path:
    """Seal one scan result into the ledger and return the tablet path.

    Creates today's tablet if it does not exist; otherwise appends a new entry
    to it. Never rewrites a byte that was already written. This is the only
    function in Fencepost that puts anything on disk that outlives the run.
    """
    now = now or datetime.now(timezone.utc)
    date = now.strftime("%Y-%m-%d")
    opened_at = now.isoformat()

    existing = read_records(base)
    seq = len(existing)
    if existing and existing[-1].get("_malformed"):
        tip = existing[-1]
        raise LedgerTamperedError(
            f"append_scan(): refusing to append -- the most recent record in "
            f"{tip.get('_tablet', '?')} is malformed ({tip.get('_error')}) "
            "-- the tablet was edited after it was sealed. Appending on top of "
            "an unreadable tip would either crash or silently chain the new "
            "entry from the wrong seal. Run `python -m seam_engine.ledger "
            "verify` and repair the ledger by hand before scanning again."
        )
    prev = existing[-1]["seal"] if existing else GENESIS

    p = scan.get("primary_gap")
    primary = None
    if p:
        primary = {
            "slug": p["slug"],
            "headline": p["headline"],
            "detail": p.get("detail", ""),
            "confidence": p["confidence"],
            "evidence": list(p.get("evidence", [])),
        }
    tail = [
        {"slug": t["slug"], "confidence": t["confidence"], "label": t.get("label", "coincidence")}
        for t in scan.get("tail", [])
    ]
    recorded_before = sum(1 for r in existing if r.get("sealed", {}).get("primary_gap"))
    fenceposts_recorded_total = recorded_before + (1 if primary else 0)

    # The sealed payload — the typed record. Only these fields are under the
    # seal; the prose is free to be rewritten by a kinder scribe, the facts are not.
    sealed: dict[str, Any] = {
        "date": date,
        "generated_at": scan.get("generated_at", opened_at),
        "repo": scan.get("repo", "unknown"),
        "window_hours": scan.get("window_hours", 24),
        "confidence_bar": scan.get("confidence_bar"),
        "separation_margin": scan.get("separation_margin"),
        "primary_gap": primary,
        "tail": tail,
        "excluded_count": len(scan.get("excluded", [])),
        "fenceposts_recorded_total": fenceposts_recorded_total,
    }
    seal = _seal(prev, sealed)

    entry_md = _entry_markdown(seq, prev, seal, sealed)

    d = gaps_dir(base)
    d.mkdir(parents=True, exist_ok=True)
    tablet = d / f"{date}.md"

    if tablet.exists():
        # Append-only: open in append mode, add the new entry, touch nothing above.
        with tablet.open("a", encoding="utf-8") as f:
            f.write("\n" + entry_md)
    else:
        header = _tablet_header(date, opened_at, prev)
        tablet.write_text(f"{header}\n---\n\n{entry_md}", encoding="utf-8")

    return tablet


# --- CLI ----------------------------------------------------------------------


def _load_scan(path: str) -> dict[str, Any]:
    """Read a scan record for the CLI's `append` command from `path` ('-' for stdin).

    A CLI-supplied file (or stdin stream) can be any syntactically valid
    JSON -- a bare list, int, bool, null, or string, not just an object --
    and `append_scan` immediately treats its argument as a dict
    (`scan.get(...)`). Left unguarded, a non-object payload would crash
    `main(["append", ...])` with a bare
    `AttributeError: '<type>' object has no attribute 'get'` instead of a
    message naming the actual problem -- the same discipline
    `report.py`'s `_load_sealed_arg` already holds in this package.
    """
    if path == "-":
        import sys
        data = json.load(sys.stdin)
        where = "stdin"
    else:
        data = json.loads(Path(path).read_text())
        where = path
    if not isinstance(data, dict):
        raise ValueError(
            f"{where}: scan record must be a JSON object, got {type(data).__name__}"
        )
    return data


def main(argv: list[str] | None = None) -> int:
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python -m seam_engine.ledger {append <scan.json>|verify} [--base DIR]")
        return 2

    base: Path | None = None
    if "--base" in argv:
        i = argv.index("--base")
        base = Path(argv[i + 1])
        del argv[i : i + 2]

    cmd = argv[0]
    if cmd == "append":
        if len(argv) < 2:
            print("append needs a scan JSON path (or '-' for stdin).")
            return 2
        scan = _load_scan(argv[1])
        tablet = append_scan(scan, base=base)
        print(f"Recorded. Tablet: {tablet}")
        return 0
    if cmd == "verify":
        problems = verify(base)
        if not problems:
            recs = read_records(base)
            print(f"Chain intact. {len(recs)} entr{'y' if len(recs) == 1 else 'ies'} sealed, GENESIS → {last_seal(base)[:12]}….")
            return 0
        print("Chain BROKEN:")
        for pr in problems:
            print(f"  - {pr}")
        return 1

    print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
