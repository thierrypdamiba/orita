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
    # The integration proof: against the real RECIPES/ tree (all three real
    # recipes shipped by tasks 22, 108, 110), the combined scan runs clean.
    monkeypatch.setattr(scan_mod, "fetch_github_activity", lambda *a, **k: [])

    result = run_combined_scan("thierrypdamiba", "orita", x_posts=BASE_X_POSTS)

    assert result["recipe_errors"] == []
    contributing_slugs = {s["slug"] for s in result["recipe_sources"]}
    assert contributing_slugs == {
        "example-release-vs-changelog",
        "merged-pr-issue-still-open",
        "release-not-tweeted",
    }
