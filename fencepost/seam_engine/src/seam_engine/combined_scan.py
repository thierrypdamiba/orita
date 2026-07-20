"""The combined election: `scan.py`'s own candidates plus every merged
recipe's, in ONE ranked pool. ROADMAP.md #111.

`CONTRIBUTING.md` has said since task 22 that wiring a recipe into the daily
primary-election path is "a separate, later step" from getting a recipe
*merged* — merging only ever proved a recipe's detector runs and finds its
own fixture gap in isolation (`test_recipes.py`'s `test_third_recipe_
detector_actually_runs_and_finds_its_gap` and its siblings). Three real
recipes have shipped since (tasks 22, 108, 110) and `run_scan` — what
`seam-scan.yml` actually calls every day — has never once called
`discover_recipes()`. The promise that "a stranger's recipe merges beside a
god's" and competes for the single primary gap has never actually happened.
This module is that step: `run_combined_scan` runs `scan.run_scan` for the
real GitHub-vs-X candidates, runs every discovered recipe's own entrypoint,
converts each recipe's own `primary_gap`/`tail` back into plain
`GapCandidate`s (dropping the `label`/`rank`/`lead` a recipe's own isolated
`rank()` call already stamped on them — those are stale outside that
recipe's own pool), pools everything, and calls `ranking.rank()` exactly
ONCE over the combined field. A recipe's candidate can now actually
out-rank `scan.py`'s own, or lose to it, fairly — the literal proof the
promise is real, both directions tested in `tests/test_combined_scan.py`.

One recipe raising (a broken fixture, a bad import) is caught and named in
`recipe_errors`, never allowed to take the real daily report down over a
single bad manifest — the same fails-safely discipline `audit.py`'s and
`badge.py`'s `|| true` CI steps already hold themselves to.

NOT wired into `seam-scan.yml` yet, on purpose. Every recipe today reads a
`fixture` under `fixtures/<slug>/`, per the MOCK ONLY oath (`CONTRIBUTING.md`,
`recipes.py`'s own validator) — its data never changes day to day. Folding a
recipe's candidate into the REAL public daily report before it holds a live
Arcade scope would not just risk a false positive, Ogun's law's ordinary
worry — it would fabricate a gap that is not actually true of the town's
live accounts today, using data frozen the day the recipe was written. That
is worse than `gmail_calendar.py`'s own honest WIP boundary (`SCOPES.md`'s
"WIP note", ROADMAP.md #16): a fixture recipe never even claims to be fresh.
This module is real, tested machinery, ready the moment a recipe's own
`fixture`/`scopes` graduate to a live read — the same day `gmail_calendar.py`
does. Until then, `seam-scan.yml` keeps calling `scan.py` alone.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from seam_engine.ranking import rank
from seam_engine.recipes import RecipeManifest, RecipeValidationError, discover_recipes, load_detector
from seam_engine.scan import GapCandidate, run_scan


def _candidate_from_recipe_gap(gap: dict[str, Any], *, recipe_slug: str) -> GapCandidate:
    """A recipe's own `primary_gap`/`tail` entry, already ranked once inside
    that recipe's isolated pool, converted back to a plain `GapCandidate` so
    it can be ranked again, fairly, inside the combined pool. `label`/`rank`/
    `lead` are dropped on purpose — they described this candidate's standing
    among that one recipe's own field, not the combined one it is about to
    join. The slug is namespaced by recipe so two recipes can never collide
    on the same bare slug.
    """
    return GapCandidate(
        slug=f"recipe-{recipe_slug}-{gap['slug']}",
        headline=gap["headline"],
        detail=gap["detail"],
        confidence=gap["confidence"],
        evidence=list(gap.get("evidence", [])),
    )


def _run_one_recipe(manifest: RecipeManifest) -> tuple[list[GapCandidate], dict[str, Any] | None]:
    """Run one recipe's entrypoint. Returns (candidates, error).

    `error` is `None` on success; on any exception (bad fixture, missing
    import, a detector that raises, OR a detector that returns cleanly but
    hands back a `primary_gap`/`tail` entry missing a required key —
    ROADMAP.md #172, `recipes.py`'s own validator only ever checks a
    recipe's `recipe.json` manifest, never what its `detector()` actually
    returns at runtime), `candidates` is empty and `error` names the recipe
    and the exception — the caller folds this into `recipe_errors` rather
    than letting one bad recipe take the whole combined scan down. Building
    `candidates` from `result` therefore stays inside the same try as
    calling `detector()`: a malformed-but-non-raising return is exactly as
    recoverable as a raising one, and must be caught the same way.
    """
    try:
        detector = load_detector(manifest)
        result = detector()
        gaps = [g for g in [result.get("primary_gap")] + list(result.get("tail", [])) if g]
        candidates = [_candidate_from_recipe_gap(g, recipe_slug=manifest.slug) for g in gaps]
    except Exception as exc:  # noqa: BLE001 -- a third-party recipe's own code; anything can raise
        return [], {"slug": manifest.slug, "error": f"{type(exc).__name__}: {exc}"}

    return candidates, None


def run_combined_scan(
    owner: str,
    repo: str,
    window_hours: int = 24,
    x_posts: list[dict[str, Any]] | None = None,
    github_events: list[dict[str, Any]] | None = None,
    fencepost_root: Path | None = None,
) -> dict[str, Any]:
    """Run `scan.py`'s own scan plus every discovered recipe's, ranked once,
    together. Same output shape as `run_scan`, plus `recipe_sources` (which
    recipes actually contributed a candidate) and `recipe_errors` (which
    recipes raised and were skipped, named not hidden).

    `github_events=None` (the default): unchanged behavior — `run_scan` calls
    `fetch_github_activity` directly, exactly as before this parameter
    existed. `github_events=<list of normalized dicts>`: threaded straight
    through as `run_scan`'s own `github_events` override (see its docstring,
    ROADMAP.md #128) — this module has no live-vs-fixture decision of its
    own to make here; it only forwards the one `scan.py` already owns.

    A recipe manifest that fails the read-only oath itself (`discover_recipes`
    raising `RecipeValidationError`) is treated the same way — named in
    `recipe_errors` as a single entry, `scan.py`'s own candidates still rank.
    That should never happen against a merged tree (CI already refuses a PR
    that breaks the oath), but the combined scan does not get to assume its
    own input is clean; it only gets to refuse to go down with it.
    """
    base = run_scan(owner, repo, window_hours=window_hours, x_posts=x_posts, github_events=github_events)

    pool: list[GapCandidate] = []
    if base["primary_gap"]:
        pool.append(GapCandidate(**{k: base["primary_gap"][k] for k in ("slug", "headline", "detail", "confidence", "evidence")}))
    for g in base["tail"]:
        pool.append(GapCandidate(**{k: g[k] for k in ("slug", "headline", "detail", "confidence", "evidence")}))

    recipe_sources: list[dict[str, Any]] = []
    recipe_errors: list[dict[str, Any]] = []

    try:
        manifests = discover_recipes(fencepost_root)
    except RecipeValidationError as exc:
        manifests = []
        recipe_errors.append({"slug": "<discover_recipes>", "error": str(exc)})

    for manifest in manifests:
        candidates, error = _run_one_recipe(manifest)
        if error is not None:
            recipe_errors.append(error)
            continue
        pool.extend(candidates)
        recipe_sources.append({"slug": manifest.slug, "author": manifest.author, "candidates": len(candidates)})

    ranking = rank(pool)

    return {
        **base,
        "primary_gap": asdict(ranking.primary) if ranking.primary else None,
        "tail": [asdict(g) for g in ranking.tail],
        "recipe_sources": recipe_sources,
        "recipe_errors": recipe_errors,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI: `python -m seam_engine.combined_scan [output.json] [--x-posts <path>]
    [--github-events <path>]`.

    Mirrors `scan.main`'s CLI shape exactly — both flags, not just the first.
    Informational only — not wired into `seam-scan.yml` (see module
    docstring for why).
    """
    import json
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)

    x_posts: list[dict[str, Any]] | None = None
    if "--x-posts" in argv:
        i = argv.index("--x-posts")
        if i + 1 >= len(argv):
            print("--x-posts needs a path to a JSON file of normalized live posts.")
            return 2
        x_posts_path = Path(argv[i + 1])
        del argv[i : i + 2]
        x_posts = json.loads(x_posts_path.read_text())

    github_events: list[dict[str, Any]] | None = None
    if "--github-events" in argv:
        i = argv.index("--github-events")
        if i + 1 >= len(argv):
            print("--github-events needs a path to a JSON file of normalized live events.")
            return 2
        github_events_path = Path(argv[i + 1])
        del argv[i : i + 2]
        github_events = json.loads(github_events_path.read_text())

    out = argv[0] if argv else None
    result = run_combined_scan("thierrypdamiba", "orita", x_posts=x_posts, github_events=github_events)
    text = json.dumps(result, indent=2, default=str)
    if out:
        Path(out).write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
