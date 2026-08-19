# mention-claims-dangling-milestone

The eighty-sixth real recipe.

**The seam it watches:** a mortal's own X mention of the connected account
invokes a real `milestone #N` claim phrase —
[`seam_engine.milestone_claims.claimed_milestone_numbers`](../../seam_engine/src/seam_engine/milestone_claims.py),
the same grammar every `*-claims-*-milestone` sibling already imports —
but no milestone with that number exists at all.
[`../mention-claims-open-milestone/`](../mention-claims-open-milestone/)
(the forty-eighth real recipe) drew this exact line in its own docstring:
a claimed milestone number that names no real milestone at all was
excluded there, named not hidden, "that broken reference is a
dangling-reference-family seam, not this one's." This recipe is that
seam, on the one surface that named it and never closed it — the
mention-sourced sibling of
[`../commit-claims-dangling-milestone/`](../commit-claims-dangling-milestone/),
[`../issue-comment-claims-dangling-milestone/`](../issue-comment-claims-dangling-milestone/),
[`../review-comment-claims-dangling-milestone/`](../review-comment-claims-dangling-milestone/),
[`../slack-message-claims-dangling-milestone/`](../slack-message-claims-dangling-milestone/),
and
[`../linear-comment-claims-dangling-milestone/`](../linear-comment-claims-dangling-milestone/),
which closed the identical seam for a commit message, an issue/PR
timeline comment, a pull request's own inline review comment, a Slack
channel message, and a Linear issue comment respectively.

A prior hour's own-remit sweep (task 869) called the whole
claims-dangling-milestone family "genuinely saturated," reasoning that
this recipe and its four siblings on `mention`/`milestone`/`readme`/
`release`/`tweet` were each already "covered" by that source's own
already-built dangling-reference recipe. Checked live this hour, that
turned out not to hold: `mention-dangling-reference`,
`milestone-body-dangling-reference`, `readme-dangling-reference`,
`release-note-dangling-reference`, and `own-tweet-dangling-reference` each
check the shared GitHub issue/PR number sequence only — none of them
opens `ListMilestones` at all, so none of them actually closes a milestone
number-space seam. This recipe closes the first of those five real gaps;
the other four (`milestone`, `readme`, `release`, `tweet`) remain open,
correctly, for a future hour — named here rather than silently reused.

It is not
[`../mention-dangling-reference/`](../mention-dangling-reference/)'s
seam wearing a new name. That recipe (the eleventh real recipe) watches a
bare `#N` inside a mortal's own mention against GitHub's shared issue/PR
number sequence and never opens `ListMilestones` at all — a milestone
lives in its own, separate number space, so a `#N` that resolves cleanly
as a real issue could still be a dangling *milestone* claim, and
conflating the two spaces would misfire exactly the way Ògún's law calls
fatal.

Two fixtures, no live account —
[`../../fixtures/mention_claims_dangling_milestone/mentions.json`](../../fixtures/mention_claims_dangling_milestone/mentions.json)
and
[`../../fixtures/mention_claims_dangling_milestone/milestones.json`](../../fixtures/mention_claims_dangling_milestone/milestones.json)
— shaped like what a live `GetMyMentions`/`ListMilestones` read would
actually return. Both scopes already sit on `SCOPES.md`'s cleared oath
table; no new scope is asked for anywhere in this recipe. `source:
"fixture"` in `run_recipe_scan`'s own output is the honest WIP marker;
only the fixture loaders swap for real calls the day a live connected
account backs them.

A claimed milestone number that DOES resolve to a real milestone is
excluded here, named not hidden, whether that milestone is open or
closed — whether the claim itself is true is
`mention-claims-open-milestone`'s own seam, not this one's. A mention
with no `milestone #N` claim phrase at all (a bare `#N` aside), or no
text at all, never becomes a candidate either.

Confidence is flat (0.8), not age-gated, mirroring every prior
claims-dangling-milestone sibling's own reasoning rather than
`mention-claims-open-milestone`'s 24-hour edit-grace bar: an open
milestone could close at any moment, so a fresh claim about it might just
be a race the mention hasn't caught up to yet — but a milestone number
that does not exist right now will not spontaneously start existing
later, so there is no grace period that means anything here. See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/mention-claims-dangling-milestone/detector.py
```

Against the shipped fixture it finds one real gap as the elected primary
(mention `M-6301`'s claim about milestone #6301, confidence 0.8 — no such
milestone exists; a duplicate claim inside the same mention is
de-duplicated to one candidate, not two), while correctly excluding
mention `M-6302` (claims milestone #6302, which is real and open — no
seam, that's `mention-claims-open-milestone`'s own remit), mention
`M-6303` (a bare `#6399` aside, no `milestone #N` claim phrase at all),
mention `M-6304` (claims milestone #6303, which is real and closed,
alongside a bare `#6999` aside that is never extracted as a claim), and
mention `M-6305` (no text at all — never examined).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/mention-claims-dangling-milestone/recipe.json
```
