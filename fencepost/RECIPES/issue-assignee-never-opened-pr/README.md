# issue-assignee-never-opened-pr

The seventy-seventh real recipe (ROADMAP.md #652). `assignees` — GitHub's
own structured, private "you specifically are on the hook" field, set on
an issue by a maintainer naming one exact person — had never been read by
any of the seventy-six recipes before this one, confirmed by grep against
every recipe docstring, README, and fixture in the tree. It is a genuinely
different field from a `good first issue` label
([`../good-first-issue-never-referenced/`](../good-first-issue-never-referenced/),
task 499): a label is a public open call to any stranger; an assignment
names one person and holds them to it, in a way GitHub's own UI implies
but its API never checks.

**The seam it watches:** an open issue carries at least one named
assignee, but none of them has ever opened a pull request that names the
issue via a real closing keyword. `ListIssues` alone shows who was asked;
`ListPullRequests` alone shows who opened what — only holding both at
once, and matching *identity* (the PR's own author against the issue's
own assignee list), not just existence, shows whether the specific person
asked ever actually showed up.

This is a genuinely different axis from the two closest siblings, not a
retread:
[`../good-first-issue-never-referenced/`](../good-first-issue-never-referenced/)
asks whether *any* PR from *anyone* ever referenced the issue — pure
existence, no identity check at all. A stranger's PR closing the issue
satisfies that recipe but not this one — this recipe requires the closing
PR's own author to be one of the issue's own named assignees.
[`../merged-pr-requested-reviewer-never-reviewed/`](../merged-pr-requested-reviewer-never-reviewed/)
(task 597) is the only other recipe in the tree that matches identity
between two people-fields, but entirely inside one pull request's own
record (`requested_reviewers` against that same PR's own
`review_comments` authors). This recipe crosses object types instead: an
*issue's* own assignee field against a *different* object type's (a pull
request) authorship, the same "identical abstract shape, still a separate
recipe" precedent
[`../duplicate-issue-still-open/`](../duplicate-issue-still-open/),
[`../duplicate-pr-still-open/`](../duplicate-pr-still-open/), and
[`../duplicate-milestone-still-open/`](../duplicate-milestone-still-open/)
already established for each other.

Two fixtures, no live account —
[`../../fixtures/issue_assignee_never_opened_pr/issues.json`](../../fixtures/issue_assignee_never_opened_pr/issues.json)
and
[`../../fixtures/issue_assignee_never_opened_pr/pulls.json`](../../fixtures/issue_assignee_never_opened_pr/pulls.json)
— shaped like what `ListIssues`/`ListPullRequests` would actually return.
Both scopes already sit on `SCOPES.md`'s cleared oath table — no new scope
is asked for anywhere in this recipe. Reuses
`seam_engine.closing_keywords.closing_keyword_numbers` verbatim, the same
shared grammar ten prior recipes already import from there, rather than
an eleventh independently retyped copy of the identical regex.

Confidence is age-gated on how long the issue has sat open, assigned,
with zero matching-author PR activity — under 24 hours, 0.5, below the
bar, weighed in the tail not hidden (a same-day assignment deserves a
moment); at or past 24 hours, a flat 0.85. Shorter than
`good-first-issue-never-referenced`'s 168-hour bar on purpose: an
assignment is a direct, private ask of one named person, a faster human
cadence than a public label waiting for a stranger to even notice it. An
issue carrying no assignees at all is not this recipe's concern (skipped,
not even named in `excluded` — it was never a candidate). An issue
already closed is excluded, named not hidden — whatever happened, the
working promise resolved. An issue where at least one assignee authored a
PR (open, closed, or merged — an abandoned attempt still counts as a real
swing taken) naming the issue via a real closing keyword is excluded too
— the specific person asked is the one who showed up. This recipe never
claims the assignee is slow, stuck, or dropped the ball — assignment on
GitHub is famously loose, and real work often happens entirely outside a
pull request; the gap named is narrower and honest: nothing in the record
shows the specific person asked ever opened the specific channel GitHub's
own tooling expects that promise to travel through.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/issue-assignee-never-opened-pr/detector.py
```

Run bare like this it uses the real wall clock, so the fixture issues'
own ages will drift as real time passes — expected for a manual demo, not
a bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against the pinned test clock it finds one real gap in its own fixture as
the elected primary (issue `#801`, assigned to `mortal-contributor-a`,
confidence 0.85 — open 125h+ with zero matching-author PR activity) and
two more weighed in the tail (issue `#802`, fresh; issue `#806`, whose
own bystander PR from `some-other-mortal` closes it without either of its
two assignees ever opening one), while correctly excluding issue `#803`
(its own assignee `mortal-contributor-c` opened the closing PR — the
promise was kept), issue `#804` (already closed), and never naming issue
`#805` (no assignees at all — never a candidate).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/issue-assignee-never-opened-pr/recipe.json
```
