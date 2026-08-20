"""The self-audit — Ogun's law, run against the town's own ledger.

STRATEGY.md names the residual risk in plain words: "false-positive gaps
('crying wolf') erode the read-trust the whole product rests on." The
mitigation named beside it is this module: "publish an honest daily
true-positive tally, and label confidence on every surfaced gap rather than
over-claiming."

A "surfaced gap" is the one thing a reader ever sees: the `primary_gap` a
Ledger entry sealed and a Report dispatched (report.py never shows the
coincidence tail — "naming six things that were *not* the gap is honest
bookkeeping in a tablet and noise in a dispatch"). So the self-audit grades
exactly that: one verdict per Ledger entry that named a gap.

No human grader, no live network call, no re-fetch of GitHub or X — this is a
*self*-audit: the engine checks a sealed claim against the law and evidence it
already recorded under its own seal. That is deliberately narrower than "did
this turn out to be true in the world," and it is honest about that limit; it
still catches the exact failure Ogun's law exists to prevent — a candidate
that reached the front page of the ledger without actually clearing the bar it
claims to have cleared, or with evidence too thin to check. A future scan
extending this to real-world confirmation (did the human's own account close
the gap?) is v0.2 work; this ships the tally, not the promise of one.

Two verdicts only, per the task: CONFIRMED or FALSE. Nothing is graded,
named, or ranked beyond that — this audits the CLAIM, never a person. Pure and
deterministic: `audit_ledger` is a function of what the ledger already sealed.
Its only I/O is reading the ledger and, on request, writing the rendered
tally — a rendering of what the ledger already sealed, never a second source
of truth (report.py's own rule, kept here too).

Sworn on iron.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from seam_engine import ledger, margin_law

# fencepost/  (…/fencepost/seam_engine/src/seam_engine/audit.py → parents[3])
_FENCEPOST_ROOT = Path(__file__).resolve().parents[3]

# The only hosts Fencepost's read-only oath (SCOPES.md) ever reads from.
# Evidence pointing anywhere else did not come from a scope Fencepost holds —
# that alone is grounds to fail the audit, whatever the confidence claims.
_ALLOWED_EVIDENCE_HOSTS = {"github.com", "x.com", "twitter.com"}


class Verdict(str, Enum):
    """What the audit asserts about one surfaced gap. Two only — no PENDING,
    no partial credit. A claim either holds up against its own recorded law
    and evidence, or it does not."""

    CONFIRMED = "confirmed"
    FALSE = "false"


@dataclass
class AuditedGap:
    tablet: str
    seq: int
    date: str
    slug: str
    headline: str
    confidence: float
    verdict: str
    checks: list[tuple[str, bool]]

    @property
    def reason(self) -> str:
        return "; ".join(f"{'OK' if ok else 'FAIL'} {label}" for label, ok in self.checks)


@dataclass
class Tally:
    gaps: list[AuditedGap]

    @property
    def confirmed(self) -> int:
        return sum(1 for g in self.gaps if g.verdict == Verdict.CONFIRMED.value)

    @property
    def false(self) -> int:
        return sum(1 for g in self.gaps if g.verdict == Verdict.FALSE.value)

    @property
    def total(self) -> int:
        return len(self.gaps)

    @property
    def rate(self) -> float | None:
        """True-positive rate, confirmed/total. None when nothing has been
        audited yet — a rate over zero claims is not a number, it is a guess,
        and Ogun's law does not guess."""
        return self.confirmed / self.total if self.total else None


def _well_formed(url: str) -> bool:
    """Does `url` resolve to a host Fencepost's read-only oath actually
    covers? Checked on `hostname`, never `netloc` -- `netloc` carries the
    port and any userinfo prefix (`user@`) along with the host, so a
    genuinely github.com URL that happens to name an explicit port
    (`https://github.com:443/...`) or credential syntax
    (`https://user@github.com/...`) would fail an exact-`netloc` compare
    even though it connects to exactly the allowed host. `hostname` already
    strips both and lowercases, and — unlike a naive split on the first
    `@` — always resolves to the REAL connecting host per the URL spec: for
    `https://github.com@evil.com/...` (github.com as bogus userinfo, the
    actual host after the last `@`), `hostname` correctly reads `evil.com`,
    so this is strictly a false-negative fix, not a new door for a
    confusable host to walk through."""
    try:
        u = urlparse(url)
    except ValueError:
        return False
    return u.scheme in ("http", "https") and (u.hostname or "").lower() in _ALLOWED_EVIDENCE_HOSTS


