#!/usr/bin/env python3
"""Kwaku-Ananse's own remit (fencepost/README.md's "The serial" section,
STRATEGY.md's "Serialized Narrative & @oritatown" team line): the daily
Fencepost Report has never had a page of its own to be shared as.

`docs/fencepost/index.html` renders the *latest* report inline, client-side,
after the page has already loaded -- but the page's own <meta> tags are
static and generic ("Fencepost -- the seam, read only") no matter which day
it is or what the day's gap actually was. A bot fetching a shared link for
a preview card (X, Slack, iMessage, every other unfurler) reads only the
static <meta> before any script runs, so every share of the index page has
always rendered the same generic preview -- never today's actual headline,
never the wall count, never the one line built to be quoted ("You were so
close. You are always so close."). STRATEGY.md's own lagging metric,
"Shared Fencepost Reports in the wild," has sat at 0 since founding
(`tools/shared_reports_check.py`); a share-unfriendly card is one honest,
fixable part of why a screenshot has an easier time traveling than a link
ever has.

This is the same shape TOWN-OPERATIONS.md's "card trick" already solved
for images (`tools/card.py`): a real page can carry per-item <meta> where
the index page cannot, because the index page has to stay generic across
every future day. Here there is no image to point `twitter:image` at (a
Report is text, sealed once, immutable -- inventing an image for it would
be exactly the kind of decoration this town's own doctrine is suspicious
of), so this builds a `summary` card, not `summary_large_image`: title and
description carry the day's real headline and count, pulled from the
already-sealed report text itself, never re-derived or guessed. `THE_LINE`
is imported from `seam_engine.report` rather than retyped -- the same
"read the live source, never duplicate it by hand" discipline
`docs/fencepost/index.html`'s own report-rendering script already holds
for the teaser line.

Usage:
    python3 tools/report_card.py <YYYY-MM-DD>
    python3 tools/report_card.py latest

Prints the URL to share. Writes `docs/fencepost/reports/<date>.html`.
"""
from __future__ import annotations

import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://thierrypdamiba.github.io/orita"

_SEAM_ENGINE_SRC = os.path.join(ROOT, "fencepost", "seam_engine", "src")
if _SEAM_ENGINE_SRC not in sys.path:
    sys.path.insert(0, _SEAM_ENGINE_SRC)

from seam_engine.report import THE_LINE  # noqa: E402

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Every bold ("**...**") segment that opens a line, whatever follows it on
# that same line -- report.py's three shapes for the day's finding differ
# here: the primary-gap case is bold text alone, immediately followed by
# " -- confidence N." and nothing else; the "nothing cleared the bar" and
# "none elected" cases are bold text followed by their OWN trailing prose
# on the same line ("The seam held...", "A candidate cleared..."). All
# three still open with a bold segment, so this matches the segment itself
# and lets the caller pick the first one that isn't a known field label.
_BOLD_LINE_RE = re.compile(r"^\*\*(?P<text>[^*]+)\*\*", re.MULTILINE)
_COUNT_RE = re.compile(r"^\*\*The count\.\*\*\s*(?P<text>.+)$", re.MULTILINE)
# The other bold-opened field labels report.py always renders, in this
# order, after the day's finding -- the first bold line that is NOT one of
# these is the finding itself, whichever of the three shapes it took.
_KNOWN_FIELD_LABELS = {"The count.", "Your move.", "Connect your own."}


class ReportCardValidationError(ValueError):
    """Raised when a report card cannot lawfully be built. Same discipline
    `tools/card.py`'s `CardValidationError` holds for the image card trick:
    refuse loudly before a single byte is written, rather than render a
    page missing the one thing that makes it worth sharing."""


def _extract(pattern: re.Pattern[str], text: str, what: str) -> str:
    m = pattern.search(text)
    if not m:
        raise ReportCardValidationError(
            f"report text carries no recognizable {what} -- refusing to build "
            f"a card from a report whose own shape this parser doesn't "
            f"recognize, rather than guess"
        )
    return m.group("text").strip()


def _extract_headline(text: str) -> str:
    """The day's finding: the first bold-opened line whose bold text isn't
    one of report.py's other known field labels (The count./Your move./
    Connect your own.) -- covers all three shapes render_report ever emits
    (a named gap, "nothing cleared the bar", "none elected today") without
    hardcoding any of their exact prose."""
    for m in _BOLD_LINE_RE.finditer(text):
        candidate = m.group("text").strip()
        if candidate not in _KNOWN_FIELD_LABELS:
            return candidate
    raise ReportCardValidationError(
        "report text carries no recognizable headline line -- refusing to "
        "build a card from a report whose own shape this parser doesn't "
        "recognize, rather than guess"
    )


def build_report_card(date: str, report_text: str) -> tuple[str, str]:
    """Build a report card page's HTML and its public URL. Pure -- no file
    I/O, so it can be tested without ever touching disk. Raises
    `ReportCardValidationError` if `date` is blank/malformed, `report_text`
    is blank, or the report text doesn't carry a recognizable headline/count
    line (the two facts the card actually shows)."""
    if not isinstance(date, str) or not _DATE_RE.match(date.strip()):
        raise ReportCardValidationError(
            f"report card requires a real YYYY-MM-DD date, got {date!r}"
        )
    if not isinstance(report_text, str) or not report_text.strip():
        raise ReportCardValidationError("report card requires non-blank report_text")

    headline = _extract_headline(report_text)
    count_sentence = _extract(_COUNT_RE, report_text, "'**The count.**' line")

    page_url = f"{BASE}/fencepost/reports/{date}.html"
    report_url = f"https://github.com/thierrypdamiba/orita/blob/main/fencepost/REPORTS/{date}.md"
    title = f"Fencepost — {date}: {headline}"
    description = f"{count_sentence} {THE_LINE}"
    t, d = (html.escape(x) for x in (title, description))
    h, c = (html.escape(x) for x in (headline, count_sentence))

    page = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{d}">
<meta property="og:type" content="article">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{page_url}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
<link rel="stylesheet" href="../../style.css">
<div class="wrap">
  <a class="crumb" href="../index.html">← Fencepost</a>
  <article class="shrine">
    <h1>{h}</h1>
    <p class="epithet">{c}</p>
    <p>{html.escape(THE_LINE)}</p>
    <p><a href="{report_url}">Read the full sealed report</a> ·
       <a href="../connect.html">Connect your own</a></p>
  </article>
  <footer><p><a href="../../index.html">Orita</a> · <a href="../index.html">Fencepost</a></p></footer>
</div>
"""
    return page, page_url


def _latest_date(reports_dir: str) -> str:
    dates = sorted(
        f[:-3] for f in os.listdir(reports_dir) if _DATE_RE.match(f[:-3]) and f.endswith(".md")
    )
    if not dates:
        raise ReportCardValidationError(f"no sealed reports found in {reports_dir}")
    return dates[-1]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 1
    reports_dir = os.path.join(ROOT, "fencepost", "REPORTS")
    date = _latest_date(reports_dir) if argv[0] == "latest" else argv[0]
    report_path = os.path.join(reports_dir, f"{date}.md")
    try:
        with open(report_path, encoding="utf-8") as f:
            report_text = f.read()
    except OSError as exc:
        print(f"report_card: cannot read {report_path}: {exc}", file=sys.stderr)
        return 1
    try:
        page, page_url = build_report_card(date, report_text)
    except ReportCardValidationError as exc:
        print(f"report_card: refused -- {exc}", file=sys.stderr)
        return 1
    out_dir = os.path.join(ROOT, "docs", "fencepost", "reports")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{date}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)
    print(page_url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
