# repo-description-dangling-reference

The eightieth real recipe. The tenth leg of the dangling-reference family
alongside [`../dangling-issue-reference/`](../dangling-issue-reference/)
(commit messages), [`../mention-dangling-reference/`](../mention-dangling-reference/)
(X mentions), [`../release-note-dangling-reference/`](../release-note-dangling-reference/)
(release notes), [`../issue-body-dangling-reference/`](../issue-body-dangling-reference/)
(issue/PR bodies), [`../milestone-body-dangling-reference/`](../milestone-body-dangling-reference/)
(milestone descriptions), [`../own-tweet-dangling-reference/`](../own-tweet-dangling-reference/)
(the town's own tweets), [`../review-comment-dangling-reference/`](../review-comment-dangling-reference/)
(inline review comments), [`../issue-comment-dangling-reference/`](../issue-comment-dangling-reference/)
(timeline comments), and [`../readme-dangling-reference/`](../readme-dangling-reference/)
(README.md) — the first to read `GetRepository`'s own `description` field
at all.

**The seam it watches:** the repository's one-line description — the text
GitHub shows in search results, in a fork listing, and above the fold on
the repo's own homepage, before README.md ever loads — counts on an issue
or pull request that isn't actually there. A maintainer types the
description once, early, often to summarize "what shipped" or "see #N for
the plan," and then almost never revisits it, unlike a README a stranger
actually opens and skims. Nothing on GitHub's side ever checks that prose
against the issue/PR tracker's own truth. Three fixtures, no live account —
[`../../fixtures/repo_description_dangling_reference/repository.json`](../../fixtures/repo_description_dangling_reference/repository.json),
[`../../fixtures/repo_description_dangling_reference/issues.json`](../../fixtures/repo_description_dangling_reference/issues.json),
and
[`../../fixtures/repo_description_dangling_reference/pulls.json`](../../fixtures/repo_description_dangling_reference/pulls.json)
— shaped like what `GetRepository`, `ListIssues`, and `ListPullRequests`
would actually return. All three scopes already sit on `SCOPES.md`'s
cleared oath table under the `github` row. No new scope is asked for
anywhere in this recipe.

Confidence is flat 0.85, mirroring `readme-dangling-reference`'s own bar
and reasoning exactly — a live read carries no staleness uncertainty, so
there is no timestamp to weigh an age-gate against. See `recipe.json`'s
`confidence_notes` for the full reasoning.

A repository carrying no description at all (GitHub allows a `null` here)
is excluded outright, named not hidden — not treated as a reference-free
false candidate.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/repo-description-dangling-reference/detector.py
```

The shipped fixture elects the primary gap for real:

```json
{
  "slug": "repo-description-dangling-reference-4001",
  "headline": "The repo description references #4001, but no issue or PR #4001 exists here",
  "confidence": 0.85
}
```

...and correctly excludes #4 (a real open issue) and #40 (a real merged
PR) — both references hold.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/repo-description-dangling-reference/recipe.json
```
