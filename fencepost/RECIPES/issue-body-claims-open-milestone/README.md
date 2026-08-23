# issue-body-claims-open-milestone

The ninety-second real recipe. The one surface the claims-open-milestone
family had never grown a leg for: an issue or pull request's own OPENING
BODY (not a timeline comment, not an inline review comment — the
description itself). `readme-claims-open-milestone`,
`release-claims-open-milestone`, `tweet-claims-open-milestone`,
`mention-claims-open-milestone`, `milestone-claims-open-milestone`,
`review-comment-claims-open-milestone`,
`slack-message-claims-open-milestone`, and
`linear-comment-claims-open-milestone` all already check the identical
claim grammar against eight other text surfaces — but none of them ever
reads an issue or PR's own body. `../issue-body-dangling-reference/`
(the twenty-fourth real recipe) already proved that surface was the
single most common place a stray `#N` gets typed in this town's own
history, for the dangling-reference leg only; this recipe closes the
milestone-claim leg for the same surface.

**The seam it watches:** an issue or pull request's own opening body
invokes a real "milestone #N" claim phrase against a milestone number —
"this also ships milestone #6301 while we're in here", "I think this
finishes milestone #6303 too" — but milestone #N is not actually closed
(still open). GitHub gives a milestone no auto-close-style keyword of its
own at all, so a body naming a milestone was never wired to anything on
GitHub's side regardless of whether the milestone ever closes.

Three fixtures, no live account —
[`../../fixtures/issue_body_claims_open_milestone/issues.json`](../../fixtures/issue_body_claims_open_milestone/issues.json),
[`.../pulls.json`](../../fixtures/issue_body_claims_open_milestone/pulls.json),
and
[`.../milestones.json`](../../fixtures/issue_body_claims_open_milestone/milestones.json)
— shaped like what `ListIssues`, `ListPullRequests`, and `ListMilestones`
would actually return. All three scopes already sit on `SCOPES.md`'s
cleared oath table — this recipe asks Arcade for nothing new. Unlike
`issue-comment-claims-open-milestone`'s own honest WIP marker (no live
"list issue/PR comments" tool exists on the-hand gateway), `ListIssues`
and `ListPullRequests` are both real, live, read-only tools today —
`run_recipe_scan`'s `"source": "fixture"` here is only CONTRIBUTING.md's
MOCK ONLY law holding for every recipe on the day it merges, not a claim
the underlying scopes are unavailable.

A claimed milestone that doesn't exist at all is excluded here, named not
hidden — that broken reference is `../issue-body-dangling-reference/`'s
own seam, not this one's (a bare `#N` reference and a `milestone #N`
claim phrase name different number spaces, so the two recipes never
collide on the same candidate). A claimed milestone that IS closed is
excluded too — the claim was simply true. A body with no "milestone #N"
claim phrase at all never becomes a candidate, and neither does a body
that's empty — neither claims anything about a second record, so there
is no seam to weigh.

Reuses `seam_engine.milestone_claims.claimed_milestone_numbers` verbatim
— the same shared grammar every other `*-claims-open-milestone` sibling
already imports from there — and reuses the exact `Issue`/`PullRequest`
dataclasses and `load_issues`/`load_pulls` loaders
`../issue-body-dangling-reference/` already established for this surface,
rather than a second, independently drifting copy of either.

**Confidence is age-gated off the claiming record's own `updated_at`,
mirroring `../issue-body-dangling-reference/`'s and
`../issue-comment-claims-open-milestone/`'s own 0.55/0.85 bar.** An issue
or PR body, like a timeline comment or a milestone description, is a text
surface its own author can edit at any time — a claim checked within 24
hours of the record's own last update scores 0.55 (below the confidence
bar, shown as a weighed coincidence, not hidden); at or past 24 hours it
scores 0.85 (unambiguous — nobody is coming back to fix it). See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/issue-body-claims-open-milestone/detector.py
```

Run bare like this it uses the real wall clock, so the fixture records'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (issue #70's claim
about milestone #6301, confidence 0.85, last updated well past the 24h
bar) and weighs two coincidences in the tail (issue #75's claim about the
same milestone #6301, and PR #53's claim about milestone #6303, both
confidence 0.55, both updated inside the 24h window at the pinned test
clock), while correctly excluding issue #71's claim about milestone #6302
(true — closed), issue #72's and PR #55's claims about milestones that
don't exist (#6999, #6998), PR #52's duplicated "milestone #6302 ...
milestone #6302" claim (deduped to one excluded entry, also true), issue
#73 (a bare `#5` aside, no "milestone #N" claim phrase at all), and issue
#74 (no body at all).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../RECIPES/issue-body-claims-open-milestone/recipe.json
```
