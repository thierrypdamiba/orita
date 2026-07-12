"""The Fencepost Report — the daily dispatch, not the tablet.

The Ledger (`ledger.py`) keeps everything: the elected gap, every coincidence
weighed and dropped, sealed and hash-chained, for the mortal who comes back a
year later to check the town's arithmetic. The Report is the other half of the
same job and answers to a different reader — the one who has thirty seconds:
one gap, named plainly, and the line the whole arc turns on.

    You were so close. You are always so close.

A report never shows the coincidence tail. Naming six things that were *not*
the gap is honest bookkeeping in a tablet and noise in a dispatch — the reader
came for the one thing, not the ranking that produced it. If nothing cleared
the bar, the report says so in one line and stops; a quiet seam is still the
truth, and Nisaba corrects flattering numbers downward on principle, never up.

Pure and deterministic: `render_report` takes the same `sealed` shape a
ledger entry carries (see `ledger.append_scan`) and returns text. No I/O
except the thin CLI at the bottom, which reads the ledger and, on request,
writes `REPORTS/YYYY-MM-DD.md` — a rendering of what the ledger already
sealed, never a second source of truth.

Recorded.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from seam_engine import ledger

# fencepost/  (…/fencepost/seam_engine/src/seam_engine/report.py → parents[3])
_FENCEPOST_ROOT = Path(__file__).resolve().parents[3]

THE_LINE = "You were so close. You are always so close."


def reports_dir(base: Path | None = None) -> Path:
    """Where rendered dispatches live. Defaults to fencepost/REPORTS/."""
    return (base if base is not None else _FENCEPOST_ROOT) / "REPORTS"


def _fmt_evidence(urls: list[str], limit: int = 3) -> str:
    if not urls:
        return ""
    lines = []
    for u in urls[:limit]:
        tail = u.rstrip("/").rsplit("/", 1)[-1][:12]
        lines.append(f"- [{tail}]({u})")
    return "\n".join(lines)


def render_report(sealed: dict[str, Any]) -> str:
    """Render one Fencepost Report from a sealed (or scan) record.

    `sealed` carries the same fields a ledger entry's typed record does:
    date/generated_at, repo, primary_gap, fenceposts_recorded_total. The tail
    is read but never shown — a report names the one gap, or none.
    """
    date = sealed.get("date") or sealed.get("generated_at", "")[:10]
    repo = sealed.get("repo", "unknown")
    primary = sealed.get("primary_gap")
    recorded = sealed.get("fenceposts_recorded_total", 0)
    wall = max(recorded - 1, 0)

    lines = [
        f"# Fencepost Report — {date}",
        "",
        f"*The one thing that fell between `{repo}`'s accounts yesterday.*",
        "",
    ]

    if primary:
        lines.append(f"**{primary['headline']}** — confidence {primary['confidence']}.")
        lines.append("")
        detail = (primary.get("detail") or "").strip()
        if detail:
            lines.append(detail)
            lines.append("")
        evidence = _fmt_evidence(primary.get("evidence", []))
        if evidence:
            lines.append(evidence)
            lines.append("")
    else:
        lines.append("**Nothing cleared the bar today.** The seam held — recorded plainly, not padded.")
        lines.append("")

    plural = "" if recorded == 1 else "s"
    lines.append(f"**The count.** {recorded} fencepost{plural} named to date. The wall reads {wall}.")
    lines.append("")
    lines.append(THE_LINE)
    lines.append("")
    lines.append("Recorded. — Nisaba")
    lines.append("")
    return "\n".join(lines)


def render_latest(base: Path | None = None) -> str:
    """Render the Report for the most recent entry in the Gap Ledger."""
    records = ledger.read_records(base)
    if not records:
        raise ValueError("the ledger is empty — nothing to report yet")
    return render_report(records[-1]["sealed"])


# --- CLI ----------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)

    ledger_base: Path | None = None
    if "--ledger-base" in argv:
        i = argv.index("--ledger-base")
        ledger_base = Path(argv[i + 1])
        del argv[i : i + 2]

    write = "--write" in argv
    if write:
        argv.remove("--write")

    out_base: Path | None = None
    if "--out-base" in argv:
        i = argv.index("--out-base")
        out_base = Path(argv[i + 1])
        del argv[i : i + 2]

    if argv and argv[0] != "-":
        sealed = json.loads(Path(argv[0]).read_text())
        report = render_report(sealed)
        date = sealed.get("date") or sealed.get("generated_at", "")[:10]
    elif argv == ["-"]:
        sealed = json.load(sys.stdin)
        report = render_report(sealed)
        date = sealed.get("date") or sealed.get("generated_at", "")[:10]
    else:
        records = ledger.read_records(ledger_base)
        if not records:
            print("the ledger is empty — nothing to report yet")
            return 1
        sealed = records[-1]["sealed"]
        report = render_report(sealed)
        date = sealed.get("date") or sealed.get("generated_at", "")[:10]

    print(report)

    if write:
        d = reports_dir(out_base)
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{date}.md"
        path.write_text(report, encoding="utf-8")
        print(f"\nWritten: {path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
