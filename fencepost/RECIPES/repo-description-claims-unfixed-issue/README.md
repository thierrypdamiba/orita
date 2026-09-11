# repo-description-claims-unfixed-issue

The hundred-seventh real recipe (ROADMAP.md #1405). The issue-side twin of
[`../repo-description-dangling-reference/`](../repo-description-dangling-reference/)
(the tenth leg of the dangling-reference family), applied to the sibling
`claims-unfixed-issue` shape instead: not "does `#N` exist at all" but
"the description claims `#N` is FIXED, and it is not."

**The seam it watches:** the repository's own one-line description — the
text GitHub shows in search results, in a fork listing, and above the
fold on the repo's own homepage, before README.md ever loads — names a
real closing keyword against an issue ("fixes #N", "closes #N", "resolves
#N", both tenses), but the named issue is still open. Every other
permanent public text surface already carries this leg
([`../readme-claims-unfixed-issue/`](../readme-claims-unfixed-issue/),
[`../release-claims-unfixed-issue/`](../release-claims-unfixed-issue/),
[`../tweet-claims-unfixed-issue/`](../tweet-claims-unfixed-issue/),
[`../milestone-claims-unfixed-issue/`](../milestone-claims-unfixed-issue/),
and seven more) — the repo description had only ever been checked for a
DANGLING reference, never for this claim shape. Two fixtures, no live
account —
[`../../fixtures/repo_description_claims_unfixed_issue/repository.json`](../../fixtures/repo_description_claims_unfixed_issue/repository.json)
and
[`../../fixtures/repo_description_claims_unfixed_issue/issues.json`](../../fixtures/repo_description_claims_unfixed_issue/issues.json)
— shaped like what `GetRepository` and `ListIssues` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table under
the `github` row. No new scope is asked for anywhere in this recipe.

Confidence is flat 0.85, mirroring `repo-description-dangling-reference`'s
own bar and reasoning exactly — a live read carries no staleness
uncertainty, so there is no timestamp to weigh an age-gate against. See
`recipe.json`'s `confidence_notes` for the full reasoning.

A repository carrying no description at all, or one with no closing-
keyword claim, is excluded outright, named not hidden. A claimed issue
that does not exist at all is excluded too — that is
`repo-description-dangling-reference`'s own seam. A claimed issue that IS
closed is excluded — the claim was simply true.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/repo-description-claims-unfixed-issue/detector.py
```

The shipped fixture elects the primary gap for real:

```json
{
  "slug": "repo-description-claims-unfixed-issue-4",
  "headline": "The repo description claims #4 fixed, but #4 is still open",
  "confidence": 0.85
}
```

...and correctly excludes #201 (a real closed issue — the claim holds)
and #299 (no such issue exists here).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/repo-description-claims-unfixed-issue/recipe.json
```
