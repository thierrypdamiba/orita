# approved-pr-still-unmerged

The ninety-fourth real recipe (ROADMAP.md #1046). [`pr-checklist-complete-still-open`](../pr-checklist-complete-still-open/)
(task 579) proved the shape: a completeness promise nothing ever compares
against the thing that made it — for a PR's own self-declared checklist.
This recipe watches the same silence from the other side of the room: not
what the author claimed, but what a reviewer already granted.

**The seam it watches:** GitHub renders a green "Approved" badge on a PR's
own page the instant a reviewer approves, and does precisely nothing with
that moment — merging is always a separate, human, forgettable step, the
identical "no trigger ever existed to fire" shape [`overdue-milestone-still-open`](../overdue-milestone-still-open/)
and [`stale-branch-no-pr`](../stale-branch-no-pr/) already proved for their
own single-object seams. An approved PR left open is a common, mundane
failure in real teams: the approval lands, the author gets pulled onto
something else, and the merge button just waits.

One fixture, no live account —
[`../../fixtures/approved_pr_still_unmerged/pull_requests.json`](../../fixtures/approved_pr_still_unmerged/pull_requests.json)
— shaped like what `ListPullRequests` (with each PR's own review decision)
would actually return. The one scope already sits on `SCOPES.md`'s cleared
oath table — no new scope is asked for anywhere in this recipe.

Confidence is age-gated on how long the PR's own `updated_at` has sat still
while `review_decision` reads `APPROVED` — 24 hours, mirroring
`pr-checklist-complete-still-open`'s own bar exactly, since a pull request
carries no real "went-approved-at" timestamp either; `updated_at` is the
closest real signal the object exposes. Under 24h scores 0.5 (below the
0.70 confidence bar, weighed in the tail not hidden — the author may
simply not have gotten to the merge button yet). At or past 24h scores a
flat 0.85 — GitHub's own review-decision field is an unambiguous,
non-fuzzy structural read, not a guess. A PR whose review_decision is
`CHANGES_REQUESTED`, `REVIEW_REQUIRED`, or null (no review yet) is excluded
at confidence 0.0, named not hidden — no approval promise was ever made. A
PR that is already merged or closed is excluded at confidence 0.0 too —
the door already resolved, whatever its review decision says.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/approved-pr-still-unmerged/detector.py
```

The shipped fixture (PR #401, approved, last updated well over 24h before
the scan) elects the primary gap for real:

```json
{
  "slug": "approved-pr-still-unmerged-401",
  "headline": "PR #401 has an approving review, but the PR itself never merged",
  "confidence": 0.85
}
```
