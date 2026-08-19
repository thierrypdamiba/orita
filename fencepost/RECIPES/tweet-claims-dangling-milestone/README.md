# tweet-claims-dangling-milestone

The ninetieth real recipe.

**The seam it watches:** a tweet from the connected X account invokes a
real `milestone #N` claim phrase —
[`seam_engine.milestone_claims.claimed_milestone_numbers`](../../seam_engine/src/seam_engine/milestone_claims.py),
the same grammar every `*-claims-*-milestone` sibling already imports —
but no milestone with that number exists at all.
[`../tweet-claims-open-milestone/`](../tweet-claims-open-milestone/) drew
this line for the whole family in its own docstring: a claimed milestone
number that names no real milestone at all was excluded there, named not
hidden, "a broken reference is `own-tweet-dangling-reference`'s own seam
(over issues/PRs), not this one's (over milestones)." This recipe is that
seam, on the fifth and last of the five sources task 870 named — the
tweet-sourced sibling of
[`../commit-claims-dangling-milestone/`](../commit-claims-dangling-milestone/),
[`../issue-comment-claims-dangling-milestone/`](../issue-comment-claims-dangling-milestone/),
[`../review-comment-claims-dangling-milestone/`](../review-comment-claims-dangling-milestone/),
[`../slack-message-claims-dangling-milestone/`](../slack-message-claims-dangling-milestone/),
[`../linear-comment-claims-dangling-milestone/`](../linear-comment-claims-dangling-milestone/),
[`../mention-claims-dangling-milestone/`](../mention-claims-dangling-milestone/),
[`../milestone-claims-dangling-milestone/`](../milestone-claims-dangling-milestone/),
[`../readme-claims-dangling-milestone/`](../readme-claims-dangling-milestone/),
and
[`../release-claims-dangling-milestone/`](../release-claims-dangling-milestone/),
which closed the identical seam for a commit message, an issue/PR
timeline comment, a pull request's own inline review comment, a Slack
channel message, a Linear issue comment, a mortal's own X mention, a
milestone's own description, README.md, and a GitHub release's own body
respectively.

Task 870's own README named five cells open at the time (`mention`,
`milestone`, `readme`, `release`, `tweet`) and closed the first itself.
Tasks 871, 872, and 873 closed `milestone`, `readme`, and `release` in
order. This recipe closes `tweet`, the fifth and last — the whole family
task 870 opened is now fully saturated across every surface the town
watches for a `milestone #N` claim.

It is not
[`../own-tweet-dangling-reference/`](../own-tweet-dangling-reference/)'s
seam wearing a new name. That recipe (the twenty-fourth) already reads
the connected account's own tweets — but strictly for a bare `#N` against
GitHub's shared issue/PR number sequence, and it never opens
`ListMilestones` at all. A milestone lives in its own, separate number
space, so a claimed `milestone #N` that happens to resolve as a real
*issue* number would read as perfectly fine there while naming no
milestone whatsoever; conflating the two spaces would misfire exactly the
way Ògún's law calls fatal. It is also not
[`../tweet-claims-open-milestone/`](../tweet-claims-open-milestone/):
that recipe and this one are exact inverses on one surface, and the
boundary is the whole point. There, a claimed number resolving to no real
milestone is *excluded* at 0.0 and a claim contradicted by a still-open
milestone is surfaced; here, the resolution failure *is* the seam and a
claimed number that does resolve is excluded at 0.0, open or closed
alike.

A tweet is X's own permanent, append-only public record — the same
"never gets a second edit pass" property `own-tweet-dangling-reference`'s
own confidence note already relies on, and the same durability
`commit-claims-dangling-milestone` and `release-claims-dangling-milestone`
already guard against in a commit message and a release body.

Two fixtures, no live account —
[`../../fixtures/tweet_claims_dangling_milestone/tweets.json`](../../fixtures/tweet_claims_dangling_milestone/tweets.json)
and
[`../../fixtures/tweet_claims_dangling_milestone/milestones.json`](../../fixtures/tweet_claims_dangling_milestone/milestones.json)
— shaped like what repeated live `GetUserTweets` reads over time and a
single live `ListMilestones` call would actually return, the same
"recent-tweets history" convention
[`../tweet-claims-unmerged-pr/`](../tweet-claims-unmerged-pr/) already
established. Both scopes already sit on `SCOPES.md`'s cleared oath table;
no new scope is asked for anywhere in this recipe, and the `toolkit` is
`x+github` (a real cross-toolkit pair — a milestone lives on GitHub, but
the claim about it lives on X). `source: "fixture"` in `run_recipe_scan`'s
own output is the honest WIP marker; only the fixture loaders swap for
real calls the day a live connected account backs them.

Confidence is flat (0.8), not age-gated, mirroring every prior
claims-dangling-milestone sibling's own reasoning. `tweet-claims-open-
milestone`'s 24-hour publish-age grace bar does not apply here: that
recipe age-gates because a claimed target could still change state at any
moment, so a fresh claim about it might just be a race the tracker hasn't
caught up to yet — but a milestone number that does not exist right now
will not spontaneously start existing later, so no grace period would
mean anything here. See `recipe.json`'s `confidence_notes` for the full
reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/tweet-claims-dangling-milestone/detector.py
```

Against the shipped fixtures it finds one real gap as the elected primary
(`T-9505`'s claim about milestone #9601, confidence 0.8 — no such
milestone exists; the same claim written twice in that tweet's own text
is de-duplicated to one candidate, not two), while correctly excluding a
tweet naming milestone #21 (real and closed — no seam) and a tweet naming
milestone #34 (real and open — no seam either, that's `tweet-claims-open-
milestone`'s own remit). Two more tweets carry no milestone claim at all:
one mentions a bare `#9605` with no claim phrase nearby —
`own-tweet-dangling-reference`'s number space, not this one's — and one
sits behind an explicit denial ("We have not hit milestone #9606 this
cycle"), dropped by the shared grammar's own negation check.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../RECIPES/tweet-claims-dangling-milestone/recipe.json
```
