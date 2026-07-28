# dangling-issue-reference

The fourth real recipe, and the first that watches a seam INSIDE a single
commit message rather than between two whole records.
[`../example-release-vs-changelog/`](../example-release-vs-changelog/),
[`../merged-pr-issue-still-open/`](../merged-pr-issue-still-open/), and
[`../release-not-tweeted/`](../release-not-tweeted/) all compare two
complete, independently-real records and ask whether one echoed the other.
This one asks a narrower question of a single record: does the thing this
commit message *claims* — "part of #12", "see #99 for context" — actually
exist?

**The seam it watches:** GitHub renders `#N` inside a commit message as a
clickable link without ever checking it resolves to anything. A typo, a
reference to an issue that got deleted, or a number that belonged to a
different repo entirely all render identically — and a commit message is
the one record in this whole engine that never gets a second edit pass.
Nobody reads `git log` looking for a broken link between an author's own
sentence and the number they typed. This does.

Two fixture lists, no live account —
[`../../fixtures/dangling_issue_reference/commits.json`](../../fixtures/dangling_issue_reference/commits.json),
[`.../issues.json`](../../fixtures/dangling_issue_reference/issues.json), and
[`.../pulls.json`](../../fixtures/dangling_issue_reference/pulls.json) —
shaped like what `ListRepoCommits`/`ListIssues`/`ListPullRequests` would
actually return. All three declared scopes already sit on `SCOPES.md`'s
cleared oath table under the `github` row. No new scope is asked for
anywhere in this recipe.

A `#N` reference is checked against BOTH the issue list and the PR list —
GitHub shares one number sequence between them, so checking only one would
misfire on a perfectly good reference to a merged PR, exactly the
crying-wolf failure Ogun's law calls fatal. A cross-repo reference
(`owner/repo#N`) is never even extracted as a candidate — that names a
different repo's own number space on purpose, a seam for a recipe watching
*that* repo, not a gap in this one. See `recipe.json`'s `confidence_notes`
for the full reasoning behind the flat 0.8 score.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src:../RECIPES/dangling-issue-reference uv run python ../RECIPES/dangling-issue-reference/detector.py
```

It finds one real gap in its own fixture (a commit that says "see #99 for
context" when neither issue nor PR #99 exists, confidence 0.8) and
correctly excludes two references that DO resolve (#12, an open issue;
#15, a closed one — existing is what matters, not open-vs-closed), while a
cross-repo reference (`arcadeai/gasstation#42`) and a commit with no
reference at all never become candidates in the first place.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/dangling-issue-reference/recipe.json
```
