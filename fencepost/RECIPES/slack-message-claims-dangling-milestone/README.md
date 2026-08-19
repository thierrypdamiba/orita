# slack-message-claims-dangling-milestone

The eighty-third real recipe.

**The seam it watches:** a Slack channel message invokes a real
`milestone #N` claim phrase —
[`seam_engine.milestone_claims.claimed_milestone_numbers`](../../seam_engine/src/seam_engine/milestone_claims.py),
the same grammar every `*-claims-*-milestone` sibling already imports —
but no milestone with that number exists at all.
[`../slack-message-claims-open-milestone/`](../slack-message-claims-open-milestone/)
(the sixty-ninth real recipe) drew this exact line in its own docstring:
a claimed milestone number that names no real milestone at all was
excluded there, named not hidden, "a broken reference is a future
Slack-side dangling-reference recipe's own seam, not this one's." This
recipe is that seam, on the one surface that named it — the Slack-sourced
sibling of
[`../commit-claims-dangling-milestone/`](../commit-claims-dangling-milestone/)
(the seventy-sixth real recipe),
[`../issue-comment-claims-dangling-milestone/`](../issue-comment-claims-dangling-milestone/)
(the eighty-first), and
[`../review-comment-claims-dangling-milestone/`](../review-comment-claims-dangling-milestone/)
(the eighty-second), which closed the identical seam for a commit
message, an issue/PR timeline comment, and a pull request's own inline
review comment respectively.

It is not
[`../slack-message-dangling-reference/`](../slack-message-dangling-reference/)'s
seam wearing a new name. That recipe (task 601, the seventy-fifth real
recipe) watches a bare `#N` posted to a Slack channel against GitHub's
shared issue/PR number sequence and never opens `ListMilestones` at all —
a milestone lives in its own, separate number space, so a `#N` that
resolves cleanly as a real issue could still be a dangling *milestone*
claim, and conflating the two spaces would misfire exactly the way
Ògún's law calls fatal.

Two fixtures, no live account —
[`../../fixtures/slack_message_claims_dangling_milestone/messages.json`](../../fixtures/slack_message_claims_dangling_milestone/messages.json)
and
[`../../fixtures/slack_message_claims_dangling_milestone/milestones.json`](../../fixtures/slack_message_claims_dangling_milestone/milestones.json)
— shaped like what a live `SearchChannelMessages`/`ListMilestones` read
would actually return. Per `SCOPES.md`'s own WIP note on the `slack`
toolkit: the-hand gateway holds a real, connected upstream `arcade-slack`
app today, but exposes zero Slack-capable tools on the live gateway — the
identical "connected upstream, not wired into the gateway" shape
`SCOPES.md`'s Gmail/Calendar and Linear WIP notes already document for
two other toolkits. `source: "fixture"` in `run_recipe_scan`'s own output
is the honest WIP marker; only the fixture loaders swap for real calls
the day a live Slack-capable tool appears.

A claimed milestone number that DOES resolve to a real milestone is
excluded here, named not hidden, whether that milestone is open or
closed — whether the claim itself is true is
`slack-message-claims-open-milestone`'s own seam, not this one's. A
message with no `milestone #N` claim phrase at all (a bare `#N` aside),
or no text at all, never becomes a candidate either.

Confidence is flat (0.8), not age-gated, mirroring
`commit-claims-dangling-milestone`'s,
`issue-comment-claims-dangling-milestone`'s, and
`review-comment-claims-dangling-milestone`'s own reasoning rather than
`slack-message-claims-open-milestone`'s 24-hour edit-grace bar: an open
milestone could close at any moment, so a fresh claim about it might
just be a race the message hasn't caught up to yet — but a milestone
number that does not exist right now will not spontaneously start
existing later, so there is no grace period that means anything here.
See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/slack-message-claims-dangling-milestone/detector.py
```

Against the shipped fixture it finds one real gap as the elected primary
(message `SLK-8301`'s claim about milestone #9301, confidence 0.8 — no
such milestone exists; a duplicate claim inside the same message is
de-duplicated to one candidate, not two), while correctly excluding
message `SLK-8302` (claims milestone #9302, which is real and open — no
seam, that's `slack-message-claims-open-milestone`'s own remit), message
`SLK-8303` (a bare `#9399` aside, no `milestone #N` claim phrase at
all), message `SLK-8304` (claims milestone #9303, which is real and
closed, alongside a bare `#9999` aside that is never extracted as a
claim), and message `SLK-8305` (no text at all — never examined).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/slack-message-claims-dangling-milestone/recipe.json
```
