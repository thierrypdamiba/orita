"""Tests for docs/fencepost/index.html's audit-tally re-parse of AUDIT.md
(ROADMAP.md #138).

`seam_engine.audit.render_tally_markdown` is the ONE place the self-audit
tally is ever rendered ("a rendering of what the Ledger already sealed,
never a second source of truth" -- the module's own docstring). The live
site never calls that function: it fetches raw `AUDIT.md` text over HTTP
and re-parses it itself, in JavaScript, with a hand-written regex for the
"Tally: N confirmed, N false, N audited. True-positive rate: N%" line and a
hand-written markdown-table-row splitter for the per-gap rows underneath
it. Neither had ever been checked, by any test anywhere, against the real
generator whose output they assume.

The regex/threshold/indices below are pulled out of `index.html`'s live
source text with `re.search` -- never retyped from memory -- so a change to
the page's own extraction logic travels into these tests automatically
instead of leaving them to quietly test a stale copy. Same discipline
`test_wall.py`'s teaser-extraction test already holds for the block one
step up in the same script.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from seam_engine import audit, ledger, report
from seam_engine.wall import wall_for

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = FENCEPOST_ROOT.parent / "docs" / "fencepost" / "index.html"


def _index_html() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")


def _extract_tally_regex() -> re.Pattern[str]:
    """Pull the JS Tally-line regex literal straight out of index.html's
    live source and compile it with Python's `re`, same /i flag."""
    m = re.search(r"text\.match\(/(Tally:.*?)/i\)", _index_html())
    assert m is not None, (
        "index.html no longer carries a `text.match(/Tally:.../i)` "
        "extraction where this test expects it"
    )
    return re.compile(m.group(1), re.IGNORECASE)


def _extract_wall_regex_source() -> str:
    m = re.search(r"text\.match\(/(wall reads.*?)/i\)", _index_html())
    assert m is not None
    return m.group(1)


def _extract_row_parse_params() -> tuple[int, tuple[int, int, int, int]]:
    """Pull the row-guard threshold and the four `parts[]` column indices
    (date, gap, confidence, verdict) straight out of index.html's live
    source."""
    html = _index_html()

    guard = re.search(r"parts\.length < (\d+)", html)
    assert guard is not None, "index.html no longer guards row length where this test expects it"
    threshold = int(guard.group(1))

    assign = re.search(
        r"var date = esc\(parts\[(\d+)\]\), gap = esc\(parts\[(\d+)\]\), "
        r"confidence = esc\(parts\[(\d+)\]\), verdict = esc\(parts\[(\d+)\]\);",
        html,
    )
    assert assign is not None, "index.html no longer assigns date/gap/confidence/verdict where this test expects it"
    indices = tuple(int(g) for g in assign.groups())
    assert len(indices) == 4
    return threshold, indices


