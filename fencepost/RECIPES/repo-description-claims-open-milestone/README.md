# repo-description-claims-open-milestone

The hundred-ninth real recipe (ROADMAP.md #1407). The fourth leg opened
on this surface, alongside
[`../repo-description-dangling-reference/`](../repo-description-dangling-reference/)
(the tenth leg of the dangling-reference family),
[`../repo-description-claims-unfixed-issue/`](../repo-description-claims-unfixed-issue/)
(the hundred-seventh) and
[`../repo-description-claims-dangling-milestone/`](../repo-description-claims-dangling-milestone/)
(the hundred-eighth).

**The seam it watches:** the repository's own one-line description — the
text GitHub shows in search results, in a fork listing, and above the
fold on the repo's own homepage, before README.md ever loads — names a
"milestone #N shipped" claim phrase, but the named milestone is still
open. Thirteen other permanent public text surfaces already carry this
exact `claims-open-milestone` leg
([`../readme-claims-open-milestone/`](../readme-claims-open-milestone/),
[`../release-claims-open-milestone/`](../release-claims-open-milestone/),
[`../tweet-claims-open-milestone/`](../tweet-claims-open-milestone/), and
ten more) — the repo description had never been checked for this claim
shape. Two fixtures, no live account —
[`../../fixtures/repo_description_claims_open_milestone/repository.json`](../../fixtures/repo_description_claims_open_milestone/repository.json)
and
[`../../fixtures/repo_description_claims_open_milestone/milestones.json`](../../fixtures/repo_description_claims_open_milestone/milestones.json)
— shaped like what `GetRepository` and `ListMilestones` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table under
the `github` row. No new scope is asked for anywhere in this recipe.

Deliberately reuses `seam_engine.milestone_claims.claimed_milestone_numbers`
verbatim — the same shared grammar `repo-description-claims-dangling-
milestone` already imports — rather than a fourteenth independently
retyped copy of the identical pattern.

Confidence is flat 0.85, NOT age-gated — mirroring
`repo-description-claims-unfixed-issue`'s own bar and reasoning exactly:
a live `GetRepository` read carries no staleness window and no race, so
a claim it currently makes and the milestone's currently-open state are
both true at the same instant the scan runs. See `recipe.json`'s
`confidence_notes` for the full reasoning.

A repository carrying no description at all, or one with no
"milestone #N" claim phrase, is excluded outright, named not hidden. A
claimed milestone that does not exist at all is excluded too — that
broken reference is `repo-description-claims-dangling-milestone`'s own
seam, not this one's. A claimed milestone that is already closed is
excluded as well — the claim was simply true.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/repo-description-claims-open-milestone/detector.py
```

The shipped fixture elects the primary gap for real:

```json
{
  "slug": "repo-description-claims-open-milestone-12",
  "headline": "The repo description claims milestone #12 shipped, but it's still open",
  "confidence": 0.85
}
```

...and correctly excludes milestone #7 (a real, closed milestone — the
claim was simply true).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/repo-description-claims-open-milestone/recipe.json
```
