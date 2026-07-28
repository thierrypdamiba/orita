# issue-closed-pr-still-open

The sixth real recipe. [`merged-pr-issue-still-open`](../merged-pr-issue-still-open/)
(task 108) watches a PR that MERGED and promised to close an issue that
didn't. This recipe watches the mirror case, a seam none of the five
recipes before it touch.

**The seam it watches:** a pull request is still OPEN — never merged, so
GitHub's own auto-close automation never had a trigger to fire — and names
a closing keyword (`closes #N` / `fixes #N` / `resolves #N`) for an issue
that has since closed anyway, through some route that has nothing to do
with this PR: a duplicate report, a manual close, a different PR that
actually shipped the fix. The open PR is now orphaned — whatever it set out
to do, the thing it named as its reason already happened without it. Two
fixtures, no live account —
[`../../fixtures/issue_closed_pr_still_open/pulls.json`](../../fixtures/issue_closed_pr_still_open/pulls.json)
and
[`../../fixtures/issue_closed_pr_still_open/issues.json`](../../fixtures/issue_closed_pr_still_open/issues.json)
— shaped like what `ListPullRequests` / `ListIssues` / `GetIssue` would
actually return, all three already on `SCOPES.md`'s cleared oath table. No
new scope is asked for anywhere in this recipe.

Confidence is age-gated on how long the named issue has been closed while
the PR sits open, not flat — 48 hours, between `merged-pr-issue-still-open`'s
24h (a merge-triggered auto-close fires within hours or it's broken) and
`contributor-thanked-not-credited`'s 72h (a README credit is a slower edit
than either). See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/issue-closed-pr-still-open/detector.py
```

Run bare like this it uses the real wall clock, so the fixture PRs' ages
(and therefore which ones clear 48 hours) will drift as real time passes —
expected for a manual demo, not a bug. The test suite always pins `now`
explicitly so the result stays deterministic in CI.

It finds one real gap in its own fixture (PR #601, confidence 0.85 — its
named issue #501 closed 123 hours before the pinned clock, through some
other route entirely) and correctly excludes PR #603 (named issue #503 is
still open — the ordinary, unremarkable case) and PR #604 (no closing
keyword at all), while PR #602 (named issue closed only 4 hours before the
pinned clock) is weighed and shown in the tail as a coincidence, not hidden
and not electing itself.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/issue-closed-pr-still-open/recipe.json
```
