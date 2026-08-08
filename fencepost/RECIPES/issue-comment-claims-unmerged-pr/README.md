# issue-comment-claims-unmerged-pr

The sixtieth real recipe. The ninth leg the claims-X family has grown on
the issue-comment side, and the third of the timeline-comment surface's
own three claim types, alongside
[`../issue-comment-claims-unfixed-issue/`](../issue-comment-claims-unfixed-issue/)
(task 590, the fifty-eighth real recipe) and
[`../issue-comment-claims-open-milestone/`](../issue-comment-claims-open-milestone/)
(task 591, the fifty-ninth real recipe) — both of those recipes' own
README named this exact remaining cell before anyone built it. This
recipe is the direct sibling of
[`../review-comment-claims-unmerged-pr/`](../review-comment-claims-unmerged-pr/)
(task 585, the fifty-fifth real recipe), which already proved an inline
review comment could carry the same "ships/includes/merges/via #N"
claim, applied here to the ordinary timeline-comment surface instead.
With this recipe shipped, the issue-comment row of the claims-X grid
stands complete at 3/3.

**The seam it watches:** an issue or pull request's own ordinary
conversation comment invokes a real "ships/includes/merges/via #N" claim
phrase against a PR number — "this also ships #901 while we're in
here", "I think this merges #903 too" — but PR #N is not actually
merged (still open, or closed without merging). GitHub never merges
anything off an ordinary timeline comment's own text — it has never
once, in GitHub's history, honored a closing keyword or a claim phrase
typed into a conversation comment on either an issue or a pull request
(GitHub shares one issue-comments endpoint between the two, which is why
this recipe's own `issue_number` field can name either object) — so a
false claim here is exactly as durable as its two timeline-comment
siblings' false claims: nothing was ever going to catch it regardless of
what happens to the PR.

Two fixtures, no live account —
[`../../fixtures/issue_comment_claims_unmerged_pr/issue_comments.json`](../../fixtures/issue_comment_claims_unmerged_pr/issue_comments.json)
and
[`.../pulls.json`](../../fixtures/issue_comment_claims_unmerged_pr/pulls.json)
— shaped like what a live read of ordinary issue/PR comments and
`ListPullRequests` would actually return. `ListPullRequests` already
sits on `SCOPES.md`'s cleared oath table, used by nearly every recipe in
this engine that reads the PR tracker. **The honest gap this recipe
names, not hides:** unlike its closest sibling
`review-comment-claims-unmerged-pr` (whose
`ListReviewCommentsInARepository` scope is a real, live, read-only tool
on the-hand gateway today), no live tool shaped like "list issue/PR
comments" is exposed anywhere on the-hand gateway as of this writing —
checked again this hour via `tools/gateway_toolset_check.py`'s own live
search, the same check `SCOPES.md`'s WIP note on
`issue-comment-dangling-reference` already runs. `run_recipe_scan`'s own
output carries `"source": "fixture"` so nothing here overclaims a live
read it cannot make; the day a live tool appears, only the two fixture
loaders swap for real calls and the detection logic below does not
change one line.

A claimed PR that doesn't exist at all is excluded here, named not
hidden — that broken reference belongs to
[`../issue-comment-dangling-reference/`](../issue-comment-dangling-reference/)'s
own seam, not this one's. A claimed PR that IS merged is excluded too —
the claim was simply true. A comment with no
ships/includes/merges/via claim phrase at all (a bare "same root cause
as #N" aside, or no `#N` at all) never becomes a candidate, and neither
does a comment with no body at all — neither claims anything about a
second record, so there is no seam to weigh.

Reuses `seam_engine.pr_claims.claimed_pr_numbers` verbatim — the same
shared grammar `review-comment-claims-unmerged-pr`, `release-claims-
unmerged-pr`, `merged-pr-never-released`, `tweet-claims-unmerged-pr`,
and `mention-claims-unmerged-pr` already import from there — rather than
a seventh independently retyped copy of the identical pattern.

**Confidence is age-gated off the comment's own `updated_at`, mirroring
`issue-comment-claims-open-milestone`'s and `review-comment-claims-
unmerged-pr`'s own 0.55/0.85 bar rather than `mention-claims-unmerged-
pr`'s/`tweet-claims-unmerged-pr`'s 0.5/0.85 one.** An ordinary timeline
comment, like a review comment or an issue/PR body, is a text surface
its own author can edit at any time — unlike a mention or a tweet,
posted once and standing, there is a real "may simply not have caught up
yet" grace period that means something here. A claim checked within 24
hours of the comment's own last update scores 0.55 (below the confidence
bar, shown as a weighed coincidence, not hidden); at or past 24 hours it
scores 0.85 (unambiguous — nobody is coming back to fix it). See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/issue-comment-claims-unmerged-pr/detector.py
```

Run bare like this it uses the real wall clock, so the fixture comments'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (comment 8201's claim
about #901 on #60's own thread, confidence 0.85, last updated well past
the 24h bar) and weighs two coincidences in the tail (comment 8202's
claim about #903 on #61's thread, and comment 8207's duplicated "ships
#901 ... via #901" claim on #66's thread, both confidence 0.55, both
updated inside the 24h window at the pinned test clock), while correctly
excluding comment 8203's claim about #902 (true — merged), comment
8204's claim about #999 (no such PR — dangling-reference's own seam),
comment 8205 (no claim phrase at all, just a bare "#905" aside), and
comment 8206 (no body at all).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/issue-comment-claims-unmerged-pr/recipe.json
```
