# issue-comment-claims-dangling-milestone

The eighty-first real recipe.

**The seam it watches:** an issue or pull request's own ordinary
TIMELINE comment invokes a real `milestone #N` claim phrase —
[`seam_engine.milestone_claims.claimed_milestone_numbers`](../../seam_engine/src/seam_engine/milestone_claims.py),
the same grammar every `*-claims-*-milestone` sibling already imports —
but no milestone with that number exists at all.
[`../issue-comment-claims-open-milestone/`](../issue-comment-claims-open-milestone/)
(the fifty-ninth real recipe) drew this exact line in its own docstring:
a claimed milestone number that names no real milestone at all was
excluded there, named not hidden, "as belonging to a future
milestone-side dangling-reference recipe's own seam, not this one's."
This recipe is that seam, on the one surface that named it — the
issue-comment-sourced sibling of
[`../commit-claims-dangling-milestone/`](../commit-claims-dangling-milestone/)
(the seventy-sixth real recipe), which closed the identical seam for a
commit message.

It is not
[`../issue-comment-dangling-reference/`](../issue-comment-dangling-reference/)'s
seam wearing a new name. That recipe watches a bare `#N` against
GitHub's shared issue/PR number sequence and never opens `ListMilestones`
at all — a milestone lives in its own, separate number space, so a `#N`
that resolves cleanly as a real issue could still be a dangling
*milestone* claim, and conflating the two spaces would misfire exactly
the way Ògún's law calls fatal.

Two fixtures, no live account —
[`../../fixtures/issue_comment_claims_dangling_milestone/issue_comments.json`](../../fixtures/issue_comment_claims_dangling_milestone/issue_comments.json)
and
[`../../fixtures/issue_comment_claims_dangling_milestone/milestones.json`](../../fixtures/issue_comment_claims_dangling_milestone/milestones.json)
— shaped like what a live read of an issue/PR's ordinary timeline
comments and `ListMilestones` would actually return. Per `SCOPES.md`'s
own WIP note on `issue-comment-dangling-reference`: no read-only "list
issue/PR comments" tool is exposed anywhere on the-hand gateway today, so
this recipe's own `recipe.json` declares only the one scope that IS
already cleared (`ListMilestones`) — it does not invent a second scope
the Oath never swore to. `source: "fixture"` in `run_recipe_scan`'s own
output is the honest WIP marker; only the fixture loader swaps for a real
call the day a live comments tool appears.

A claimed milestone number that DOES resolve to a real milestone is
excluded here, named not hidden, whether that milestone is open or
closed — whether the claim itself is true is
`issue-comment-claims-open-milestone`'s own seam, not this one's. A
comment with no `milestone #N` claim phrase at all (a bare `#N` aside),
or no body at all, never becomes a candidate either.

Confidence is flat (0.8), not age-gated, mirroring
`commit-claims-dangling-milestone`'s own reasoning rather than
`issue-comment-claims-open-milestone`'s 24-hour edit-grace bar: an open
milestone could close at any moment, so a fresh claim about it might just
be a race the comment hasn't caught up to yet — but a milestone number
that does not exist right now will not spontaneously start existing
later, so there is no grace period that means anything here. This holds
even though a comment, unlike a commit message, stays editable forever:
the editability of the surface has no bearing on whether the milestone
*number* it names exists. See `recipe.json`'s `confidence_notes` for the
full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/issue-comment-claims-dangling-milestone/detector.py
```

Against the shipped fixture it finds one real gap as the elected primary
(comment `9201`'s claim about milestone #7201, confidence 0.8 — no such
milestone exists; a duplicate claim inside the same comment is
de-duplicated to one candidate, not two), while correctly excluding
comment `9202` (claims milestone #7202, which is real and open — no
seam, that's `issue-comment-claims-open-milestone`'s own remit), comment
`9203` (a bare `#7299` aside, no `milestone #N` claim phrase at all),
comment `9204` (claims milestone #7203, which is real and closed,
alongside a bare `#7999` aside that is never extracted as a claim), and
comment `9205` (no body at all — never examined).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/issue-comment-claims-dangling-milestone/recipe.json
```
