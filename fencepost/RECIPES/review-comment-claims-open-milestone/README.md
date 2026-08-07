# review-comment-claims-open-milestone

The fifty-sixth real recipe (ROADMAP.md #588). The missing review-comment-side
leg of the claims-open-milestone family alongside
[`../readme-claims-open-milestone/`](../readme-claims-open-milestone/),
[`../release-claims-open-milestone/`](../release-claims-open-milestone/),
[`../tweet-claims-open-milestone/`](../tweet-claims-open-milestone/),
[`../mention-claims-open-milestone/`](../mention-claims-open-milestone/), and
[`../milestone-claims-open-milestone/`](../milestone-claims-open-milestone/) —
those five already check whether a "milestone #N" claim phrase holds against
the milestone tracker, but every one of them reads either a surface the town
itself controls (its own README, release notes, another milestone's own
description, tweets) or a stranger's inbound X mention. None of them ever
read a GitHub-native surface at all. This recipe is the direct sibling of
[`../review-comment-claims-unfixed-issue/`](../review-comment-claims-unfixed-issue/)
(task 582, the fifty-fourth real recipe) and
[`../review-comment-claims-unmerged-pr/`](../review-comment-claims-unmerged-pr/)
(task 585, the fifty-fifth) — those two proved a review comment is a real
GitHub-native claim surface for the issue-side and PR-side legs of the
claims-X grid; this is the third and final leg the review-comment source had
never grown. `review-comment-claims-unfixed-issue`'s own README named the
grid at five sources times three claim types (fifteen legs) before
review-comment joined as a sixth source; with this recipe the full
six-sources-times-three-claim-types grid (eighteen legs) is complete —
every source this engine reads (README, release, milestone, tweet, mention,
review comment) now has all three claim-type legs (open-milestone,
unfixed-issue, unmerged-pr) built.

**The seam it watches:** a pull request's own inline code review comment
invokes a real "milestone #N" claim phrase against a milestone number —
"this also ships milestone #6001 while we're in here", "I think this closes
milestone #6003 too" — but milestone #N is not actually closed (still open).
GitHub gives a milestone no auto-close-style keyword of its own at all (the
same reason `milestone-closed-never-released/detector.py` invented the
`milestone #N` grammar in the first place, rather than overloading the
issue-side closing-keyword one or the PR-side ships/includes/merges/via
one), so a review comment naming a milestone was never wired to anything on
GitHub's side regardless of whether the milestone ever closes — a false
claim here is exactly as durable as this family's other review-comment legs
found for issues and PRs. Two fixtures, no live account —
[`../../fixtures/review_comment_claims_open_milestone/review_comments.json`](../../fixtures/review_comment_claims_open_milestone/review_comments.json)
and
[`.../milestones.json`](../../fixtures/review_comment_claims_open_milestone/milestones.json)
— shaped like what `ListReviewCommentsInARepository` and `ListMilestones`
would actually return. Both scopes already sit on `SCOPES.md`'s cleared oath
table (`ListReviewCommentsInARepository` live since
`review-comment-dangling-reference`, the forty-fourth real recipe;
`ListMilestones` used by every `*-claims-open-milestone` sibling). No new
scope is asked for anywhere in this recipe.

A claimed milestone that doesn't exist at all is excluded here, named not
hidden — that broken reference belongs to a dangling-reference recipe's own
seam (over issues/PRs), not this one's (over milestones; no
review-comment-side milestone-dangling-reference recipe exists yet either —
a genuinely separate future seam, named here rather than quietly assumed
covered). A claimed milestone that IS closed is excluded too — the claim was
simply true. A review comment with no "milestone #N" claim phrase at all (a
bare "same root cause as #N" aside, or no `#N` at all) never becomes a
candidate, and neither does a review comment with no body at all — neither
claims anything about a second record, so there is no seam to weigh.

Reuses `seam_engine.milestone_claims.claimed_milestone_numbers` verbatim —
the same shared grammar `milestone-closed-never-released`,
`release-claims-open-milestone`, `milestone-closed-not-tweeted`,
`tweet-claims-open-milestone`, `mention-claims-open-milestone`, and
`readme-claims-open-milestone` already import from there — rather than a
seventh independently retyped copy of the identical pattern.

**Confidence is age-gated off the review comment's own `updated_at`,
mirroring `review-comment-claims-unfixed-issue`'s and
`review-comment-claims-unmerged-pr`'s own 0.55/0.85 bar exactly rather than
`tweet-claims-open-milestone`'s/`release-claims-open-milestone`'s 0.5/0.85
one.** A review comment, like an issue/PR body or a milestone description,
is a text surface its own author can edit at any time — unlike a tweet or a
mention, posted once and standing, there is a real "may simply not have
caught up yet" grace period that means something here. A claim checked
within 24 hours of the comment's own last update scores 0.55 (below the
confidence bar, shown as a weighed coincidence, not hidden); at or past 24
hours it scores 0.85 (unambiguous — nobody is coming back to fix it). See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/review-comment-claims-open-milestone/detector.py
```

Run bare like this it uses the real wall clock, so the fixture comments'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (review comment 9301's
claim about milestone #6001 on PR #301, confidence 0.85, last updated well
past the 24h bar) and weighs two coincidences in the tail (comment 9302's
claim about milestone #6003 on PR #302, and comment 9307's duplicated
"ships milestone #6001 ... milestone #6001 confirmed again" claim on PR
#307, both confidence 0.55, both updated inside the 24h window at the
pinned test clock), while correctly excluding comment 9303's claim about
milestone #6002 (true — closed), comment 9304's claim about milestone #6999
(no such milestone — a dangling reference, out of this recipe's own remit),
comment 9305 (no "milestone #N" claim phrase at all, just a bare "#6005"
aside), and comment 9306 (no body at all).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/review-comment-claims-open-milestone/recipe.json
```
