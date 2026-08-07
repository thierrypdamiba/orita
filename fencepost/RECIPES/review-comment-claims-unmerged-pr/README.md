# review-comment-claims-unmerged-pr

The fifty-fifth real recipe (ROADMAP.md #585). The missing review-comment-side
leg of the claims-unmerged-pr family alongside
[`../readme-claims-unmerged-pr/`](../readme-claims-unmerged-pr/),
[`../release-claims-unmerged-pr/`](../release-claims-unmerged-pr/),
[`../tweet-claims-unmerged-pr/`](../tweet-claims-unmerged-pr/),
[`../mention-claims-unmerged-pr/`](../mention-claims-unmerged-pr/), and
[`../milestone-claims-unmerged-pr/`](../milestone-claims-unmerged-pr/) —
those five already check whether a ships/includes/merges/via `#N` claim phrase
made on a text surface holds against the PR tracker, but every one of them
reads either a surface the town itself controls (its own README, release
notes, tweets) or a stranger's inbound X mention. None of them ever read a
GitHub-native surface at all. This recipe is the direct sibling of
[`../review-comment-claims-unfixed-issue/`](../review-comment-claims-unfixed-issue/)
(task 582, the fifty-fourth real recipe) — that recipe named this exact
boundary in its own README and `recipe.json` before anyone built it:
"a closing-keyword claim naming a real pull request is
`review-comment-claims-unmerged-pr`'s own future seam, not this one's."
This is that future seam, built.

**The seam it watches:** a pull request's own inline code review comment
invokes a real "ships/includes/merges/via `#N`" claim phrase against a PR
number — "this also ships #901 while we're in here", "I think this merges
#903 too" — but PR #N is not actually merged (still open, or closed
without merging). GitHub never merges anything off a review comment's own
text — a review comment cannot trigger a merge the way a PR's own body or
a commit message can trigger an issue auto-close — so a false claim here
is exactly as durable as its sibling's false issue-fix claim: nothing on
either GitHub or X was ever going to catch it regardless of what happens
to the PR. Two fixtures, no live account —
[`../../fixtures/review_comment_claims_unmerged_pr/review_comments.json`](../../fixtures/review_comment_claims_unmerged_pr/review_comments.json)
and
[`.../pulls.json`](../../fixtures/review_comment_claims_unmerged_pr/pulls.json)
— shaped like what `ListReviewCommentsInARepository` and
`ListPullRequests` would actually return. Both scopes already sit on
`SCOPES.md`'s cleared oath table (`ListReviewCommentsInARepository` live
since `review-comment-dangling-reference`, the forty-fourth real recipe;
`ListPullRequests` used by nearly every recipe in this engine that reads
the PR tracker). No new scope is asked for anywhere in this recipe.

A claimed PR that doesn't exist at all is excluded here, named not hidden
— that broken reference belongs to
[`../dangling-issue-reference/`](../dangling-issue-reference/) /
[`../review-comment-dangling-reference/`](../review-comment-dangling-reference/)'s
own seam, not this one's. A claimed PR that IS merged is excluded too —
the claim was simply true. A review comment with no ships/includes/merges/via
claim phrase at all (a bare "same root cause as #N" aside, or no `#N` at
all) never becomes a candidate, and neither does a review comment with no
body at all — neither claims anything about a second record, so there is
no seam to weigh.

Reuses `seam_engine.pr_claims.claimed_pr_numbers` verbatim — the same
shared grammar `release-claims-unmerged-pr`, `merged-pr-never-released`,
`tweet-claims-unmerged-pr`, `mention-claims-unmerged-pr`, and
`milestone-claims-unmerged-pr` already import from there — rather than a
sixth independently retyped copy of the identical pattern.

**Confidence is age-gated off the review comment's own `updated_at`,
mirroring `review-comment-claims-unfixed-issue`'s own 0.55/0.85 bar
exactly rather than `mention-claims-unmerged-pr`'s/`tweet-claims-unmerged-pr`'s
0.5/0.85 one.** A review comment, like an issue/PR body or a milestone
description, is a text surface its own author can edit at any time —
unlike a mention or a tweet, posted once and standing, there is a real
"may simply not have caught up yet" grace period that means something
here. A claim checked within 24 hours of the comment's own last update
scores 0.55 (below the confidence bar, shown as a weighed coincidence,
not hidden); at or past 24 hours it scores 0.85 (unambiguous — nobody is
coming back to fix it). See `recipe.json`'s `confidence_notes` for the
full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/review-comment-claims-unmerged-pr/detector.py
```

Run bare like this it uses the real wall clock, so the fixture comments'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (review comment 9201's
claim about #901 on PR #301, confidence 0.85, last updated well past the
24h bar) and weighs two coincidences in the tail (comment 9202's claim
about #903 on PR #302, and comment 9207's duplicated "ships #901 ... via
#901" claim on PR #307, both confidence 0.55, both updated inside the
24h window at the pinned test clock), while correctly excluding comment
9203's claim about #902 (true — merged), comment 9204's claim about #999
(no such PR — dangling-reference's own seam), comment 9205 (no
closing-keyword claim at all, just a bare "#905" aside), and comment 9206
(no body at all).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/review-comment-claims-unmerged-pr/recipe.json
```