def _esc(s: str) -> str:
    """Mirrors index.html's own `esc()` exactly -- &/</> only."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _parse_rows_like_the_site(
    text: str, threshold: int, indices: tuple[int, int, int, int]
) -> list[dict[str, str]]:
    """Reimplements index.html's row filter/split/guard exactly (line
    starts with '|', not a header, not the separator; split on '|', trim
    each cell; drop anything shorter than the page's own threshold),
    parameterized by values extracted live from the page itself."""
    date_i, gap_i, confidence_i, verdict_i = indices
    rows = [
        line
        for line in text.split("\n")
        if line.startswith("|") and "date" not in line and "--|--" not in line
    ]
    out = []
    for row in rows:
        parts = [c.strip() for c in row.split("|")]
        if len(parts) < threshold:
            continue
        out.append(
            {
                "date": _esc(parts[date_i]),
                "gap": _esc(parts[gap_i]),
                "confidence": _esc(parts[confidence_i]),
                "verdict": _esc(parts[verdict_i]),
            }
        )
    return out


def _at(y: int, m: int, d: int, h: int = 12) -> datetime:
    return datetime(y, m, d, h, tzinfo=timezone.utc)


def _scan(
    *,
    primary: bool = True,
    confidence: float = 0.85,
    bar: float = 0.70,
    margin: float = 0.15,
    evidence: list[str] | None = None,
    tail_confidence: float = 0.55,
) -> dict:
    if evidence is None:
        evidence = ["https://github.com/x/orita/commit/0000000"]
    p = None
    if primary:
        p = {
            "slug": "milestone-unannounced",
            "headline": "Milestone-level work shipped but never reached the sky",
            "detail": "3 milestone commit(s), none echoed in a post.",
            "confidence": confidence,
            "evidence": evidence,
            "label": "primary",
        }
    return {
        "generated_at": "t",
        "repo": "x/orita",
        "window_hours": 24,
        "confidence_bar": bar,
        "separation_margin": margin,
        "primary_gap": p,
        "tail": [{"slug": "coincidence-a", "confidence": tail_confidence, "label": "coincidence"}],
        "excluded": [],
    }


# --- the regex is real, and distinct from its neighbors ----------------------


def test_tally_regex_extracted_from_the_page_is_nonempty():
    pattern = _extract_tally_regex()
    assert pattern.pattern, "extracted Tally regex is empty"


def test_tally_regex_is_structurally_distinct_from_the_wall_count_regex():
    tally_source = _extract_tally_regex().pattern
    wall_source = _extract_wall_regex_source()
    assert tally_source != wall_source


# --- the wall-count regex, task 138 built the extractor for and never used ---
# `_extract_wall_regex_source()` above was, until now, called exactly once --
# only to prove it differs from the Tally regex, never to prove it actually
# matches the real generator it parses. The teaser (task 126) and the Tally
# block (task 138) both carry that proof; this block, one line up in the
# same <script>, never did.


def _sealed(recorded: int) -> dict:
    return {
        "date": "2026-07-12",
        "generated_at": "2026-07-12T00:00:00+00:00",
        "repo": "x/orita",
        "primary_gap": None,
        "tail": [],
        "fenceposts_recorded_total": recorded,
    }


def test_wall_count_regex_matches_real_report_output_with_correct_group():
    wall_pattern = re.compile(_extract_wall_regex_source(), re.IGNORECASE)
    for recorded in (0, 1, 7):
        text = report.render_report(_sealed(recorded))
        match = wall_pattern.search(text)
        assert match is not None, (
            f"the page's own wall-count regex failed to match render_report's "
            f"real output for fenceposts_recorded_total={recorded}"
        )
        assert int(match.group(1)) == wall_for(recorded)


def test_wall_count_regex_stops_matching_a_reworded_copy_of_the_real_line():
    wall_pattern = re.compile(_extract_wall_regex_source(), re.IGNORECASE)
    text = report.render_report(_sealed(3))
    assert wall_pattern.search(text) is not None, "sanity: the real line must match before mutating it"
    mutated = text.replace("The wall reads", "The wall shows")
    assert "The wall reads" not in mutated
    assert wall_pattern.search(mutated) is None, (
        "the extracted wall-count regex still matched a deliberately reworded "
        "copy of the real line -- it isn't actually anchored to the wording "
        "index.html depends on"
    )


# --- the regex matches the REAL generator's output, groups included ----------


def test_tally_regex_matches_real_ledger_output_with_correct_groups(tmp_path: Path):
    ledger.append_scan(_scan(confidence=0.85), now=_at(2026, 7, 12), base=tmp_path)  # confirmed
    ledger.append_scan(_scan(confidence=0.60, bar=0.70), now=_at(2026, 7, 13), base=tmp_path)  # false
    ledger.append_scan(_scan(primary=False), now=_at(2026, 7, 14), base=tmp_path)  # nothing to audit

    t = audit.audit_ledger(tmp_path)
    rendered = audit.render_tally_markdown(t)

    pattern = _extract_tally_regex()
    match = pattern.search(rendered)
    assert match is not None, "the page's own regex failed to match render_tally_markdown's real output"
    assert int(match.group(1)) == t.confirmed
    assert int(match.group(2)) == t.false
    assert int(match.group(3)) == round((t.rate or 0.0) * 100)


def test_tally_regex_matches_the_towns_real_live_audit_ledger():
    # Not a fixture: the actual fencepost/GAPS ledger this hour, rendered
    # through the actual generator, read by the actual extracted regex.
    t = audit.audit_ledger()
    rendered = audit.render_tally_markdown(t)
    if t.total == 0:
        return  # nothing sealed yet in this checkout -- covered separately below
    pattern = _extract_tally_regex()
    match = pattern.search(rendered)
    assert match is not None
    assert int(match.group(1)) == t.confirmed
    assert int(match.group(2)) == t.false
    assert int(match.group(3)) == round((t.rate or 0.0) * 100)


# --- the zero-gap render does NOT match -- the page's own `else` fires -------


def test_zero_gap_render_does_not_match_the_tally_regex(tmp_path: Path):
    ledger.append_scan(_scan(primary=False), now=_at(2026, 7, 12), base=tmp_path)
    t = audit.audit_ledger(tmp_path)
    assert t.total == 0
    rendered = audit.render_tally_markdown(t)

    pattern = _extract_tally_regex()
    assert pattern.search(rendered) is None, (
        "a zero-gap render matched the Tally regex -- the page's own `else` "
        "branch (0/0/-) would never fire, silently showing a stale/wrong match instead"
    )


# --- mutation: the regex actually bites, it doesn't just look plausible ------


def test_tally_regex_stops_matching_a_reworded_copy_of_the_real_line():
    real_line = "**Tally: 3 confirmed, 0 false, 3 audited. True-positive rate: 100%.**"
    mutated_line = "**Tally: 3 confirmed, 0 false, 3 audited. TP rate: 100%.**"

    pattern = _extract_tally_regex()
    assert pattern.search(real_line) is not None
    assert pattern.search(mutated_line) is None, (
        "the extracted regex still matched after 'True-positive rate' was "
        "reworded to 'TP rate' -- it is not actually checking the wording it claims to"
    )


# --- the row parser reproduces the REAL generator's rows, field for field ----


def test_row_parser_reproduces_real_ledger_gaps_exactly(tmp_path: Path):
    ledger.append_scan(_scan(confidence=0.85), now=_at(2026, 7, 12), base=tmp_path)  # confirmed
    ledger.append_scan(_scan(confidence=0.60, bar=0.70), now=_at(2026, 7, 13), base=tmp_path)  # false

    t = audit.audit_ledger(tmp_path)
    rendered = audit.render_tally_markdown(t)

    threshold, indices = _extract_row_parse_params()
    parsed = _parse_rows_like_the_site(rendered, threshold, indices)

    assert len(parsed) == t.total == 2
    for row, gap in zip(parsed, t.gaps):
        expected_verdict = "CONFIRMED" if gap.verdict == audit.Verdict.CONFIRMED.value else "FALSE"
        assert row["date"] == gap.date
        assert row["gap"] == _esc(gap.headline)
        assert row["confidence"] == str(gap.confidence)
        assert row["verdict"] == expected_verdict


def test_row_parser_reproduces_the_towns_real_live_audit_ledger():
    t = audit.audit_ledger()
    if t.total == 0:
        return
    rendered = audit.render_tally_markdown(t)
    threshold, indices = _extract_row_parse_params()
    parsed = _parse_rows_like_the_site(rendered, threshold, indices)

    assert len(parsed) == t.total
    for row, gap in zip(parsed, t.gaps):
        expected_verdict = "CONFIRMED" if gap.verdict == audit.Verdict.CONFIRMED.value else "FALSE"
        assert row["date"] == gap.date
        assert row["gap"] == _esc(gap.headline)
        assert row["verdict"] == expected_verdict


# --- mutation: the row parser's own length guard actually bites --------------


def test_row_parser_drops_a_malformed_row_missing_pipes(tmp_path: Path):
    ledger.append_scan(_scan(confidence=0.85), now=_at(2026, 7, 12), base=tmp_path)
    t = audit.audit_ledger(tmp_path)
    rendered = audit.render_tally_markdown(t)
    threshold, indices = _extract_row_parse_params()

    lines = rendered.split("\n")
    row_line_idx = next(
        i for i, line in enumerate(lines) if line.startswith("|") and "date" not in line and "--|--" not in line
    )
    real_row = lines[row_line_idx]
    real_parts = real_row.split("|")
    assert len(real_parts) >= threshold  # sanity: the real row clears the page's own guard
    assert len(_parse_rows_like_the_site(real_row, threshold, indices)) == 1

    # Drop just enough trailing '|'s (never the leading one, so the row
    # still passes the page's own `startswith('|')` filter) to push the
    # real row's part count strictly below the extracted threshold -- one
    # pipe alone isn't enough, the real row carries one field of slack.
    pipe_positions = [i for i, c in enumerate(real_row) if c == "|"]
    to_drop = len(real_parts) - threshold + 1
    malformed_row = real_row
    for pos in sorted(pipe_positions[-to_drop:], reverse=True):
        malformed_row = malformed_row[:pos] + malformed_row[pos + 1 :]
    assert malformed_row.startswith("|")
    assert len(malformed_row.split("|")) < threshold  # sanity: mutation actually undershoots

    assert len(_parse_rows_like_the_site(malformed_row, threshold, indices)) == 0, (
        "a row with fewer '|'s than the page's own guard requires still "
        "parsed -- the `parts.length < threshold` guard would not have caught it"
    )
