"""Tests for the combined election (ROADMAP.md #111): `scan.py`'s own
candidates and every discovered recipe's, ranked once, together.

Every scenario below avoids the real network (same discipline as
test_scan.py's own module docstring): `scan.fetch_github_activity` is
monkeypatched to a fixed list of `GithubEvent`s so the confidence a
scan.py-sourced candidate carries is fully controlled, not dependent on
GitHub's live state.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import seam_engine.combined_scan as combined_scan_mod
import seam_engine.scan as scan_mod
from seam_engine.combined_scan import run_combined_scan
from seam_engine.scan import GithubEvent

NOW = datetime(2026, 7, 17, 15, 0, tzinfo=timezone.utc)
LIVE_SINCE = NOW - timedelta(days=30)

# One real, unmatched X post — establishes account_live_since and gives
# scan.py's keyword-overlap check something real to compare against, without
# ever overlapping the release/milestone titles constructed below.
BASE_X_POSTS = [
    {"id": "1", "text": "hello world", "url": "https://x.com/oritatown/status/1",
     "ts": LIVE_SINCE.isoformat()},
]


def _write_recipe(recipes_dir: Path, slug: str, detector_body: str) -> None:
    d = recipes_dir / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "recipe.json").write_text(json.dumps({
        "slug": slug, "title": "T", "author": "test", "description": "d",
        "toolkit": "github", "scopes": ["ListRepoCommits"],
        "fixture": "fixtures/x", "detector_file": "detector.py",
        "entrypoint": "run_recipe_scan", "confidence_notes": "n",
    }))
    (d / "detector.py").write_text(detector_body)


def _recipe_returning(headline: str, confidence: float, *, slug: str = "gap") -> str:
    return (
        "def run_recipe_scan():\n"
        "    return {\n"
        "        'generated_at': '2026-07-17T15:00:00Z',\n"
        "        'source': 'fixture',\n"
        "        'confidence_bar': 0.70,\n"
        "        'separation_margin': 0.15,\n"
        "        'primary_gap': {\n"
        f"            'slug': {slug!r}, 'headline': {headline!r}, 'detail': 'd',\n"
        f"            'confidence': {confidence}, 'evidence': ['https://example.com'],\n"
        "            'label': 'primary', 'rank': 1, 'lead': 1.0,\n"
        "        },\n"
        "        'tail': [],\n"
        "        'excluded': [],\n"
        "    }\n"
    )


def _raising_recipe() -> str:
    return "def run_recipe_scan():\n    raise RuntimeError('fixture is missing')\n"


def _malformed_recipe() -> str:
    # Returns cleanly (no exception) but its primary_gap is missing the
    # headline/detail/confidence keys _candidate_from_recipe_gap requires —
    # a schema-valid recipe.json (recipes.py never runs or type-checks a
    # detector's return value) whose detector nonetheless hands back a
    # malformed gap at runtime. ROADMAP.md #172.
    return (
        "def run_recipe_scan():\n"
        "    return {\n"
        "        'generated_at': '2026-07-17T15:00:00Z',\n"
        "        'source': 'fixture',\n"
        "        'confidence_bar': 0.70,\n"
        "        'separation_margin': 0.15,\n"
        "        'primary_gap': {'slug': 'oops'},\n"
        "        'tail': [],\n"
        "        'excluded': [],\n"
        "    }\n"
    )


def _milestone_events(n: int) -> list[GithubEvent]:
    """`n` milestone-tagged commits since account_live_since, by a real
    (non-quiet-voice) author, none overlapping BASE_X_POSTS' keywords —
    scan.py's own `compute_candidates` scores this
    `min(0.85, 0.35 + 0.1*n)`, so n=4 gives a deterministic 0.75.
    """
    return [
        GithubEvent(
            kind="commit", id=f"abc{i:04d}", title="ship the flagship pivot",
            url=f"https://github.com/thierrypdamiba/orita/commit/abc{i:04d}",
            ts=LIVE_SINCE + timedelta(days=1, hours=i), author="ogun",
        )
        for i in range(n)
    ]


def test_recipe_candidate_displaces_scans_own_primary(monkeypatch, tmp_path):
    # Scan's own field alone would elect its 4-milestone-commit candidate as
    # primary (confidence 0.75, alone in the field). A recipe with a
    # materially stronger, clearly-separated candidate (0.95) should win the
    # combined election instead — the literal "competes beside a god's and
    # can win" proof.
    monkeypatch.setattr(scan_mod, "fetch_github_activity", lambda *a, **k: _milestone_events(4))

    recipes_dir = tmp_path / "RECIPES"
    _write_recipe(recipes_dir, "strong-recipe", _recipe_returning("a real cross-account gap", 0.95))

    result = run_combined_scan(
        "thierrypdamiba", "orita", x_posts=BASE_X_POSTS, fencepost_root=tmp_path,
    )

    assert result["primary_gap"] is not None
    assert result["primary_gap"]["slug"] == "recipe-strong-recipe-gap"
    assert result["primary_gap"]["confidence"] == 0.95
    # Scan's own candidate is still present, just not elected.
    tail_slugs = {g["slug"] for g in result["tail"]}
    assert "milestone-unannounced" in tail_slugs
    assert result["recipe_sources"] == [{"slug": "strong-recipe", "author": "test", "candidates": 1}]
    assert result["recipe_errors"] == []


def test_scans_own_candidate_beats_a_weak_recipe(monkeypatch, tmp_path):
    # A release with no keyword-overlapping post scores a fixed 0.9 in
    # scan.py alone. A recipe candidate well below the confidence bar should
    # lose fairly: shown in the tail, never hidden, never elected.
    release = GithubEvent(
        kind="release", id="v1.0.0", title="Launch",
        url="https://github.com/thierrypdamiba/orita/releases/tag/v1.0.0",
        ts=LIVE_SINCE + timedelta(days=1), author="off-by-one",
    )
    monkeypatch.setattr(scan_mod, "fetch_github_activity", lambda *a, **k: [release])

    recipes_dir = tmp_path / "RECIPES"
    _write_recipe(recipes_dir, "weak-recipe", _recipe_returning("a minor coincidence", 0.4))

    result = run_combined_scan(
        "thierrypdamiba", "orita", x_posts=BASE_X_POSTS, fencepost_root=tmp_path,
    )

    assert result["primary_gap"] is not None
    assert result["primary_gap"]["slug"] == "release-v1.0.0"
    tail_slugs = {g["slug"] for g in result["tail"]}
    assert "recipe-weak-recipe-gap" in tail_slugs
    assert result["recipe_sources"] == [{"slug": "weak-recipe", "author": "test", "candidates": 1}]


def test_one_broken_recipe_is_named_and_does_not_stop_the_others(monkeypatch, tmp_path):
    # No scan.py-sourced candidates here on purpose — this scenario is about
    # one recipe's failure not poisoning another's success, not about
    # out-ranking scan.py (already proven above).
    monkeypatch.setattr(scan_mod, "fetch_github_activity", lambda *a, **k: [])

    recipes_dir = tmp_path / "RECIPES"
    _write_recipe(recipes_dir, "broken-recipe", _raising_recipe())
    _write_recipe(recipes_dir, "healthy-recipe", _recipe_returning("a healthy gap", 0.95))

    result = run_combined_scan(
        "thierrypdamiba", "orita", x_posts=BASE_X_POSTS, fencepost_root=tmp_path,
    )

    assert len(result["recipe_errors"]) == 1
    assert result["recipe_errors"][0]["slug"] == "broken-recipe"
    assert "fixture is missing" in result["recipe_errors"][0]["error"]

    healthy_sources = [s for s in result["recipe_sources"] if s["slug"] == "healthy-recipe"]
    assert healthy_sources == [{"slug": "healthy-recipe", "author": "test", "candidates": 1}]

    assert result["primary_gap"] is not None
    assert result["primary_gap"]["slug"] == "recipe-healthy-recipe-gap"


def test_a_malformed_non_raising_recipe_return_is_named_and_does_not_stop_the_others(monkeypatch, tmp_path):
    # ROADMAP.md #172: a recipe whose detector returns cleanly (no
    # exception) but hands back a primary_gap missing required keys used to
    # crash run_combined_scan outright with an uncaught KeyError, because
    # _run_one_recipe's try/except wrapped only the detector() call, not the
    # GapCandidate-construction that follows it. Same shape as the
    # already-covered raising-recipe case above: one bad recipe must never
    # take down the whole combined scan, whether it raises or just returns
    # garbage.
    monkeypatch.setattr(scan_mod, "fetch_github_activity", lambda *a, **k: [])

    recipes_dir = tmp_path / "RECIPES"
    _write_recipe(recipes_dir, "malformed-recipe", _malformed_recipe())
    _write_recipe(recipes_dir, "healthy-recipe", _recipe_returning("a healthy gap", 0.95))

    result = run_combined_scan(
        "thierrypdamiba", "orita", x_posts=BASE_X_POSTS, fencepost_root=tmp_path,
    )

    assert len(result["recipe_errors"]) == 1
    assert result["recipe_errors"][0]["slug"] == "malformed-recipe"
    assert "KeyError" in result["recipe_errors"][0]["error"]

    healthy_sources = [s for s in result["recipe_sources"] if s["slug"] == "healthy-recipe"]
    assert healthy_sources == [{"slug": "healthy-recipe", "author": "test", "candidates": 1}]

    assert result["primary_gap"] is not None
    assert result["primary_gap"]["slug"] == "recipe-healthy-recipe-gap"


def test_no_recipes_directory_is_the_same_as_scan_alone(monkeypatch, tmp_path):
    release = GithubEvent(
        kind="release", id="v1.0.0", title="Launch",
        url="https://github.com/thierrypdamiba/orita/releases/tag/v1.0.0",
        ts=LIVE_SINCE + timedelta(days=1), author="off-by-one",
    )
    monkeypatch.setattr(scan_mod, "fetch_github_activity", lambda *a, **k: [release])

    result = run_combined_scan(
        "thierrypdamiba", "orita", x_posts=BASE_X_POSTS, fencepost_root=tmp_path,
    )

    assert result["primary_gap"]["slug"] == "release-v1.0.0"
    assert result["recipe_sources"] == []
    assert result["recipe_errors"] == []


def test_runs_all_real_recipes_in_the_actual_repo_without_error(monkeypatch):
    # The integration proof: against the real RECIPES/ tree (all fifty-six
    # real recipes shipped by tasks 22, 108, 110, 368, 371, 373, 376, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 388, 390, 398, 399, 400, 401, 402, 403, 419, 450, 451, 452, 485, 486, 488, 489, 490, 491, 492, 493, 499, 512, 514, 520, 527, 530, 534, 535, 558, 564, 579, 581, 582, 585, 588, plus mention-claims-open-milestone, mention-claims-unmerged-pr, milestone-claims-unmerged-pr, milestone-claims-open-milestone), the combined scan runs clean.
    monkeypatch.setattr(scan_mod, "fetch_github_activity", lambda *a, **k: [])

    result = run_combined_scan("thierrypdamiba", "orita", x_posts=BASE_X_POSTS)

    assert result["recipe_errors"] == []
    contributing_slugs = {s["slug"] for s in result["recipe_sources"]}
    assert contributing_slugs == {
        "example-release-vs-changelog",
        "merged-pr-issue-still-open",
        "release-not-tweeted",
        "dangling-issue-reference",
        "contributor-thanked-not-credited",
        "issue-closed-pr-still-open",
        "duplicate-issue-still-open",
        "commit-closes-keyword-issue-still-open",
        "release-claims-unmerged-pr",
        "milestone-closed-issue-still-open",
        "milestone-closed-pr-still-open",
        "merged-pr-never-released",
        "release-claims-unfixed-issue",
        "milestone-closed-never-released",
        "readme-credited-not-thanked",
        "release-claims-open-milestone",
        "issue-closed-never-released",
        "mention-dangling-reference",
        "milestone-closed-not-tweeted",
        "merged-pr-not-tweeted",
        "issue-closed-not-tweeted",
        "duplicate-pr-still-open",
        "release-note-dangling-reference",
        "own-tweet-dangling-reference",
        "issue-body-dangling-reference",
        "commit-closes-keyword-pr-still-open",
        "merged-pr-pr-still-open",
        "tweet-claims-unmerged-pr",
        "tweet-claims-unfixed-issue",
        "tweet-claims-open-milestone",
        "deleted-branch-pr-still-open",
        "star-milestone-not-announced",
        "duplicate-milestone-still-open",
        "overdue-milestone-still-open",
        "stale-branch-no-pr",
        "readme-claims-open-milestone",
        "readme-claims-unfixed-issue",
        "readme-claims-unmerged-pr",
        "good-first-issue-never-referenced",
        "milestone-complete-still-open",
        "merged-pr-branch-not-deleted",
        "milestone-body-dangling-reference",
        "issue-closed-subissue-still-open",
        "review-comment-dangling-reference",
        "milestone-claims-unfixed-issue",
        "issue-checklist-complete-still-open",
        "mention-claims-unfixed-issue",
        "mention-claims-open-milestone",
        "mention-claims-unmerged-pr",
        "milestone-claims-unmerged-pr",
        "milestone-claims-open-milestone",
        "pr-checklist-complete-still-open",
        "issue-comment-dangling-reference",
        "review-comment-claims-unfixed-issue",
        "review-comment-claims-unmerged-pr",
        "review-comment-claims-open-milestone",
    }


# --- run_combined_scan's github_events override (ROADMAP.md #128, #141) -----
#
# `combined_scan.main`'s own docstring has claimed since task 111 that it
# "Mirrors `scan.main`'s CLI shape exactly" — true the day it was written,
# false the moment task 128 gave `scan.main` a second flag (`--github-events`)
# that `combined_scan.main` never gained. Nothing in this file, or anywhere
# else, ever checked the claim against `scan.main`'s real shape. These
# scenarios mirror test_scan.py's own github_events override + CLI tests
# line for line, proving the claim true again now that both flags exist.


def test_run_combined_scan_with_github_events_override_never_calls_fetch_github_activity(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("fetch_github_activity should not be called when github_events is supplied")

    monkeypatch.setattr(scan_mod, "fetch_github_activity", boom)
    live_events = [
        {"kind": "commit", "id": "1", "title": "t",
         "url": "https://github.com/thierrypdamiba/orita/commit/1",
         "ts": "2026-07-16T00:00:00Z", "author": "a"},
    ]

    result = run_combined_scan(
        "thierrypdamiba", "orita", x_posts=BASE_X_POSTS, github_events=live_events,
    )

    assert result["github_events_source"] == "override"


def test_run_combined_scan_without_github_events_uses_direct_fetch(monkeypatch):
    called = {}

    def fake_fetch(owner, repo, since):
        called["hit"] = True
        return []

    monkeypatch.setattr(scan_mod, "fetch_github_activity", fake_fetch)

    result = run_combined_scan("thierrypdamiba", "orita", x_posts=BASE_X_POSTS)

    assert called.get("hit") is True
    assert result["github_events_source"] == "direct"


# --- ROADMAP.md #180: check_prior_milestones/ledger_base threaded through --

# `run_combined_scan` delegated to `run_scan` but never passed
# `check_prior_milestones`/`ledger_base`, so it never inherited `run_scan`'s
# own guard against a truncated `github_events` silently under-reporting a
# real, ledger-sealed `milestone-unannounced` gap (`scan.py`'s own "Found
# and closed 2026-07-19" paragraph, ROADMAP.md #179's `seam_scan` fix).
# Reproduced live before this fix: handed a truncated override missing a
# sealed gap's evidence, `run_combined_scan` returned `primary_gap: None`
# with no error. These tests seed a fixture ledger the same way
# `test_scan.py`'s own `check_prior_milestones` tests do and prove the
# guard now reaches this entrypoint too.

from seam_engine import ledger as _ledger_mod  # noqa: E402 -- grouped with this section on purpose

_SEALED_EVIDENCE_URL = "https://github.com/thierrypdamiba/orita/commit/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
_SEALED_AT = "2026-07-18T13:10:49.350606+00:00"
_UNRELATED_EVENT_URL = "https://github.com/thierrypdamiba/orita/commit/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

_OLD_X_POSTS = [
    {"id": "1", "text": "old news", "url": "https://x.com/oritatown/status/1",
     "ts": "2026-07-12T00:00:00Z"},
]


def _seal_milestone_gap(base: Path) -> None:
    _ledger_mod.append_scan(
        {
            "generated_at": _SEALED_AT, "repo": "thierrypdamiba/orita",
            "window_hours": 24, "confidence_bar": 0.7, "separation_margin": 0.15,
            "primary_gap": {
                "slug": "milestone-unannounced", "headline": "h", "detail": "d",
                "confidence": 0.75, "evidence": [_SEALED_EVIDENCE_URL],
            },
            "tail": [], "excluded": [],
        },
        base=base,
    )


def test_run_combined_scan_check_prior_milestones_defaults_off_preserving_old_behavior(tmp_path):
    # Backward compatibility: every scenario above this section calls
    # run_combined_scan without check_prior_milestones and must keep working
    # unchanged -- a fixture ledger with real missing evidence is present,
    # but the default (False) means it is never even consulted.
    _seal_milestone_gap(tmp_path)
    truncated_events = [
        {"kind": "commit", "id": "unrelated", "title": "chore", "url": _UNRELATED_EVENT_URL,
         "ts": "2026-07-19T00:30:00Z", "author": "someone"},
    ]

    result = run_combined_scan(
        "thierrypdamiba", "orita", x_posts=_OLD_X_POSTS, github_events=truncated_events,
        ledger_base=tmp_path,
    )

    assert result["primary_gap"] is None  # the same silent miss -- unchanged, opt-in only


def test_run_combined_scan_raises_when_check_prior_milestones_true_and_evidence_missing(tmp_path):
    _seal_milestone_gap(tmp_path)
    truncated_events = [
        {"kind": "commit", "id": "unrelated", "title": "chore", "url": _UNRELATED_EVENT_URL,
         "ts": "2026-07-19T00:30:00Z", "author": "someone"},
    ]

    with pytest.raises(ValueError, match=r"missing 1 previously-sealed"):
        run_combined_scan(
            "thierrypdamiba", "orita", x_posts=_OLD_X_POSTS, github_events=truncated_events,
            check_prior_milestones=True, ledger_base=tmp_path,
        )


def test_run_combined_scan_does_not_raise_when_the_override_still_carries_all_open_evidence(tmp_path):
    _seal_milestone_gap(tmp_path)
    complete_events = [
        {"kind": "commit", "id": "a", "title": "fencepost milestone work", "url": _SEALED_EVIDENCE_URL,
         "ts": "2026-07-18T12:00:00Z", "author": "someone"},
        {"kind": "commit", "id": "unrelated", "title": "chore", "url": _UNRELATED_EVENT_URL,
         "ts": "2026-07-19T00:30:00Z", "author": "someone"},
    ]

    result = run_combined_scan(
        "thierrypdamiba", "orita", x_posts=_OLD_X_POSTS, github_events=complete_events,
        check_prior_milestones=True, ledger_base=tmp_path,
    )

    assert result["github_events_source"] == "override"


# --- the CLI's --github-events flag, threaded through combined_scan.main ----


def test_cli_main_rejects_missing_github_events_path_argument():
    assert combined_scan_mod.main(["--github-events"]) == 2


def test_cli_reads_github_events_file_and_threads_it_into_run_combined_scan(tmp_path, monkeypatch):
    captured = {}
    original = combined_scan_mod.run_combined_scan

    def fake_run_combined_scan(owner, repo, window_hours=24, x_posts=None, github_events=None, fencepost_root=None):
        captured["github_events"] = github_events
        return original(owner, repo, window_hours=window_hours, x_posts=x_posts, github_events=github_events, fencepost_root=fencepost_root)

    monkeypatch.setattr(combined_scan_mod, "run_combined_scan", fake_run_combined_scan)
    monkeypatch.setattr(scan_mod, "fetch_github_activity", lambda *a, **k: [])

    live_events = [
        {"kind": "commit", "id": "1", "title": "t",
         "url": "https://github.com/thierrypdamiba/orita/commit/1",
         "ts": "2026-07-16T00:00:00Z", "author": "a"},
    ]
    events_path = tmp_path / "live-events.json"
    events_path.write_text(json.dumps(live_events))
    out_path = tmp_path / "out.json"

    rc = combined_scan_mod.main([str(out_path), "--github-events", str(events_path)])

    assert rc == 0
    assert captured["github_events"] == live_events
    result = json.loads(out_path.read_text())
    assert result["github_events_source"] == "override"


def test_cli_without_github_events_flag_uses_direct_fetch(monkeypatch, tmp_path):
    monkeypatch.setattr(scan_mod, "fetch_github_activity", lambda *a, **k: [])
    out_path = tmp_path / "out.json"

    rc = combined_scan_mod.main([str(out_path)])

    assert rc == 0
    result = json.loads(out_path.read_text())
    assert result["github_events_source"] == "direct"


@pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
def test_cli_x_posts_with_non_list_json_raises_named_error(tmp_path, bad_value):
    """task 361: mirrors test_scan.py's identical test for scan.main --
    combined_scan.main shares scan.py's `_load_json_list` helper, closing
    the same non-list-JSON crash class (RECIPES/*/detector.py, task 358;
    gmail_calendar.py, task 359) on this module's own CLI loaders."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps(bad_value))
    out_path = tmp_path / "out.json"
    with pytest.raises(ValueError, match="expected a JSON list"):
        combined_scan_mod.main([str(out_path), "--x-posts", str(bad_file)])


@pytest.mark.parametrize("bad_value", [{"a": 1}, 5, None, "x", True])
def test_cli_github_events_with_non_list_json_raises_named_error(tmp_path, bad_value):
    """Mirrors test_cli_x_posts_with_non_list_json_raises_named_error for
    --github-events."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps(bad_value))
    out_path = tmp_path / "out.json"
    with pytest.raises(ValueError, match="expected a JSON list"):
        combined_scan_mod.main([str(out_path), "--github-events", str(bad_file)])


def test_cli_docstring_shape_claim_is_true_both_flags_supported():
    # A structural check on the claim itself, not just its behavior: the
    # docstring says combined_scan.main mirrors scan.main's CLI shape
    # exactly. Prove both modules' main() functions recognize the same two
    # flags, read straight off their own source rather than a second
    # hardcoded list -- the class of check tasks 135-140 already applied to
    # doc-vs-code mirror claims elsewhere in this codebase, aimed here at a
    # code-vs-code one instead.
    import inspect

    scan_source = inspect.getsource(scan_mod.main)
    combined_source = inspect.getsource(combined_scan_mod.main)
    for flag in ("--x-posts", "--github-events"):
        assert flag in scan_source, f"scan.main no longer recognizes {flag!r} -- test's own assumption is stale"
        assert flag in combined_source, f"combined_scan.main does not recognize {flag!r} -- the mirror claim is false"
