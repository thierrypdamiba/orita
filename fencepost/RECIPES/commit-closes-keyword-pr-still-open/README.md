# commit-closes-keyword-pr-still-open

The twenty-fifth real recipe. [`commit-closes-keyword-issue-still-open`](../commit-closes-keyword-issue-still-open/)
(task 388, the eighth real recipe) watches a commit already on the default
branch naming a real GitHub closing keyword for an *issue* that stays
open -- but its own docstring scopes itself deliberately: "this recipe
explicitly only checks issue numbers." This recipe is the PR-side twin,
built the same way [`duplicate-pr-still-open`](../duplicate-pr-still-open/)
(task 400) was built as [`duplicate-issue-still-open`](../duplicate-issue-still-open/)'s
own twin.

**The seam it watches:** a commit already on the default branch names a
closing keyword (`closes #N` / `fixes #N` / `resolves #N`, present OR past
tense) for a **pull request** number, and that PR is still open well after
the commit landed. GitHub's real auto-close trigger does not care which
record type the number resolves to -- a commit carrying a closing keyword
fires the identical mechanism whether `#N` is an issue or a PR (against a
PR the same keyword is GitHub's documented auto-merge-adjacent trigger:
the PR is expected to close, one way or another, the moment the
referencing commit reaches the default branch). Neither the issue-side
sibling above, nor any duplicate/milestone/release recipe in this
`RECIPES/` tree, was ever built to watch this half of the seam. Two
fixtures, no live account --
[`../../fixtures/commit_closes_keyword_pr_still_open/commits.json`](../../fixtures/commit_closes_keyword_pr_still_open/commits.json)
and
[`.../prs.json`](../../fixtures/commit_closes_keyword_pr_still_open/prs.json)
-- shaped like what `ListRepoCommits`/`ListPullRequests` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table. No new
scope is asked for anywhere in this recipe.

`CLOSING_KEYWORD_RE` is imported from
[`seam_engine.closing_keywords`](../../seam_engine/src/seam_engine/closing_keywords.py)
-- the one real source three prior recipes already bind to -- rather than
retyped a sixth time. `tools/duplicate_regex_check.py` exists precisely to
catch a recipe that promises reuse in a docstring but retypes the pattern
anyway; this recipe imports for real.

A commit naming a closing keyword for a PR number that does not exist in
this fixture's PR set at all is excluded, not surfaced -- a broken link,
not a broken promise. A commit naming an already-resolved PR -- merged, OR
closed without merging -- is excluded too: either way the promise already
held. A commit using the present-participle phrasing ("closing #N") never
matches at all, proving live (again) that Iron Rule #8's own prescribed
safe form actually is safe, on the PR side exactly as it already was on the
issue side.

Confidence is age-gated: under 24 hours since the commit landed scores 0.5
(below the 0.70 bar, weighed in the tail not hidden); at or past 24 hours it
scores 0.85 -- the identical bar `commit-closes-keyword-issue-still-open`
uses, kept rather than reinvented. See `recipe.json`'s `confidence_notes`
for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/commit-closes-keyword-pr-still-open/detector.py
```

Or through the discovery/validation path a stranger's PR is checked
against:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python -m seam_engine.recipes discover
PYTHONPATH=src uv run python -m seam_engine.recipes check ../RECIPES/commit-closes-keyword-pr-still-open/recipe.json
```
