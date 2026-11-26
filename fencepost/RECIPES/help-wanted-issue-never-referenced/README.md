# help-wanted-issue-never-referenced

The hundred-fourteenth real recipe (ROADMAP.md #2683) — the sibling of
[`../good-first-issue-never-referenced/`](../good-first-issue-never-referenced/)
(task 499) for GitHub's other standard onboarding label. `good first issue`
had a watcher; `help wanted` — the same explicit "come help with this one"
invitation, aimed at a shelf item that doesn't need to be beginner-scoped —
never did, until this recipe.

**The seam it watches:** `ListIssues` shows the label; `ListPullRequests`
shows every PR's own claimed closes. Neither list alone shows whether the
invitation was answered — only holding both at once, and checking whether
any PR body names the labeled issue's number via `closes #N` / `fixes #N`
/ `resolves #N` (either tense), shows it. Same shape exactly as the
`good-first-issue-never-referenced` twin: `Issue`/`PullRequest` dataclasses,
`seam_engine.closing_keywords.closing_keyword_numbers` reused verbatim, the
identical `(surfaced, excluded)` return.

Two fixtures, no live account —
[`../../fixtures/help_wanted_issue_never_referenced/issues.json`](../../fixtures/help_wanted_issue_never_referenced/issues.json)
and
[`../../fixtures/help_wanted_issue_never_referenced/pulls.json`](../../fixtures/help_wanted_issue_never_referenced/pulls.json)
— shaped like what `ListIssues`/`ListPullRequests` would actually return.
Both scopes already sit on `SCOPES.md`'s cleared oath table — no new scope
is asked for anywhere in this recipe.

One deliberate difference from the twin, reasoned not copied: confidence is
age-gated on a 336-hour (14-day) staleness bar, double
`good-first-issue-never-referenced`'s own 168h bar. `help wanted` is
GitHub's own signal that a shelf item is NOT scoped for a first-time
contributor — it typically wants more context or more time to find the
right stranger — so it honestly deserves longer before unanswered silence
counts as a settled gap rather than a contributor simply not having found
it yet. Under 336 hours scores 0.5, below the 0.70 confidence bar, weighed
in the tail not hidden. At or past 336 hours, a flat 0.85. An issue not
labeled `help wanted` is not this recipe's concern at all (skipped, not
even named in `excluded` — it was never a candidate). An issue already
closed, or one named by at least one PR's closing keyword (open, closed,
or merged — an abandoned attempt still counts as someone noticing), is
excluded, named not hidden.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/help-wanted-issue-never-referenced/detector.py
```

The shipped fixture (issue #801, open since 2026-07-01, zero PR reference)
elects the primary gap for real:

```json
{
  "slug": "help-wanted-issue-never-referenced-801",
  "headline": "Issue #801 ('Add a dark-mode toggle to the Gap Ledger site') is labeled 'help wanted', no pull request has ever named it",
  "confidence": 0.85
}
```

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/help-wanted-issue-never-referenced/recipe.json
```
