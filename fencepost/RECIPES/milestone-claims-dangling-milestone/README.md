# milestone-claims-dangling-milestone

The eighty-seventh real recipe.

**The seam it watches:** a milestone's own description invokes a real
`milestone #N` claim phrase —
[`seam_engine.milestone_claims.claimed_milestone_numbers`](../../seam_engine/src/seam_engine/milestone_claims.py),
the same grammar every `*-claims-*-milestone` sibling already imports —
but no milestone with that number exists at all.
[`../milestone-claims-open-milestone/`](../milestone-claims-open-milestone/)
(the fifty-first real recipe) drew this exact line in its own docstring: a
claimed milestone number that names no real milestone at all was excluded
there, named not hidden, "a broken reference is
`milestone-body-dangling-reference`'s own seam, not this one's." This
recipe is that seam, on the second of the five sources task 870 named and
left open — the milestone-sourced sibling of
[`../commit-claims-dangling-milestone/`](../commit-claims-dangling-milestone/),
[`../issue-comment-claims-dangling-milestone/`](../issue-comment-claims-dangling-milestone/),
[`../review-comment-claims-dangling-milestone/`](../review-comment-claims-dangling-milestone/),
[`../slack-message-claims-dangling-milestone/`](../slack-message-claims-dangling-milestone/),
[`../linear-comment-claims-dangling-milestone/`](../linear-comment-claims-dangling-milestone/),
and
[`../mention-claims-dangling-milestone/`](../mention-claims-dangling-milestone/),
which closed the identical seam for a commit message, an issue/PR
timeline comment, a pull request's own inline review comment, a Slack
channel message, a Linear issue comment, and a mortal's own X mention
respectively.

Task 870's own README already named the remaining four open cells
(`milestone`, `readme`, `release`, `tweet`) rather than leaving them
silently implied. This recipe closes `milestone`, the second of the
four; `readme`, `release`, and `tweet` remain open, correctly, for a
future hour.

It is not
[`../milestone-body-dangling-reference/`](../milestone-body-dangling-reference/)'s
seam wearing a new name. That recipe watches a bare `#N` inside a
milestone's own description against GitHub's shared issue/PR number
sequence and never opens `ListMilestones` at all — a milestone lives in
its own, separate number space, so a `#N` that resolves cleanly as a real
issue could still be a dangling *milestone* claim, and conflating the two
spaces would misfire exactly the way Ògún's law calls fatal.

One fixture, no live account —
[`../../fixtures/milestone_claims_dangling_milestone/milestones.json`](../../fixtures/milestone_claims_dangling_milestone/milestones.json)
— shaped like what a single live `ListMilestones` read would actually
return. The same-list shape
[`../milestone-claims-open-milestone/`](../milestone-claims-open-milestone/)
already established: every milestone in the fixture plays both the
claimant role AND a possible target for some OTHER milestone's own claim.
That scope already sits on `SCOPES.md`'s cleared oath table; no new scope
is asked for anywhere in this recipe, and the `toolkit` stays
`github`-only. `source: "fixture"` in `run_recipe_scan`'s own output is
the honest WIP marker; only the fixture loader swaps for a real call the
day a live connected account backs it.

A milestone claiming ITSELF (`milestone #90` written inside milestone
#90's own description) is excluded, named not hidden — not a claim about
a second record, so no seam. A claimed milestone number that DOES
resolve to a real milestone is excluded too, whether that milestone is
open or closed — whether the claim itself is true is
`milestone-claims-open-milestone`'s own seam, not this one's. A
milestone with no `milestone #N` claim phrase at all (a bare `#N` aside),
or no description at all, never becomes a candidate either.

Confidence is flat (0.8), not age-gated, mirroring every prior
claims-dangling-milestone sibling's own reasoning rather than
`milestone-claims-open-milestone`'s 24-hour edit-grace bar: an open
milestone could close at any moment, so a fresh claim about it might just
be a race the description hasn't caught up to yet — but a milestone
number that does not exist right now will not spontaneously start
existing later, so there is no grace period that means anything here.
See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/milestone-claims-dangling-milestone/detector.py
```

Against the shipped fixture it finds one real gap as the elected primary
(milestone #90's claim about milestone #9901, confidence 0.8 — no such
milestone exists; the same claim written twice in #90's own description is
de-duplicated to one candidate, not two), while correctly excluding
milestone #91 (claims milestone #92, which is real and open — no seam,
that's `milestone-claims-open-milestone`'s own remit), milestone #92
(claims milestone #93, which is real and closed), milestone #96 (claims
itself — no second record, no seam), and milestone #97 (claims milestone
#92, which is real and open, alongside a bare `#9999` aside that is never
extracted as a claim). Milestones #93, #94, and #95 carry no description,
no claim phrase, or no `milestone #N` phrase at all — never examined as
claimants.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/milestone-claims-dangling-milestone/recipe.json
```
