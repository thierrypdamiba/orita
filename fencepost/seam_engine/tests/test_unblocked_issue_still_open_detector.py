"""Tests for RECIPES/unblocked-issue-still-open/detector.py's own detection
logic (ROADMAP.md #593) -- the sixty-first real recipe: an issue that
names itself blocked by another issue, whose named blocker has since
closed, while the blocked issue itself was never revisited.

Loaded the same way `seam_engine.recipes.load_detector` loads any recipe's
detector at runtime (`importlib.util.spec_from_file_location`), so this test
exercises the exact module a live scan would import, not a copy.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

FENCEPOST_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = FENCEPOST_ROOT / "RECIPES" / "unblocked-issue-still-open" / "detector.py"

_spec = importlib.util.spec_from_file_location("seam_engine._recipe_unblocked_issue_still_open_test", DETECTOR_PATH)
detector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = detector
_spec.loader.exec_module(detector)

_NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)


def _issue(
    number: int,
    body: str,
    state: str = "open",
    closed_at: datetime | None = None,
) -> "detector.Issue":
    return detector.Issue(
        number=number, title=f"Issue {number}", state=state, body=body,
        closed_at=closed_at, url=f"https://github.com/example/example-repo/issues/{number}",
    )


class TestNamedBlockerOf:
    def test_blocked_by_hash_n(self):
        assert detector._named_blocker_of("Blocked by #900") == 900

    def test_blocked_on_hash_n(self):
        assert detector._named_blocker_of("blocked on #903") == 903

    def test_blocked_colon_hash_n(self):
        assert detector._named_blocker_of("Blocked: #905") == 905

    def test_bare_blocked_hash_n(self):
        assert detector._named_blocker_of("blocked #905") == 905

    def test_no_marker_returns_none(self):
        assert detector._named_blocker_of("A regular bug report, no blocker mention at all.") is None

    def test_unblocked_does_not_false_positive(self):
        # "unblocked" contains "blocked" as a literal substring but is not
        # the same word -- the leading `\b` must not let this slip through,
        # since there is no word boundary between "un" and "blocked".
        assert detector._named_blocker_of("This issue is now unblocked, see #900 for context") is None

    def test_blocks_forward_direction_does_not_match(self):
        # "blocks #N" (this issue blocks another) is a different claim in
        # the opposite direction -- this recipe only reads a *self*-declared
        # dependency ("I am blocked by/on"), never the inverse.
        assert detector._named_blocker_of("This blocks #900, not the other way around") is None

    def test_a_negated_blocker_marker_is_not_a_claim(self):
        # A body that explicitly denies still being blocked must not be
        # read as naming a live blocker anyway -- the same false-positive
        # shape task 612 fixed for duplicate_markers.py's "duplicate of #N".
        assert detector._named_blocker_of("This is not blocked by #10 anymore, we are good to go.") is None

    def test_no_longer_blocked_is_not_a_claim(self):
        assert detector._named_blocker_of("No longer blocked by #10.") is None

    def test_isnt_blocked_is_not_a_claim(self):
        assert detector._named_blocker_of("This isn't blocked on #12, go ahead.") is None

    def test_negation_does_not_launder_a_later_genuine_marker(self):
        # A denial of one thing must not swallow an unrelated, real marker
        # sitting further along in the same body -- `finditer` keeps
        # walking past a skipped (negated) candidate to the next one.
        assert detector._named_blocker_of("Not a fan of this, blocked by #10 for real.") == 10

    def test_negation_in_a_prior_sentence_does_not_suppress_a_real_marker(self):
        # Task 693 (Retrya): the shared `seam_engine.negation.is_negated`
        # window used to search straight through a sentence boundary -- a
        # negation word in a PRIOR, unrelated sentence silently swallowed a
        # genuine blocker marker in the sentence that followed it.
        # Reproduced live pre-fix: this returned `None`. See
        # `seam_engine.negation`'s own docstring for the fix and the full
        # blast radius.
        assert detector._named_blocker_of("Not fine. blocked by #10 anymore.") == 10


class TestComputeGaps:
    def test_a_stale_closed_blocker_is_surfaced_at_high_confidence(self):
        blocked = _issue(901, "Blocked by #900")
        blocker = _issue(900, "Some bug", state="closed", closed_at=datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([blocker, blocked], now=_NOW)

        assert excluded == []
        assert len(surfaced) == 1
        assert surfaced[0].slug == "unblocked-issue-still-open-901-900"
        assert surfaced[0].confidence == 0.85

    def test_a_recently_closed_blocker_is_surfaced_at_low_confidence(self):
        blocked = _issue(902, "Blocked on #903")
        blocker = _issue(903, "Some bug", state="closed", closed_at=_NOW - timedelta(hours=6))

        surfaced, excluded = detector.compute_gaps([blocker, blocked], now=_NOW)

        assert len(surfaced) == 1
        assert surfaced[0].confidence == 0.5

    def test_a_still_open_named_blocker_is_excluded_not_surfaced(self):
        blocked = _issue(904, "Blocked by #905")
        blocker = _issue(905, "Some bug", state="open")

        surfaced, excluded = detector.compute_gaps([blocker, blocked], now=_NOW)

        assert surfaced == []
        excluded_slugs = {g.slug for g in excluded}
        assert "blocker-still-open-904-905" in excluded_slugs

    def test_an_issue_with_no_blocker_marker_produces_no_candidate_at_all(self):
        issue = _issue(906, "A regular bug report, no blocker mention at all.")

        surfaced, excluded = detector.compute_gaps([issue], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-blocker-marker-906"

    def test_a_blocked_issue_that_is_itself_already_closed_is_never_considered(self):
        # This recipe's seam is specifically a blocked issue that is STILL
        # open. One that already closed itself (whatever its body once
        # claimed) has no gap left to surface.
        blocked = _issue(907, "Blocked by #908", state="closed", closed_at=datetime(2026, 7, 22, 11, 0, 0, tzinfo=timezone.utc))
        blocker = _issue(908, "Some bug", state="closed", closed_at=datetime(2026, 7, 22, 10, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([blocker, blocked], now=_NOW)

        assert surfaced == []
        assert excluded == []

    def test_an_unrecognized_blocker_number_is_excluded_not_surfaced(self):
        blocked = _issue(909, "blocked on #999")

        surfaced, excluded = detector.compute_gaps([blocked], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "nonexistent-blocker-909-999"

    def test_a_denied_blocker_marker_produces_no_candidate_at_all(self):
        # Before the fix, this body's "not blocked by #920" was read as an
        # unnegated marker naming #920 as a live blocker -- since #920 is
        # closed, that misfired straight into `unblocked-issue-still-open`.
        # The negation must not turn a denial into a false gap.
        blocked = _issue(919, "This is not blocked by #920 anymore, we're clear.")
        blocker = _issue(920, "Some bug", state="closed", closed_at=datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc))

        surfaced, excluded = detector.compute_gaps([blocker, blocked], now=_NOW)

        assert surfaced == []
        assert excluded[0].slug == "no-blocker-marker-919"

    def test_a_closed_blocker_with_no_timestamp_is_excluded_as_malformed_not_still_open(self):
        blocked = _issue(910, "Blocked by #911")
        blocker = _issue(911, "Some bug", state="closed", closed_at=None)

        surfaced, excluded = detector.compute_gaps([blocker, blocked], now=_NOW)

        assert surfaced == []
        by_slug = {g.slug: g for g in excluded}
        candidate = by_slug["blocker-closed-no-timestamp-910-911"]
        assert "has not closed yet" not in candidate.detail
        assert "malformed" in candidate.detail
        assert candidate.evidence == [blocked.url, blocker.url]


class TestNonexistentBlockerIsNotMislabeledStillOpen:
    """The identical split `duplicate-issue-still-open`'s own
    `nonexistent-original-...` vs `original-still-open-...` branches make:
    a dangling reference (the named blocker was never real) and a
    genuinely-unresolved blocker are different facts about the world and
    must not share a slug or a detail line."""

    def test_a_named_blocker_that_does_not_exist_is_excluded_as_nonexistent_not_still_open(self):
        blocked = _issue(912, "blocked by #999")  # #999 is never in the issue list at all

        surfaced, excluded = detector.compute_gaps([blocked], now=_NOW)

        assert surfaced == []
        assert len(excluded) == 1
        candidate = excluded[0]
        assert candidate.slug == "nonexistent-blocker-912-999"
        assert "closed" not in candidate.detail
        assert "open" not in candidate.detail
        assert candidate.evidence == [blocked.url]  # no blocker.url to append -- it doesn't exist

    def test_a_named_blocker_that_exists_and_is_still_open_is_still_excluded_as_still_open(self):
        blocked = _issue(913, "Blocked by #914")
        blocker = _issue(914, "Some bug", state="open")

        surfaced, excluded = detector.compute_gaps([blocker, blocked], now=_NOW)

        assert surfaced == []
        by_slug = {g.slug: g for g in excluded}
        candidate = by_slug["blocker-still-open-913-914"]
        assert candidate.evidence == [blocked.url, blocker.url]


class TestRunRecipeScan:
    def test_the_shipped_fixture_elects_exactly_one_primary_gap(self):
        result = detector.run_recipe_scan(now=_NOW)
        assert result["primary_gap"] is not None
        assert result["primary_gap"]["slug"] == "unblocked-issue-still-open-901-900"
        assert result["primary_gap"]["confidence"] == 0.85

    def test_the_shipped_fixture_weighs_the_recently_closed_blocker_in_the_tail(self):
        result = detector.run_recipe_scan(now=_NOW)
        tail_slugs = {g["slug"] for g in result["tail"]}
        assert "unblocked-issue-still-open-902-903" in tail_slugs

    def test_the_shipped_fixture_excludes_the_still_open_named_blocker(self):
        result = detector.run_recipe_scan(now=_NOW)
        excluded_slugs = {g["slug"] for g in result["excluded"]}
        assert "blocker-still-open-904-905" in excluded_slugs
        assert "no-blocker-marker-906" in excluded_slugs
        assert "nonexistent-blocker-909-999" in excluded_slugs
        assert "blocker-closed-no-timestamp-910-911" in excluded_slugs

    def test_the_shipped_fixture_never_considers_the_already_closed_blocked_issue(self):
        result = detector.run_recipe_scan(now=_NOW)
        all_slugs = {g["slug"] for g in result["excluded"]}
        all_slugs |= {g["slug"] for g in result["tail"]}
        if result["primary_gap"]:
            all_slugs.add(result["primary_gap"]["slug"])
        assert not any("-907-" in s for s in all_slugs)


class TestLoaders:
    """load_issues -- mirrors every prior recipe's own _load_rows guard
    against syntactically valid but non-list JSON."""

    def test_load_issues_parses_the_real_fixture(self):
        issues = detector.load_issues()
        assert len(issues) > 0
        assert all(isinstance(i, detector.Issue) for i in issues)

    @pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
    def test_load_issues_raises_named_error_not_typeerror_when_json_is_not_a_list(
        self, tmp_path: Path, bad_value: object
    ):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps(bad_value))
        with pytest.raises(ValueError, match="expected a JSON list"):
            detector.load_issues(bad_file)
