# good-first-issue-never-referenced

The thirty-eighth real recipe (ROADMAP.md #499). Every recipe in the
`*-still-open` family watches a promise already made and possibly broken —
a closing keyword, a merged PR, a released tag. This one watches a
promise nobody has even tried to keep yet: a `good first issue` label —
GitHub's own explicit "this one's easy, come help" — sitting on an open
issue that no pull request, ever, in any state, has named through a real
closing keyword.

**The seam it watches:** `ListIssues` shows the label; `ListPullRequests`
shows every PR's own claimed closes. Neither list alone shows whether the
invitation was answered — only holding both at once, and checking whether
any PR body names the labeled issue's number via `closes #N` / `fixes #N`
/ `resolves #N` (either tense), shows it. This is the mirror question
[`../stale-branch-no-pr/`](../stale-branch-no-pr/) (task 485) already asks
for a branch that never became a PR at all, aimed instead at the one
label whose entire purpose is to be picked up by a stranger — and the
same real, live gap the town's own
[issue #7](https://github.com/thierrypdamiba/orita/issues/7) ("Good first
issue: write a seam recipe nobody's built yet") asks a mortal to close.

Two fixtures, no live account —
[`../../fixtures/good_first_issue_never_referenced/issues.json`](../../fixtures/good_first_issue_never_referenced/issues.json)
and
[`../../fixtures/good_first_issue_never_referenced/pulls.json`](../../fixtures/good_first_issue_never_referenced/pulls.json)
— shaped like what `ListIssues`/`ListPullRequests` would actually return.
Both scopes already sit on `SCOPES.md`'s cleared oath table — no new
scope is asked for anywhere in this recipe. Reuses
`seam_engine.closing_keywords.closing_keyword_numbers` verbatim, the same
shared grammar three other recipes already import from there, rather than
a fifth independently retyped copy of the identical regex.

Confidence is age-gated on how long the labeled issue has sat open with
zero PR reference — under 168 hours (7 days), 0.5, below the bar, weighed
in the tail not hidden (a contributor may simply not have found it yet);
at or past 168 hours, a flat 0.85. Longer than the `*-still-open` family's
24-hour bar on purpose: this measures whether anyone has *started*, a
slower human cadence than whether an existing promise already broke. An
issue not labeled `good first issue` is not this recipe's concern at all
(skipped, not even named in `excluded` — it was never a candidate). An
issue already closed, or one named by at least one PR's closing keyword
(open, closed, or merged — an abandoned attempt still counts as someone
noticing), is excluded, named not hidden.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/good-first-issue-never-referenced/detector.py
```

The shipped fixture (issue #601, open 333h+ with zero PR reference)
elects the primary gap for real:

```json
{
  "slug": "good-first-issue-never-referenced-601",
  "headline": "Issue #601 ('Write a seam recipe for the milestone-description family') is labeled 'good first issue', no pull request has ever named it",
  "confidence": 0.85
}
```

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/good-first-issue-never-referenced/recipe.json
```
