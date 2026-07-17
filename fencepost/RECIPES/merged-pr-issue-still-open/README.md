# merged-pr-issue-still-open

The second real recipe (ROADMAP.md #108) — [`../example-release-vs-changelog/`](../example-release-vs-changelog/)
stood alone from task 22 through task 107. This one exists to prove the other
half of [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md)'s pitch: a second,
independently-written detector sits beside the reference one and both still
clear `discover_recipes()`'s oath together.

**The seam it watches:** a pull request merges naming a GitHub closing
keyword (`closes #N` / `fixes #N` / `resolves #N`), but the issue it named is
still open. Two fixtures, no live account —
[`../../fixtures/merged_pr_issue_still_open/pulls.json`](../../fixtures/merged_pr_issue_still_open/pulls.json)
and
[`../../fixtures/merged_pr_issue_still_open/issues.json`](../../fixtures/merged_pr_issue_still_open/issues.json)
— shaped like what `ListPullRequests` / `ListIssues` / `GetIssue` would
actually return, all three already on `SCOPES.md`'s cleared oath table. No
new scope is asked for anywhere in this recipe.

Confidence is age-gated, not flat: a promised close under 24 hours old
scores 0.55 (below the bar — auto-close can lag, or nobody's looked yet);
at or past 24 hours it scores 0.85 (an unambiguous, non-fuzzy signal). See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/merged-pr-issue-still-open/detector.py
```

Run bare like this it uses the real wall clock, so the two fixture PRs'
ages (and therefore which ones clear 24 hours) will drift as real time
passes — that is expected for a manual demo, not a bug; the test suite
(`seam_engine/tests/test_recipes.py`) always pins `now` explicitly so the
result stays deterministic in CI.

It finds one real gap in its own fixture (PR #101, confidence 0.85 — merged
stale, still open) and correctly excludes PR #102 (issue already closed),
PR #103 (no closing keyword at all), while PR #104 (fresh, <24h) is weighed
and shown in the tail as a coincidence, not hidden and not electing itself
primary.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/merged-pr-issue-still-open/recipe.json
```
