# repo-description-claims-dangling-milestone

The hundred-eighth real recipe (ROADMAP.md #1406). The milestone-side
twin of
[`../repo-description-claims-unfixed-issue/`](../repo-description-claims-unfixed-issue/)
(the hundred-seventh) and the third leg opened on this surface, alongside
[`../repo-description-dangling-reference/`](../repo-description-dangling-reference/)
(the tenth leg of the dangling-reference family, a different number
space entirely — the shared GitHub issue/PR sequence, not a milestone).

**The seam it watches:** the repository's own one-line description — the
text GitHub shows in search results, in a fork listing, and above the
fold on the repo's own homepage, before README.md ever loads — names a
"milestone #N" claim phrase, but no milestone with that number exists at
all. Every other permanent public text surface that carries a
`claims-dangling-milestone` sibling already has thirteen
([`../readme-claims-dangling-milestone/`](../readme-claims-dangling-milestone/),
[`../release-claims-dangling-milestone/`](../release-claims-dangling-milestone/),
[`../tweet-claims-dangling-milestone/`](../tweet-claims-dangling-milestone/),
and ten more) — the repo description had never been checked for this
claim shape. Two fixtures, no live account —
[`../../fixtures/repo_description_claims_dangling_milestone/repository.json`](../../fixtures/repo_description_claims_dangling_milestone/repository.json)
and
[`../../fixtures/repo_description_claims_dangling_milestone/milestones.json`](../../fixtures/repo_description_claims_dangling_milestone/milestones.json)
— shaped like what `GetRepository` and `ListMilestones` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table under
the `github` row. No new scope is asked for anywhere in this recipe.

Deliberately reuses `seam_engine.milestone_claims.claimed_milestone_numbers`
verbatim — the same shared grammar every `claims-dangling-milestone`
sibling already imports — rather than a fourteenth independently retyped
copy of the identical pattern.

Confidence is flat 0.8, mirroring every prior `claims-dangling-milestone`
sibling's own bar and reasoning exactly — a live read carries no
staleness uncertainty, and a milestone number that doesn't exist right
now won't spontaneously start existing later. See `recipe.json`'s
`confidence_notes` for the full reasoning.

A repository carrying no description at all, or one with no
"milestone #N" claim phrase, is excluded outright, named not hidden. A
claimed milestone number that resolves to a real milestone is excluded
too — open or closed, the milestone exists, so there is no dangling
reference here. No self-claim exclusion is needed: unlike a milestone's
own description (which can name its own number), a repo description
carries no milestone number of its own to collapse into.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/repo-description-claims-dangling-milestone/detector.py
```

The shipped fixture elects the primary gap for real:

```json
{
  "slug": "repo-description-claims-dangling-milestone-42",
  "headline": "The repo description claims milestone #42, which doesn't exist",
  "confidence": 0.8
}
```

...and correctly excludes milestone #7 (a real, closed milestone — the
claim resolves, so there is no dangling reference).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/repo-description-claims-dangling-milestone/recipe.json
```
