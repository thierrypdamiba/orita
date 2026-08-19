# review-comment-claims-dangling-milestone

The eighty-second real recipe (ROADMAP.md #866). The review-comment-sourced
sibling of
[`../commit-claims-dangling-milestone/`](../commit-claims-dangling-milestone/)
(task 649, the seventy-sixth real recipe) and
[`../issue-comment-claims-dangling-milestone/`](../issue-comment-claims-dangling-milestone/)
(task 865, the eighty-first) — closing the one seam
[`../review-comment-claims-open-milestone/`](../review-comment-claims-open-milestone/)'s
own docstring named and left open: "that broken reference belongs to a
dangling-reference recipe's own seam (over issues/PRs), not this one's (over
milestones; no review-comment-side milestone-dangling-reference recipe
exists yet either — a genuinely separate future seam)."

**The seam it watches:** a pull request's own inline code review comment
invokes a real "milestone #N" claim phrase against a milestone number — "this
also ships milestone #8001 while we're in here" — but no milestone with that
number exists at all. GitHub renders the number as a clickable link
regardless of whether it resolves to anything; nothing on GitHub's side ever
checks a "milestone #N" claim phrase against the real milestone tracker
before rendering it. Two fixtures, no live account —
[`../../fixtures/review_comment_claims_dangling_milestone/review_comments.json`](../../fixtures/review_comment_claims_dangling_milestone/review_comments.json)
and
[`.../milestones.json`](../../fixtures/review_comment_claims_dangling_milestone/milestones.json)
— shaped like what `ListReviewCommentsInARepository` and `ListMilestones`
would actually return. Both scopes already sit on `SCOPES.md`'s cleared oath
table (`ListReviewCommentsInARepository` live since
`review-comment-dangling-reference`, the forty-fourth real recipe;
`ListMilestones` used by every `*-claims-open-milestone`/`*-claims-dangling-
milestone` sibling). No new scope is asked for anywhere in this recipe.

Not `review-comment-dangling-reference`'s seam wearing a new name: that
recipe watches a bare `#N` against BOTH the issue list and the PR list —
GitHub's shared issue/PR number sequence — and never once opens
`ListMilestones`. A milestone lives in its own, separate number space that
issues and pull requests never touch, so a `#N` that resolves cleanly as an
issue could still be a dangling MILESTONE claim, and a `#N` that is a real
milestone could just as easily collide with a real issue number. This
recipe reads `claimed_milestone_numbers`'s own "milestone #N" phrase
grammar, never the bare-`#N` grammar `review-comment-dangling-reference`
already owns.

A claimed milestone that DOES resolve to a real milestone is excluded here,
named not hidden, regardless of whether it is open or closed — whether the
claim is TRUE is `review-comment-claims-open-milestone`'s own seam, not this
one's; this recipe only ever asks whether the name resolves to anything at
all. A review comment that merely mentions a bare `#N` in passing ("same
root cause as #8099") makes no milestone claim at all, and is excluded, not
guessed into either bucket. A review comment with no body at all is never
examined — it claims nothing about a second record, so there is no seam to
weigh.

Reuses `seam_engine.milestone_claims.claimed_milestone_numbers` verbatim —
the same shared grammar `commit-claims-dangling-milestone` and
`issue-comment-claims-dangling-milestone` already import — rather than a
third independently retyped copy of the identical pattern.

**Confidence is flat (0.8), not age-gated**, mirroring
`commit-claims-dangling-milestone`'s and
`issue-comment-claims-dangling-milestone`'s own reasoning rather than
`review-comment-claims-open-milestone`'s 24-hour edit-grace bar. That bar
exists because an OPEN milestone could close at any moment, so a fresh claim
about it might just be a race the comment hasn't caught up to yet; a
milestone number that does not exist right now will not spontaneously start
existing later no matter how long the comment sits, so there is no grace
period that means anything here — even though a review comment, like an
issue/PR comment, stays editable forever. The editability of the SURFACE has
no bearing on whether the milestone NUMBER it names exists, which is the
only thing this recipe ever asks. See `recipe.json`'s `confidence_notes` for
the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/review-comment-claims-dangling-milestone/detector.py
```

Against its own fixture it elects one primary gap (review comment 9401's
duplicated "milestone #8001 ... milestone #8001 confirmed again" claim on PR
#401, confidence 0.8, deduplicated to one candidate), while correctly
excluding comment 9402's claim about milestone #8002 (real, open — whether
that claim is TRUE belongs to `review-comment-claims-open-milestone`, not
this recipe), comment 9403 (no "milestone #N" claim phrase at all, just a
bare "#8099" aside), comment 9404's claim about milestone #8003 (real,
closed — also out of this recipe's remit, and its trailing bare "#8999"
aside produces no second candidate), and comment 9405 (no body at all).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/review-comment-claims-dangling-milestone/recipe.json
```
