# deleted-branch-pr-still-open

The thirtieth real recipe. Every recipe before this one watched a seam
between two document-shaped records (an issue, a PR body, a release, a
tweet). This one is the first to read the repository's own **Activity**
feed — `ListRepositoryActivities`, on `SCOPES.md`'s oath table since the
first day but never used by a shipped recipe until now.

**The seam it watches:** a pull request's head branch is deleted upstream —
a stale feature branch cleaned up, a force-push-and-delete, a merge-queue
bot tidying up after itself — but GitHub does not treat "the source branch
is gone" as a reason to close the PR built on it. The PR just sits there,
open, permanently unmergeable, until a human happens to notice and closes
it by hand. Neither the Activity feed alone (a deletion event names a ref,
not a PR number) nor the PR list alone (an open PR's own `head_ref` field
reads identically whether the branch is alive or already gone) shows this —
only holding both at the same instant does. Two fixtures, no live account —
[`../../fixtures/deleted_branch_pr_still_open/activities.json`](../../fixtures/deleted_branch_pr_still_open/activities.json)
and
[`../../fixtures/deleted_branch_pr_still_open/pull_requests.json`](../../fixtures/deleted_branch_pr_still_open/pull_requests.json)
— shaped like what `ListRepositoryActivities`/`ListPullRequests` would
actually return, both already on `SCOPES.md`'s cleared oath table. No new
scope is asked for anywhere in this recipe.

Confidence is age-gated on how long ago the deletion event fired while the
PR still reads open, not flat — 24 hours, mirroring
`duplicate-issue-still-open`'s own grace window (a branch deleted minutes
ago may just be an in-progress rebase, not yet a real gap). See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/deleted-branch-pr-still-open/detector.py
```

Run bare like this it uses the real wall clock, so the fixture's own
deletion-event ages (and therefore which one clears 24 hours) will drift as
real time passes — expected for a manual demo, not a bug, the same
documented property every age-gated MOCK-only fixture in this repo already
carries. The test suite always pins `now` explicitly so the result stays
deterministic in CI.

It finds one real gap in its own fixture (PR #88, confidence 0.85 — its
branch `feature/login-timeout-fix` was deleted well over 24 hours before the
pinned clock and the PR still reads open) and correctly excludes PR #81
(its branch `chore/bump-deps` was deleted too, but the PR had already merged
— the ordinary, unremarkable case) and the deletion of
`spike/cache-experiment` (no PR in the fixture ever pointed at it). The
fixture's own `push` event to `main` is silently skipped — it names no
deleted branch, so it is not this seam at all.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/deleted-branch-pr-still-open/recipe.json
```
