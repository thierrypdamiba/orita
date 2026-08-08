# merged-pr-requested-reviewer-never-reviewed

The sixty-third real recipe (ROADMAP.md #595). It reads a field none of the sixty-two prior
recipes has ever read: a pull request's own `requested_reviewers` list —
GitHub's real, structured record of exactly who was explicitly asked to
sign off before the work landed.

**The seam it watches:** a pull request merges, but a login its own
`requested_reviewers` field names never leaves a single review comment on
it, anywhere in the read-so-far history. GitHub does not require an
answered review request before a PR can merge (only a repository's own
branch-protection rule can force that, and this recipe assumes nothing
about whether one is configured), and once the PR merges, nothing
retroactively flags or clears the unanswered request — the solicitation
and the outcome just quietly drift apart forever. Neither `ListPullRequests`
alone (a merged PR's own `requested_reviewers` field reads identically
whether that person ever showed up or not) nor
`ListReviewCommentsInARepository` alone (an *absence* of a comment from one
particular login proves nothing by itself — maybe nobody was ever asked)
shows this; only holding both at the same instant does.

This is a genuinely different axis from every family this repo has already
saturated. It is not the claims-X grid (seven text surfaces × three claim
phrases, 21/21 closed) — there is no claim phrase and no body text parsed
here at all, just one structured field compared against one structured
fact. It is not the dangling-reference grid (nine legs, all asking whether
a `#N` target *exists*) — this recipe never reads a `#N` reference. It is
not the `*-still-open` family — a requested reviewer is not a promise the
PR itself made about its own fate; it is a solicitation GitHub's own
tooling made on the PR's behalf, and the PR in question has already
resolved (merged) by the time this recipe has anything to say about it.
It shares only the general *shape* of
[`merged-pr-branch-not-deleted`](../merged-pr-branch-not-deleted/) and
[`deleted-branch-pr-still-open`](../deleted-branch-pr-still-open/) — a
post-resolution, GitHub-native expectation nothing forces closed — but
watches a person's named, solicited review, not a branch's survival.

The claim stays narrow on purpose, the same no-grading law every sibling
holds: this recipe never claims the requested reviewer dropped the ball —
reviewers get reassigned, go on leave, or get overtaken by a maintainer
merging anyway, all ordinary and blameless. It claims only that GitHub's
own solicitation and GitHub's own review-comment record disagree. It also
makes no claim about a silent approval (a review submitted with no comment
text) — `ListReviewCommentsInARepository` reads only the inline comment
thread, not the review-submission event itself, so that signal sits
outside what this recipe's own scope can see.

Two fixtures, no live account —
[`../../fixtures/merged_pr_requested_reviewer_never_reviewed/pull_requests.json`](../../fixtures/merged_pr_requested_reviewer_never_reviewed/pull_requests.json)
and
[`../../fixtures/merged_pr_requested_reviewer_never_reviewed/review_comments.json`](../../fixtures/merged_pr_requested_reviewer_never_reviewed/review_comments.json)
— shaped like what `ListPullRequests`/`ListReviewCommentsInARepository`
would actually return. Both scopes already sit on `SCOPES.md`'s cleared
oath table under the `github` row — no new scope is asked for anywhere in
this recipe; this is simply the first recipe to pair the two together.

Confidence is age-gated on how long the pull request has sat merged while
its named reviewer's request goes unanswered, reusing
`merged-pr-branch-not-deleted`'s and `deleted-branch-pr-still-open`'s own
24-hour bar rather than inventing a new number for a structurally similar
family: under 24 hours may just be a review still in flight, weighed in
the tail at 0.5; at or past 24 hours it is unambiguous, a flat 0.85. A
pull request that has not merged (still open, or closed without merging)
is excluded, named not hidden — no resolved promise exists yet. A merged
pull request naming no requested reviewer at all is excluded too — no
solicitation was ever made. A merged pull request with no recorded
`merged_at` is excluded as malformed. A blank requested-reviewer entry is
excluded outright — not a real login. See `recipe.json`'s
`confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/merged-pr-requested-reviewer-never-reviewed/detector.py
```

Run bare like this it uses the real wall clock, so the fixture PRs' own
ages (and therefore which ones clear 24 hours) will drift as real time
passes — expected for a manual demo, not a bug, the same documented
property every age-gated MOCK-only fixture in this repo already carries.
The test suite always pins `now` explicitly so the result stays
deterministic in CI.

It finds one real gap in its own fixture as the elected primary (PR #950's
requested reviewer `@reviewer-a`, confidence 0.85 — merged well over 24
hours before the pinned clock, never once commenting, even though a
different login did leave a comment on the same PR, proving this recipe
tracks the specific named person, not "did anyone comment at all"), two
more weighed in the tail (PR #951's `@reviewer-b` and PR #956's
`@reviewer-g`, both merged only hours before the pinned clock), and
correctly excludes: PR #952 and the fulfilled half of PR #956
(`@reviewer-f`) and PR #958 (`@reviewer-h`) — each requested reviewer did
leave a comment — PR #953 (still open) and PR #957 (closed without
merging) — no resolved promise yet — PR #954 (merged with no requested
reviewer at all) and PR #955 (merged with no recorded `merged_at`,
malformed), and PR #958's own blank requested-reviewer entry.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/merged-pr-requested-reviewer-never-reviewed/recipe.json
```
