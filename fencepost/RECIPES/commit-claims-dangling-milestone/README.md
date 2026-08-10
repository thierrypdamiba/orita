# commit-claims-dangling-milestone

The seventy-sixth real recipe.

**The seam it watches:** a commit's own message invokes a real
`milestone #N` claim phrase —
[`seam_engine.milestone_claims.claimed_milestone_numbers`](../../seam_engine/src/seam_engine/milestone_claims.py),
the same grammar eleven prior recipes already import — but no milestone
with that number exists at all.
[`../commit-claims-open-milestone/`](../commit-claims-open-milestone/)
(the sixty-sixth real recipe) drew this exact line in its own docstring:
a claimed milestone number that names no real milestone at all was
excluded there, named not hidden, "as belonging to a future
milestone-side dangling-reference recipe, not this one." This recipe is
that seam.

It is not [`../dangling-issue-reference/`](../dangling-issue-reference/)'s
seam wearing a new name. That recipe watches a bare `#N` against GitHub's
shared issue/PR number sequence and never opens `ListMilestones` at all —
a milestone lives in its own, separate number space, so a `#N` that
resolves cleanly as a real issue could still be a dangling *milestone*
claim, and conflating the two spaces would misfire exactly the way
Ògún's law calls fatal. It is also not
[`../milestone-body-dangling-reference/`](../milestone-body-dangling-reference/)'s
seam — that recipe reads a real milestone's own description for a
dangling issue/PR reference, the reverse direction of the claim this one
reads (a commit claiming a milestone number, not a milestone's own body
claiming an issue number).

Two fixtures, no live account —
[`../../fixtures/commit_claims_dangling_milestone/commits.json`](../../fixtures/commit_claims_dangling_milestone/commits.json)
and
[`../../fixtures/commit_claims_dangling_milestone/milestones.json`](../../fixtures/commit_claims_dangling_milestone/milestones.json)
— shaped like what `ListRepoCommits` and `ListMilestones` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table under
the `github` row. No new scope is asked for anywhere in this recipe.

A claimed milestone number that DOES resolve to a real milestone is
excluded here, named not hidden, whether that milestone is open or
closed — whether the claim itself is true is
`commit-claims-open-milestone`'s own seam, not this one's. A commit with
no `milestone #N` claim phrase at all (a bare `#N` aside, or no reference
at all) never becomes a candidate either.

Confidence is flat (0.8), not age-gated, mirroring
`dangling-issue-reference`'s own reasoning rather than
`commit-claims-open-milestone`'s 24-hour bar: an open milestone could
close at any moment, so a fresh claim about it might just be a race — but
a milestone number that does not exist right now will not spontaneously
start existing later, so there is no grace period that means anything
here. See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/commit-claims-dangling-milestone/detector.py
```

Against the shipped fixture it finds one real gap as the elected primary
(commit `e1f22a3`'s claim about milestone #8302, confidence 0.8 — no such
milestone exists; a duplicate claim inside the same message is
de-duplicated to one candidate, not two), while correctly excluding
commit `f2a33b4` (claims milestone #8301, which is real — no seam here,
that's `commit-claims-open-milestone`'s own remit), commit `a3b44c5` (a
bare `#8304` aside, no `milestone #N` claim phrase at all), and commit
`b4c55d6` (claims milestone #8301, which is real, alongside a bare
`#8399` aside that is never extracted as a claim).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/commit-claims-dangling-milestone/recipe.json
```
