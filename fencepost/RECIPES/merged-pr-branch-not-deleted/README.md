# merged-pr-branch-not-deleted

The fortieth real recipe, and the third leg of a branch-lifecycle trio this
engine now covers end to end: `stale-branch-no-pr` watches a branch survive
with no PR ever pointing at it; `deleted-branch-pr-still-open` watches a
branch's promise (an open PR) survive after the branch itself is gone; this
one watches the branch survive AFTER its own promise has already resolved.

**The seam it watches:** a pull request reaches a terminal state — merged,
or closed without merging — but no `branch_deletion` event was ever
recorded for its head branch. GitHub's merge UI offers a "Delete branch"
button, but nothing forces it; the branch just sits in the branch list
forever unless a human happens to click it or remembers to clean up by
hand. Neither the pull-request list alone (a resolved PR's own `head_ref`
field reads identically whether the branch behind it is alive or already
gone) nor the Activity feed alone (a deletion event's *absence* proves
nothing on its own) shows this — only holding both at the same instant
does. Two fixtures, no live account —
[`../../fixtures/merged_pr_branch_not_deleted/pull_requests.json`](../../fixtures/merged_pr_branch_not_deleted/pull_requests.json)
and
[`../../fixtures/merged_pr_branch_not_deleted/activities.json`](../../fixtures/merged_pr_branch_not_deleted/activities.json)
— shaped like what `ListPullRequests`/`ListRepositoryActivities` would
actually return, both already on `SCOPES.md`'s cleared oath table. No new
scope is asked for anywhere in this recipe.

Confidence is age-gated on how long ago the pull request resolved while its
branch remains undeleted, not flat — 24 hours, mirroring
`deleted-branch-pr-still-open`'s own grace window on the same lifecycle (a
PR resolved minutes ago may just be mid-cleanup, not yet a real gap). See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/merged-pr-branch-not-deleted/detector.py
```

Run bare like this it uses the real wall clock, so the fixture's own
resolved-PR ages (and therefore which one clears 24 hours) will drift as
real time passes — expected for a manual demo, not a bug, the same
documented property every age-gated MOCK-only fixture in this repo already
carries. The test suite always pins `now` explicitly so the result stays
deterministic in CI.

It finds one real gap in its own fixture (PR #145, confidence 0.85 — merged
well over 24 hours before the pinned clock, its branch
`feature/dark-mode-toggle` never deleted), ranks PR #150 into the tail
(confidence 0.5 — closed only 16 hours before the pinned clock, still inside
the grace window), and correctly excludes PR #152 (its branch
`chore/bump-deps-2` was deleted too, the ordinary case this recipe is
deliberately not about) and PR #160 (still open — no cleanup promise has
been missed yet).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/merged-pr-branch-not-deleted/recipe.json
```
