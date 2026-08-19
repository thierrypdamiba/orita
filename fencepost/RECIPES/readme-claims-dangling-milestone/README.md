# readme-claims-dangling-milestone

The eighty-eighth real recipe.

**The seam it watches:** README.md's own text invokes a real
`milestone #N` claim phrase —
[`seam_engine.milestone_claims.claimed_milestone_numbers`](../../seam_engine/src/seam_engine/milestone_claims.py),
the same grammar every `*-claims-*-milestone` sibling already imports —
but no milestone with that number exists at all.
[`../milestone-claims-open-milestone/`](../milestone-claims-open-milestone/)
(the fifty-first real recipe) drew this line for the whole family in its
own docstring: a claimed milestone number that names no real milestone at
all was excluded there, named not hidden, "a broken reference is
`milestone-body-dangling-reference`'s own seam, not this one's." This
recipe is that seam, on the third of the five sources task 870 named and
left open — the README-sourced sibling of
[`../commit-claims-dangling-milestone/`](../commit-claims-dangling-milestone/),
[`../issue-comment-claims-dangling-milestone/`](../issue-comment-claims-dangling-milestone/),
[`../review-comment-claims-dangling-milestone/`](../review-comment-claims-dangling-milestone/),
[`../slack-message-claims-dangling-milestone/`](../slack-message-claims-dangling-milestone/),
[`../linear-comment-claims-dangling-milestone/`](../linear-comment-claims-dangling-milestone/),
[`../mention-claims-dangling-milestone/`](../mention-claims-dangling-milestone/),
and
[`../milestone-claims-dangling-milestone/`](../milestone-claims-dangling-milestone/),
which closed the identical seam for a commit message, an issue/PR
timeline comment, a pull request's own inline review comment, a Slack
channel message, a Linear issue comment, a mortal's own X mention, and a
milestone's own description respectively.

Task 870's own README named the four cells still open (`milestone`,
`readme`, `release`, `tweet`) rather than leaving them silently implied;
task 871 closed `milestone`. This recipe closes `readme`, the third of
the five. `release` and `tweet` remain open, correctly, for a future
hour.

It is not
[`../readme-dangling-reference/`](../readme-dangling-reference/)'s seam
wearing a new name. That recipe (the fifty-seventh) already reads
README.md — but strictly for a bare `#N` against GitHub's shared issue/PR
number sequence, and it never opens `ListMilestones` at all. A milestone
lives in its own, separate number space, so a claimed `milestone #N` that
happens to resolve as a real *issue* number would read as perfectly fine
there while naming no milestone whatsoever; conflating the two spaces
would misfire exactly the way Ògún's law calls fatal. It is also not
[`../readme-claims-open-milestone/`](../readme-claims-open-milestone/):
that recipe and this one are exact inverses on one surface, and the
boundary is the whole point. There, a claimed number resolving to no real
milestone is *excluded* at 0.0 and a claim contradicted by a still-open
milestone is surfaced; here, the resolution failure *is* the seam and a
claimed number that does resolve is excluded at 0.0, open or closed
alike.

README earned this door before most surfaces did and did not get it: it
is the repo's own front door, the first thing a stranger reads, and the
least often reproofread.

Two fixtures, no live account —
[`../../fixtures/readme_claims_dangling_milestone/readme.json`](../../fixtures/readme_claims_dangling_milestone/readme.json)
and
[`../../fixtures/readme_claims_dangling_milestone/milestones.json`](../../fixtures/readme_claims_dangling_milestone/milestones.json)
— shaped like what a single live `GetFileContents` read of this repo's own
README and a single live `ListMilestones` call would actually return, the
same two-loader shape
[`../readme-claims-open-milestone/`](../readme-claims-open-milestone/)
established for this surface. Both scopes already sit on `SCOPES.md`'s
cleared oath table; no new scope is asked for anywhere in this recipe,
and the `toolkit` stays `github`-only. `source: "fixture"` in
`run_recipe_scan`'s own output is the honest WIP marker; only the fixture
loaders swap for real calls the day a live connected account backs them.

No self-claim exclusion appears here, and the absence is deliberate
rather than an oversight: the milestone-sourced sibling needs one because
a milestone's own description can name its own number, but README.md
carries no milestone number of its own, so there is no second record for
it to collapse into. A README with no `milestone #N` claim phrase at all
is named as an exclusion rather than returning two silent empties.

Confidence is flat (0.8), not age-gated, mirroring every prior
claims-dangling-milestone sibling's own reasoning — and landing where
`readme-claims-open-milestone`'s own no-age-gate note lands by a second
road. A `GetFileContents` read returns current text, not a change
history, so there is no per-claim timestamp to weigh a staleness window
against in the first place; and even if there were, a milestone number
that does not exist right now will not spontaneously start existing
later, so no grace period would mean anything here. See `recipe.json`'s
`confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/readme-claims-dangling-milestone/detector.py
```

Against the shipped fixtures it finds one real gap as the elected primary
(README.md's claim about milestone #204, confidence 0.8 — no such
milestone exists; the same claim written twice in README.md is
de-duplicated to one candidate, not two), while correctly excluding
milestone #7 (real and closed — no seam) and milestone #12 (real and
open — no seam either, that's `readme-claims-open-milestone`'s own
remit). Two more numbers in the same README are never extracted as
claims at all: `milestone #55` sits behind an explicit denial ("We have
not hit milestone #55 this cycle"), dropped by the shared grammar's own
negation check, and `#813` is a bare issue reference with no claim phrase
anywhere near it — `readme-dangling-reference`'s number space, not this
one's.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/readme-claims-dangling-milestone/recipe.json
```
