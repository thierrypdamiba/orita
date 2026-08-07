# issue-comment-claims-open-milestone

The fifty-ninth real recipe. The eighth leg the claims-X family has
grown on the issue-comment side, alongside
[`../issue-comment-claims-unfixed-issue/`](../issue-comment-claims-unfixed-issue/)
(the fifty-eighth real recipe) — that one already checks whether a
real GitHub closing-keyword claim ("fixes #N" / "closes #N" /
"resolves #N") holds against the issue tracker on an issue or pull
request's own ordinary timeline comment; this recipe asks the identical
surface's milestone-side question, the direct sibling of
[`../review-comment-claims-open-milestone/`](../review-comment-claims-open-milestone/)
(the fifty-sixth real recipe), which already proved an inline review
comment could carry the same "milestone #N" claim. Between the two, the
timeline-comment surface now covers two of the three claim types
(unfixed-issue and open-milestone); `issue-comment-claims-unmerged-pr`
is the one remaining leg.

**The seam it watches:** an issue or pull request's own ordinary
conversation comment invokes a real "milestone #N" claim phrase against a
milestone number — "this also ships milestone #6101 while we're in
here", "I think this closes milestone #6103 too" — but milestone #N is
not actually closed (still open). GitHub gives a milestone no auto-close-
style keyword of its own at all, so a timeline comment naming a milestone
was never wired to anything on GitHub's side regardless of whether the
milestone ever closes.

Two fixtures, no live account —
[`../../fixtures/issue_comment_claims_open_milestone/issue_comments.json`](../../fixtures/issue_comment_claims_open_milestone/issue_comments.json)
and
[`.../milestones.json`](../../fixtures/issue_comment_claims_open_milestone/milestones.json)
— shaped like what a live read of ordinary issue/PR comments and
`ListMilestones` would actually return. `ListMilestones` already sits on
`SCOPES.md`'s cleared oath table, used by every `*-claims-open-milestone`
sibling. **The honest gap this recipe names, not hides:** unlike its
closest sibling `review-comment-claims-open-milestone` (whose
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

A claimed milestone that doesn't exist at all is excluded here, named
not hidden — that broken reference belongs to a future milestone-side
dangling-reference recipe's own seam, not this one's. A claimed
milestone that IS closed is excluded too — the claim was simply true. A
comment with no "milestone #N" claim phrase at all (a bare "same root
cause as #N" aside, or no `#N` at all) never becomes a candidate, and
neither does a comment with no body at all — neither claims anything
about a second record, so there is no seam to weigh.

Reuses `seam_engine.milestone_claims.claimed_milestone_numbers` verbatim
— the same shared grammar `milestone-closed-never-released`,
`release-claims-open-milestone`, `milestone-closed-not-tweeted`,
`tweet-claims-open-milestone`, `mention-claims-open-milestone`,
`readme-claims-open-milestone`, and `review-comment-claims-open-milestone`
already import from there — rather than an eighth independently retyped
copy of the identical pattern.

**Confidence is age-gated off the comment's own `updated_at`, mirroring
`issue-comment-claims-unfixed-issue`'s and `review-comment-claims-open-
milestone`'s own 0.55/0.85 bar rather than `tweet-claims-open-
milestone`'s/`mention-claims-open-milestone`'s 0.5/0.85 one.** An
ordinary timeline comment, like a review comment or an issue/PR body, is
a text surface its own author can edit at any time — unlike a mention or
a tweet, posted once and standing, there is a real "may simply not have
caught up yet" grace period that means something here. A claim checked
within 24 hours of the comment's own last update scores 0.55 (below the
confidence bar, shown as a weighed coincidence, not hidden); at or past
24 hours it scores 0.85 (unambiguous — nobody is coming back to fix it).
See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/issue-comment-claims-open-milestone/detector.py
```

Run bare like this it uses the real wall clock, so the fixture comments'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (comment 8101's claim
about milestone #6101 on issue #50's thread, confidence 0.85, last
updated well past the 24h bar) and weighs two coincidences in the tail
(comment 8102's claim about milestone #6103 on PR #51's thread, and
comment 8107's duplicated "milestone #6101 ... milestone #6101" claim on
issue #56's thread, both confidence 0.55, both updated inside the 24h
window at the pinned test clock), while correctly excluding comment
8103's claim about milestone #6102 (true — closed), comment 8104's claim
about milestone #6999 (no such milestone), comment 8105 (no "milestone
#N" claim at all, just a bare "#6105" aside), and comment 8106 (no body
at all).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/issue-comment-claims-open-milestone/recipe.json
```
