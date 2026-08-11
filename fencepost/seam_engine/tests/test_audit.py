"""Tests for the self-audit — Ogun's law, run against the town's own ledger.

Every claim this module makes about a gap has a test that goes red if the
claim stops being checked: a gap that didn't clear its own recorded bar, a
gap that didn't lead by its own recorded margin, a gap with no evidence, and
a gap with evidence outside the read-only oath's own scopes all have to come
back FALSE, or the audit is a rubber stamp and Ogun's law is dead letter.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from seam_engine import audit, ledger


def _scan(
    *,
    primary: bool = True,
    confidence: float = 0.85,
    bar: float = 0.70,
    margin: float = 0.15,
    evidence: list[str] | None = None,
    tail_confidence: float = 0.55,
    generated_at: str = "t",
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
        "generated_at": generated_at,
        "repo": "x/orita",
        "window_hours": 24,
        "confidence_bar": bar,
        "separation_margin": margin,
        "primary_gap": p,
        "tail": [{"slug": "coincidence-a", "confidence": tail_confidence, "label": "coincidence"}],
        "excluded": [],
    }


def _at(y: int, m: int, d: int, h: int = 12) -> datetime:
    return datetime(y, m, d, h, tzinfo=timezone.utc)


# --- a sound claim is confirmed ------------------------------------------------


def test_a_gap_that_clears_its_own_law_is_confirmed(tmp_path: Path):
    ledger.append_scan(_scan(), now=_at(2026, 7, 12), base=tmp_path)
    t = audit.audit_ledger(tmp_path)

    assert t.total == 1
    assert t.confirmed == 1
    assert t.false == 0
    assert t.gaps[0].verdict == audit.Verdict.CONFIRMED.value
    assert t.rate == 1.0


def test_a_quiet_day_audits_nothing(tmp_path: Path):
    ledger.append_scan(_scan(primary=False), now=_at(2026, 7, 12), base=tmp_path)
    t = audit.audit_ledger(tmp_path)

    assert t.total == 0
    assert t.rate is None  # no claims made, no rate to report


# --- each way a claim can go false ---------------------------------------------


def test_confidence_below_its_own_recorded_bar_is_false(tmp_path: Path):
    # A forged/regressed record: it shipped as primary but does not actually
    # clear the bar recorded alongside it.
    ledger.append_scan(_scan(confidence=0.60, bar=0.70), now=_at(2026, 7, 12), base=tmp_path)
    t = audit.audit_ledger(tmp_path)

    assert t.gaps[0].verdict == audit.Verdict.FALSE.value
    assert "clears its own recorded confidence bar" in t.gaps[0].reason
    assert "FAIL clears its own recorded confidence bar" in t.gaps[0].reason


def test_thin_lead_over_the_tail_is_false(tmp_path: Path):
    # Confidence clears the bar, but the lead over the runner-up falls short
    # of the margin the record itself claims to have needed.
    ledger.append_scan(
        _scan(confidence=0.75, bar=0.70, margin=0.15, tail_confidence=0.70),
        now=_at(2026, 7, 12), base=tmp_path,
    )
    t = audit.audit_ledger(tmp_path)

    assert t.gaps[0].verdict == audit.Verdict.FALSE.value
    assert "FAIL leads the recorded field by its own recorded margin" in t.gaps[0].reason


def test_no_evidence_is_false(tmp_path: Path):
    ledger.append_scan(_scan(evidence=[]), now=_at(2026, 7, 12), base=tmp_path)
    t = audit.audit_ledger(tmp_path)

    assert t.gaps[0].verdict == audit.Verdict.FALSE.value
    assert "FAIL carries at least one evidence link" in t.gaps[0].reason


def test_evidence_outside_the_read_only_oath_is_false(tmp_path: Path):
    # A URL that doesn't point at a scope Fencepost's SCOPES.md actually holds
    # (github.com / x.com / twitter.com) cannot back a claim.
    ledger.append_scan(
        _scan(evidence=["https://example.com/not-a-real-scope"]),
        now=_at(2026, 7, 12), base=tmp_path,
    )
    t = audit.audit_ledger(tmp_path)

    assert t.gaps[0].verdict == audit.Verdict.FALSE.value
    assert "FAIL every evidence link resolves to a scope Fencepost actually holds" in t.gaps[0].reason


# --- _well_formed: the host check itself, not just its FALSE-verdict effect ---
#
# `netloc` (the pre-fix comparison target) carries the port and any userinfo
# prefix along with the host; `hostname` (the fix) strips both and lowercases.
# A genuinely github.com-hosted evidence URL that happens to carry either
# must not be punished for it -- Ogun's law is about the REAL host a URL
# resolves to, not the exact string shape GitHub's API happened to emit.


def test_well_formed_accepts_an_explicit_default_port():
    # https://github.com:443/... is exactly github.com -- the port is the
    # scheme's own default, not a different host.
    assert audit._well_formed("https://github.com:443/x/orita/commit/0000000") is True


def test_well_formed_accepts_a_userinfo_prefix():
    # https://user@github.com/... connects to github.com; `user@` is
    # credential syntax the URL spec carries separately from the host.
    assert audit._well_formed("https://user@github.com/x/orita/commit/0000000") is True


def test_well_formed_still_rejects_a_host_confusable_url():
    # https://github.com@evil.com/... is a classic confusable: everything
    # before the LAST @ is userinfo, and the real host is evil.com. Fixing
    # the false negative above must not open this door.
    assert audit._well_formed("https://github.com@evil.com/x/orita/commit/0000000") is False


def test_well_formed_still_rejects_an_unrelated_host():
    assert audit._well_formed("https://example.com/not-a-real-scope") is False


def test_evidence_with_an_explicit_port_is_confirmed_not_false(tmp_path: Path):
    # The end-to-end regression: a sound gap whose evidence happens to carry
    # an explicit default port must be CONFIRMED, not wrongly graded FALSE.
    ledger.append_scan(
        _scan(evidence=["https://github.com:443/x/orita/commit/0000000"]),
        now=_at(2026, 7, 12), base=tmp_path,
    )
    t = audit.audit_ledger(tmp_path)

    assert t.gaps[0].verdict == audit.Verdict.CONFIRMED.value
    assert "OK every evidence link resolves to a scope Fencepost actually holds" in t.gaps[0].reason


# --- the tally is honest, not a percentage that hides the count ---------------


def test_tally_counts_across_multiple_entries(tmp_path: Path):
    ledger.append_scan(_scan(confidence=0.85), now=_at(2026, 7, 12), base=tmp_path)          # confirmed
    ledger.append_scan(_scan(primary=False), now=_at(2026, 7, 13), base=tmp_path)            # nothing to audit
    ledger.append_scan(_scan(confidence=0.60, bar=0.70), now=_at(2026, 7, 14), base=tmp_path)  # false

    t = audit.audit_ledger(tmp_path)
    assert t.total == 2
    assert t.confirmed == 1
    assert t.false == 1
    assert t.rate == 0.5


# --- rendering: the public tally never claims a rate it can't show ------------


def test_rendered_tally_with_no_claims_says_so_plainly(tmp_path: Path):
    ledger.append_scan(_scan(primary=False), now=_at(2026, 7, 12), base=tmp_path)
    t = audit.audit_ledger(tmp_path)
    rendered = audit.render_tally_markdown(t)

    assert "No gap has been surfaced yet" in rendered
    assert "%" not in rendered  # no claimed rate over zero claims


def test_rendered_tally_shows_the_real_count_and_rate(tmp_path: Path):
    ledger.append_scan(_scan(confidence=0.85), now=_at(2026, 7, 12), base=tmp_path)
    ledger.append_scan(_scan(confidence=0.60, bar=0.70), now=_at(2026, 7, 13), base=tmp_path)
    t = audit.audit_ledger(tmp_path)
    rendered = audit.render_tally_markdown(t)

    assert "1 confirmed, 1 false, 2 audited" in rendered
    assert "True-positive rate: 50%" in rendered
    assert "CONFIRMED" in rendered
    assert "FALSE" in rendered


def test_render_never_names_or_ranks_a_person():
    # Ogun's own oath: grade/name/rank NO ONE. The audit grades a claim, not
    # a god — no author/owner field ever enters the rendered tally.
    t = audit.Tally(gaps=[
        audit.AuditedGap(
            tablet="2026-07-12.md", seq=0, date="2026-07-12", slug="x",
            headline="h", confidence=0.9,
            verdict=audit.Verdict.CONFIRMED.value,
            checks=[("clears its own recorded confidence bar", True)],
        )
    ])
    rendered = audit.render_tally_markdown(t)
    for banned in ("author", "owner", "blame", "grade:"):
        assert banned not in rendered.lower()


# --- CLI: writes the rendering, never a second source of truth ----------------


def test_main_writes_the_tally_file(tmp_path: Path, capsys):
    ledger.append_scan(_scan(confidence=0.85), now=_at(2026, 7, 12), base=tmp_path)
    rc = audit.main(["--base", str(tmp_path), "--write", "--out-base", str(tmp_path)])

    assert rc == 0
    out = audit.audit_path(tmp_path)
    assert out.exists()
    assert "1 confirmed, 0 false, 1 audited" in out.read_text()


def test_main_exits_nonzero_when_a_false_positive_is_in_the_ledger(tmp_path: Path):
    ledger.append_scan(_scan(confidence=0.60, bar=0.70), now=_at(2026, 7, 12), base=tmp_path)
    rc = audit.main(["--base", str(tmp_path)])
    assert rc == 1


def test_main_rejects_trailing_base_flag_with_no_value(capsys):
    rc = audit.main(["--base"])
    assert rc == 2
    assert "--base needs a path" in capsys.readouterr().out


def test_main_rejects_trailing_out_base_flag_with_no_value(capsys):
    rc = audit.main(["--out-base"])
    assert rc == 2
    assert "--out-base needs a path" in capsys.readouterr().out
