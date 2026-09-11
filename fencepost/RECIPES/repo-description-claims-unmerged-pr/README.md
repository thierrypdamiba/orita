# repo-description-claims-unmerged-pr

The hundred-tenth real recipe (ROADMAP.md #1408). The fifth and last leg
opened on this surface, alongside
[`../repo-description-dangling-reference/`](../repo-description-dangling-reference/)
(the tenth leg of the dangling-reference family),
[`../repo-description-claims-unfixed-issue/`](../repo-description-claims-unfixed-issue/)
(the hundred-seventh),
[`../repo-description-claims-dangling-milestone/`](../repo-description-claims-dangling-milestone/)
(the hundred-eighth), and
[`../repo-description-claims-open-milestone/`](../repo-description-claims-open-milestone/)
(the hundred-ninth, whose own docstring flagged this leg as the last one
missing). With this recipe shipped, `repo-description` now carries every
`claims-X` leg the `readme`, `release`, and `tweet` surfaces already
carry.

**The seam it watches:** the repository's own one-line description — the
text GitHub shows in search results, in a fork listing, and above the
fold on the repo's own homepage, before README.md ever loads — names a
ships/includes/merges/via #N claim about a pull request, but the named PR
never actually merged. Fourteen other permanent public text surfaces
already carry this exact `claims-unmerged-pr` leg
([`../readme-claims-unmerged-pr/`](../readme-claims-unmerged-pr/),
[`../release-claims-unmerged-pr/`](../release-claims-unmerged-pr/),
[`../tweet-claims-unmerged-pr/`](../tweet-claims-unmerged-pr/), and
eleven more) — the repo description had never been checked for this
claim shape. Two fixtures, no live account —
[`../../fixtures/repo_description_claims_unmerged_pr/repository.json`](../../fixtures/repo_description_claims_unmerged_pr/repository.json)
and
[`../../fixtures/repo_description_claims_unmerged_pr/pulls.json`](../../fixtures/repo_description_claims_unmerged_pr/pulls.json)
— shaped like what `GetRepository` and `ListPullRequests` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table under
the `github` row. No new scope is asked for anywhere in this recipe.

Deliberately reuses `seam_engine.pr_claims.claimed_pr_numbers` verbatim —
the same shared grammar every other `claims-unmerged-pr` sibling already
imports — rather than a fifteenth independently retyped copy of the
identical pattern. Also reuses `repo-description-claims-open-milestone`'s
own `load_description` shape verbatim (a `GetRepository` whole-file read,
`description` may be JSON `null`) rather than a second, slightly
different copy of that loader drifting apart from its sibling.

Confidence is flat 0.85, NOT age-gated — mirroring
`repo-description-claims-open-milestone`'s and `repo-description-claims-
unfixed-issue`'s own bar and reasoning exactly: a live `GetRepository`
read carries no staleness window and no race, so a claim it currently
makes and the PR's currently-unmerged state are both true at the same
instant the scan runs. See `recipe.json`'s `confidence_notes` for the
full reasoning.

A repository carrying no description at all, or one with no
ships/includes/merges/via #N claim phrase, is excluded outright, named
not hidden. A claimed PR that does not exist at all is excluded too —
that broken reference is `repo-description-dangling-reference`'s own
seam, not this one's. A claimed PR that is already merged is excluded as
well — the claim was simply true.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/repo-description-claims-unmerged-pr/detector.py
```

The shipped fixture elects the primary gap for real:

```json
{
  "slug": "repo-description-claims-unmerged-pr-901",
  "headline": "The repo description claims #901 shipped, but #901 never merged",
  "confidence": 0.85
}
```

...and correctly excludes #902 (a real, merged PR — the claim was simply
true).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/repo-description-claims-unmerged-pr/recipe.json
```
