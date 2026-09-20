# merged-pr-changes-requested-not-addressed

The hundred-twelfth real recipe (ROADMAP.md #1613). A pull request merged
while its own live GitHub review_decision still read CHANGES_REQUESTED —
a reviewer's objection that was never superseded by a later APPROVED
review, a dismissal, or a re-review before the merge button was pressed
anyway.

**The seam it watches:** GitHub renders `review_decision` as a live
aggregate of every review currently in force on a pull request — it
already accounts for a dismissed review and for a later review that
supersedes an earlier one. Nothing about pressing "Merge" ever checks
that field first, and nothing about merging clears or updates it
afterward. `ListPullRequests` alone, read after the fact, is the only way
to see both facts (merged, and still objected-to) held at the same
instant — nothing else on GitHub's own timeline ever cross-checks one
against the other.

Distinct from the closest sibling,
[`../approved-pr-still-unmerged/`](../approved-pr-still-unmerged/): that
recipe watches an APPROVED review that never got its own merge — granted,
but not taken. This recipe watches the opposite silence: a
CHANGES_REQUESTED review that never got its own resolution, yet the pull
request merged anyway. Both share the same one scope
(`ListPullRequests`, review_decision included) and the same excluded-case
discipline — a PR that never merged, or that carries no unresolved
review_decision, made or kept no promise to have missed.

`review_decision` is trusted as GitHub's own live aggregate, not
re-derived from an individual review list — the identical trust
`approved-pr-still-unmerged` already places in the same field. A
repository admin merging over a required review with an explicit
override is a real, legitimate path to this exact state that this recipe
cannot see or second-guess; confidence is capped at 0.8 (below
`tag-never-released`'s 0.85) to reflect that one irreducible blind spot,
never read as an accusation.

One fixture, no live account —
[`../../fixtures/merged_pr_changes_requested_not_addressed/pull_requests.json`](../../fixtures/merged_pr_changes_requested_not_addressed/pull_requests.json)
— shaped like what a real `ListPullRequests` read (with each PR's own
review decision) would return. The one scope is not new: it already sits
on `SCOPES.md`'s cleared oath table under the `github` row, and
`approved-pr-still-unmerged` already reads the identical field off the
identical call.

Confidence is flat 0.8 on a surfaced gap — a merge is a single,
already-complete event, so there is no staleness window to age against
the way a still-open, still-approved PR has (`approved-pr-still-
unmerged`'s own 24h bar exists for exactly that reason, and does not
apply here). A pull request that never merged, or whose review_decision
is not CHANGES_REQUESTED, is excluded at confidence 0.0 — the identical
discipline every recipe before this one holds.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/merged-pr-changes-requested-not-addressed/detector.py
```

It finds one real gap in its own fixture as the elected primary (PR #214,
merged with review_decision still CHANGES_REQUESTED, confidence 0.8),
while correctly excluding PR #221 (merged, but APPROVED — the objection
was resolved), PR #229 (CHANGES_REQUESTED, but never merged — still
open), and PR #233 (merged, but no review_decision was ever recorded —
no promise made).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/merged-pr-changes-requested-not-addressed/recipe.json
```