def _audit_primary(tablet: str, seq: int, date: str, sealed: dict[str, Any]) -> AuditedGap | None:
    """Grade one Ledger entry's primary_gap against the law and evidence it
    was sealed with. Returns None when the entry named no gap — a quiet seam
    is not a claim, so there is nothing here to audit.
    """
    primary = sealed.get("primary_gap")
    if not primary:
        return None

    confidence = primary.get("confidence", 0.0)
    bar = sealed.get("confidence_bar")
    margin = sealed.get("separation_margin")
    evidence = primary.get("evidence", [])
    tail_confidences = [t.get("confidence", 0.0) for t in sealed.get("tail", [])]
    runner_up = max(tail_confidences, default=0.0)

    checks: list[tuple[str, bool]] = [
        (
            "clears its own recorded confidence bar",
            bar is not None and confidence >= bar,
        ),
        (
            "leads the recorded field by its own recorded margin",
            # Task 902: this used to re-derive the margin decision itself
            # via `round(confidence - runner_up, 4) >= margin` -- a second,
            # independent copy of the exact election law `ranking.rank`
            # already computes at seal time, and a STALE copy: task 895
            # proved that a display-rounded (4-place) boundary decision is
            # off-by-one's own class of miscount (a true lead of 0.14996
            # rounds UP to 0.1500 and would wrongly clear a 0.15 margin --
            # crying wolf, the fatal direction Ogun's law forbids) and fixed
            # it in what is now `margin_law.clears_margin` (10-place
            # rounding: enough to erase IEEE-754 dust, far too fine to
            # round across a real boundary). This audit module
            # re-implemented the pre-fix 4-place shape independently and
            # never inherited the correction -- the self-audit that exists
            # to catch a false PRIMARY could itself rubber-stamp CONFIRMED
            # one, using exactly the bug its own sibling module already
            # closed. Now calls the one corrected law (via `margin_law`,
            # not `ranking` directly -- `ranking.py` imports `scan.py`,
            # which imports `httpx`; `margin_law.py` carries none of that,
            # so this module's plain-python3 callers, `tools/
            # ritual_check.py` included, don't inherit a dependency they
            # don't need to check one float comparison). Cannot fire on
            # today's 2-dp confidences (verified, same as task 895's own
            # note) -- shuts the door before a finer-grained future source
            # opens it.
            margin is not None and margin_law.clears_margin(confidence - runner_up, margin),
        ),
        (
            "carries at least one evidence link",
            len(evidence) > 0,
        ),
        (
            "every evidence link resolves to a scope Fencepost actually holds",
            len(evidence) > 0 and all(_well_formed(u) for u in evidence),
        ),
    ]
    verdict = Verdict.CONFIRMED if all(ok for _, ok in checks) else Verdict.FALSE

    return AuditedGap(
        tablet=tablet,
        seq=seq,
        date=date,
        slug=primary.get("slug", "unknown"),
        headline=primary.get("headline", ""),
        confidence=confidence,
        verdict=verdict.value,
        checks=checks,
    )


def audit_ledger(base: Path | None = None) -> Tally:
    """Audit every gap the whole Ledger has ever surfaced, in chain order."""
    gaps: list[AuditedGap] = []
    for rec in ledger.read_records(base):
        sealed = rec.get("sealed", {})
        g = _audit_primary(
            tablet=rec.get("_tablet", "?"),
            seq=rec.get("seq", 0),
            date=sealed.get("date", ""),
            sealed=sealed,
        )
        if g is not None:
            gaps.append(g)
    return Tally(gaps=gaps)


# --- rendering ----------------------------------------------------------------


def render_tally_markdown(t: Tally) -> str:
    """Render the public true-positive tally. Regenerated in full each run —
    a rendering of what the Ledger already sealed, never a second source of
    truth, and never hand-edited."""
    lines = [
        "# Self-Audit — the true-positive tally",
        "",
        "*False positives are the whole ballgame. Every gap this town has ever "
        "put its name to is graded here against the law and evidence it was "
        "sealed with — the bar it had to clear, the margin it had to lead by, "
        "the evidence it had to show. A ledger that flatters is a ledger that "
        "lies.*",
        "",
    ]

    if t.total == 0:
        lines.append("**No gap has been surfaced yet.** Nothing to audit. Nothing claimed.")
        lines.append("")
    else:
        rate_pct = round((t.rate or 0.0) * 100)
        lines.append(
            f"**Tally: {t.confirmed} confirmed, {t.false} false, {t.total} audited. "
            f"True-positive rate: {rate_pct}%.**"
        )
        lines.append("")
        lines.append("| date | entry | gap | confidence | verdict | reason |")
        lines.append("|--|--|--|--|--|--|")
        for g in t.gaps:
            verdict_word = "CONFIRMED" if g.verdict == Verdict.CONFIRMED.value else "FALSE"
            lines.append(
                f"| {g.date} | `{g.tablet}#entry-{g.seq}` | {g.headline} "
                f"| {g.confidence} | {verdict_word} | {g.reason} |"
            )
        lines.append("")

    lines.append("Audited on iron, against nothing but what was already sealed. — Ogun")
    lines.append("")
    return "\n".join(lines)


def audit_path(base: Path | None = None) -> Path:
    """Where the rendered tally lives. Defaults to fencepost/AUDIT.md."""
    return (base if base is not None else _FENCEPOST_ROOT) / "AUDIT.md"


# --- CLI ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)

    ledger_base: Path | None = None
    if "--base" in argv:
        i = argv.index("--base")
        if i + 1 >= len(argv):
            print("--base needs a path to a Ledger directory.")
            return 2
        ledger_base = Path(argv[i + 1])
        del argv[i : i + 2]

    write = "--write" in argv
    if write:
        argv.remove("--write")

    out_base: Path | None = None
    if "--out-base" in argv:
        i = argv.index("--out-base")
        if i + 1 >= len(argv):
            print("--out-base needs a path to write the tally under.")
            return 2
        out_base = Path(argv[i + 1])
        del argv[i : i + 2]

    t = audit_ledger(ledger_base)
    rendered = render_tally_markdown(t)
    print(rendered)

    if write:
        path = audit_path(out_base)
        path.write_text(rendered, encoding="utf-8")
        print(f"\nWritten: {path}", file=sys.stderr)

    return 0 if t.false == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
