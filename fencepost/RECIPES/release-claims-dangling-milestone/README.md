# release-claims-dangling-milestone

The eighty-ninth real recipe.

**The seam it watches:** a GitHub release's own body invokes a real
`milestone #N` claim phrase —
[`seam_engine.milestone_claims.claimed_milestone_numbers`](../../seam_engine/src/seam_engine/milestone_claims.py),
the same grammar every `*-claims-*-milestone` sibling already imports —
but no milestone with that number exists at all.
[`../release-claims-open-milestone/`](../release-claims-open-milestone/)
(the sixteenth real recipe) drew this line for the whole family in its
own docstring: a claimed milestone number that names no real milestone at
all was excluded there, named not hidden, "a broken reference is
`dangling-issue-reference`'s own seam (over issues/PRs), not this one's
(over milestones)." This recipe is that seam, on the fourth of the five
sources task 870 named and left open — the release-sourced sibling of
[`../commit-claims-dangling-milestone/`](../commit-claims-dangling-milestone/),
[`../issue-comment-claims-dangling-milestone/`](../issue-comment-claims-dangling-milestone/),
[`../review-comment-claims-dangling-milestone/`](../review-comment-claims-dangling-milestone/),
[`../slack-message-claims-dangling-milestone/`](../slack-message-claims-dangling-milestone/),
[`../linear-comment-claims-dangling-milestone/`](../linear-comment-claims-dangling-milestone/),
[`../mention-claims-dangling-milestone/`](../mention-claims-dangling-milestone/),
[`../milestone-claims-dangling-milestone/`](../milestone-claims-dangling-milestone/),
and
[`../readme-claims-dangling-milestone/`](../readme-claims-dangling-milestone/),
which closed the identical seam for a commit message, an issue/PR
timeline comment, a pull request's own inline review comment, a Slack
channel message, a Linear issue comment, a mortal's own X mention, a
milestone's own description, and README.md respectively.

Task 870's own README named the four cells still open at the time
(`milestone`, `readme`, `release`, `tweet`); tasks 871 and 872 closed
`milestone` and `readme`. This recipe closes `release`, the fourth of the
five. `tweet` remains open, correctly, for a future hour.

It is not
[`../release-note-dangling-reference/`](../release-note-dangling-reference/)'s
seam wearing a new name. That recipe (the twenty-third) already reads a
release's own body — but strictly for a bare `#N` against GitHub's shared
issue/PR number sequence, and it never opens `ListMilestones` at all. A
milestone lives in its own, separate number space, so a claimed
`milestone #N` that happens to resolve as a real *issue* number would
read as perfectly fine there while naming no milestone whatsoever;
conflating the two spaces would misfire exactly the way Ògún's law calls
fatal. It is also not
[`../release-claims-open-milestone/`](../release-claims-open-milestone/):
that recipe and this one are exact inverses on one surface, and the
boundary is the whole point. There, a claimed number resolving to no real
milestone is *excluded* at 0.0 and a claim contradicted by a still-open
milestone is surfaced; here, the resolution failure *is* the seam and a
claimed number that does resolve is excluded at 0.0, open or closed
alike.

A release's body is GitHub's own permanent, published-once public
record — the same "never gets a second edit pass" property
`release-note-dangling-reference`'s own confidence note already relies
on, and the same durability `commit-claims-dangling-milestone` already
guards against in a commit message.

Two fixtures, no live account —
[`../../fixtures/release_claims_dangling_milestone/releases.json`](../../fixtures/release_claims_dangling_milestone/releases.json)
and
[`../../fixtures/release_claims_dangling_milestone/milestones.json`](../../fixtures/release_claims_dangling_milestone/milestones.json)
— shaped like what repeated live `GetLatestRelease` reads over time and a
single live `ListMilestones` call would actually return, the same
"recent-releases history" convention
[`../release-claims-open-milestone/`](../release-claims-open-milestone/)
already established. Both scopes already sit on `SCOPES.md`'s cleared
oath table; no new scope is asked for anywhere in this recipe, and the
`toolkit` stays `github`-only. `source: "fixture"` in `run_recipe_scan`'s
own output is the honest WIP marker; only the fixture loaders swap for
real calls the day a live connected account backs them.

Confidence is flat (0.8), not age-gated, mirroring every prior
claims-dangling-milestone sibling's own reasoning. `release-claims-open-
milestone`'s 24-hour publish-age grace bar does not apply here: that
recipe age-gates because an OPEN milestone could still close at any
moment, so a fresh claim about it might just be a race the milestone
tracker hasn't caught up to yet — but a milestone number that does not
exist right now will not spontaneously start existing later, so no grace
period would mean anything here. See `recipe.json`'s `confidence_notes`
for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/release-claims-dangling-milestone/detector.py
```

Against the shipped fixtures it finds one real gap as the elected primary
(`rel-9105`'s claim about milestone #9401, confidence 0.8 — no such
milestone exists; the same claim written twice in that release's body is
de-duplicated to one candidate, not two), while correctly excluding a
release naming milestone #7 (real and closed — no seam) and a release
naming milestone #12 (real and open — no seam either, that's
`release-claims-open-milestone`'s own remit). Two more releases carry no
milestone claim at all: one mentions a bare `#9405` with no claim phrase
nearby — `release-note-dangling-reference`'s number space, not this
one's — and one sits behind an explicit denial ("We have not hit
milestone #9406 this cycle"), dropped by the shared grammar's own
negation check.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../RECIPES/release-claims-dangling-milestone/recipe.json
```
