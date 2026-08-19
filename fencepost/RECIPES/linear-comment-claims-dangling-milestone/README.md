# linear-comment-claims-dangling-milestone

The eighty-fourth real recipe.

**The seam it watches:** a Linear issue comment invokes a real
`milestone #N` claim phrase —
[`seam_engine.milestone_claims.claimed_milestone_numbers`](../../seam_engine/src/seam_engine/milestone_claims.py),
the same grammar every `*-claims-*-milestone` sibling already imports —
but no milestone with that number exists at all.
[`../linear-comment-claims-open-milestone/`](../linear-comment-claims-open-milestone/)
drew this exact line in its own docstring: a claimed milestone number
that names no real milestone at all was excluded there, named not
hidden, "that broken reference belongs to a future Linear-side
dangling-reference recipe, not this one." This recipe is that seam, on
the one surface that named it — the Linear-sourced sibling of
[`../commit-claims-dangling-milestone/`](../commit-claims-dangling-milestone/)
(the seventy-sixth real recipe),
[`../issue-comment-claims-dangling-milestone/`](../issue-comment-claims-dangling-milestone/)
(the eighty-first),
[`../review-comment-claims-dangling-milestone/`](../review-comment-claims-dangling-milestone/)
(the eighty-second), and
[`../slack-message-claims-dangling-milestone/`](../slack-message-claims-dangling-milestone/)
(the eighty-third), which closed the identical seam for a commit
message, an issue/PR timeline comment, a pull request's own inline
review comment, and a Slack channel message respectively.

It is not
[`../linear-comment-dangling-reference/`](../linear-comment-dangling-reference/)'s
seam wearing a new name. That recipe watches a bare `#N` posted inside a
Linear issue comment against GitHub's shared issue/PR number sequence
and never opens `ListMilestones` at all — a milestone lives in its own,
separate number space, so a `#N` that resolves cleanly as a real issue
could still be a dangling *milestone* claim, and conflating the two
spaces would misfire exactly the way Ògún's law calls fatal.

Two fixtures, no live account —
[`../../fixtures/linear_comment_claims_dangling_milestone/comments.json`](../../fixtures/linear_comment_claims_dangling_milestone/comments.json)
and
[`../../fixtures/linear_comment_claims_dangling_milestone/milestones.json`](../../fixtures/linear_comment_claims_dangling_milestone/milestones.json)
— shaped like what a live `SearchIssueComments`/`ListMilestones` read
would actually return. Per `SCOPES.md`'s own WIP note on the `linear`
toolkit: the-hand gateway holds a real, connected upstream
`arcade-linear` app today, but exposes zero Linear-capable tools on the
live gateway — the identical "connected upstream, not wired into the
gateway" shape `SCOPES.md`'s Gmail/Calendar and Slack WIP notes already
document for two other toolkits. `source: "fixture"` in `run_recipe_
scan`'s own output is the honest WIP marker; only the fixture loaders
swap for real calls the day a live Linear-capable tool appears.

A claimed milestone number that DOES resolve to a real milestone is
excluded here, named not hidden, whether that milestone is open or
closed — whether the claim itself is true is
`linear-comment-claims-open-milestone`'s own seam, not this one's. A
comment with no `milestone #N` claim phrase at all (a bare `#N` aside),
or no text at all, never becomes a candidate either.

Confidence is flat (0.8), not age-gated, mirroring
`commit-claims-dangling-milestone`'s,
`issue-comment-claims-dangling-milestone`'s,
`review-comment-claims-dangling-milestone`'s, and
`slack-message-claims-dangling-milestone`'s own reasoning rather than
`linear-comment-claims-open-milestone`'s 24-hour edit-grace bar: an open
milestone could close at any moment, so a fresh claim about it might
just be a race the comment hasn't caught up to yet — but a milestone
number that does not exist right now will not spontaneously start
existing later, so there is no grace period that means anything here.
See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/linear-comment-claims-dangling-milestone/detector.py
```

Against the shipped fixture it finds one real gap as the elected primary
(comment `LIN-C-9501`'s claim about milestone #9601, confidence 0.8 — no
such milestone exists; a duplicate claim inside the same comment is
de-duplicated to one candidate, not two), while correctly excluding
comment `LIN-C-9502` (claims milestone #9602, which is real and open —
no seam, that's `linear-comment-claims-open-milestone`'s own remit),
comment `LIN-C-9503` (a bare `#9699` aside, no `milestone #N` claim
phrase at all), comment `LIN-C-9504` (claims milestone #9603, which is
real and closed, alongside a bare `#9999` aside that is never extracted
as a claim), and comment `LIN-C-9505` (no text at all — never examined).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/linear-comment-claims-dangling-milestone/recipe.json
```
