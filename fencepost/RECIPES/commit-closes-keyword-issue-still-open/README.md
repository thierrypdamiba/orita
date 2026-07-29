# commit-closes-keyword-issue-still-open

The eighth real recipe. [`merged-pr-issue-still-open`](../merged-pr-issue-still-open/)
and [`issue-closed-pr-still-open`](../issue-closed-pr-still-open/) both watch
a *pull request's* own closing-keyword promise -- one for the merged-but-
didn't-close case, one for the mirror. Neither watches the trigger GitHub
actually fires most often on *this repository*: a commit pushed straight to
`main`, no PR at all, carrying a real closing keyword.

**The seam it watches:** a commit already on the default branch names a
closing keyword (`closes #N` / `fixes #N` / `resolves #N`, present OR past
tense -- `closed #N` and `fixed #N` close on push exactly as their
present-tense siblings do, per `tools/closing_keyword_guard.py`'s own
grammar, task 184's real incident) for an issue that is still open well
after the commit landed. GitHub's auto-close trigger fires on *any* commit
that reaches the default branch, merged-PR or direct push alike -- this
town's own commits are almost all the second kind
(`git -c user.name="<God>" ...`, straight to `main`), which is exactly the
shape neither existing PR-based recipe was ever built to see. Two
fixtures, no live account --
[`../../fixtures/commit_closes_keyword_issue_still_open/commits.json`](../../fixtures/commit_closes_keyword_issue_still_open/commits.json)
and
[`.../issues.json`](../../fixtures/commit_closes_keyword_issue_still_open/issues.json)
-- shaped like what `ListRepoCommits`/`ListIssues` would actually return.
Both scopes already sit on `SCOPES.md`'s cleared oath table. No new scope
is asked for anywhere in this recipe.

A commit naming a closing keyword for an issue number that does not exist
in the repo at all is excluded, not surfaced -- that broken link is
[`dangling-issue-reference`](../dangling-issue-reference/)'s seam, not this
one's. A commit using the present-participle phrasing ("closing #N") never
matches at all, proving live that Iron Rule #8's own prescribed safe form
actually is safe, not just recommended.

Confidence is age-gated: under 24 hours since the commit landed scores 0.5
(below the 0.70 bar, weighed in the tail not hidden); at or past 24 hours it
scores 0.85. See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/commit-closes-keyword-issue-still-open/detector.py
```

Or through the discovery/validation path a stranger's PR is checked
against:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python -m seam_engine.recipes discover
PYTHONPATH=src uv run python -m seam_engine.recipes check ../RECIPES/commit-closes-keyword-issue-still-open/recipe.json
```
