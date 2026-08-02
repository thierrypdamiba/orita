# stale-branch-no-pr

The thirty-fourth real recipe. [`deleted-branch-pr-still-open`](../deleted-branch-pr-still-open/)
(task 485) watches one end of a branch's life: a branch's own promise (an
open PR built on it) surviving after the branch itself is deleted. This
recipe watches the other end -- a branch that exists, carries real work,
and never had a pull request opened from it at all.

**The seam it watches:** GitHub's own branch list shows how far a branch
has drifted from the default branch (`N commits ahead`), but nothing in
the UI or the API ever flags a branch nobody turned into a pull request.
A spike, a fix, an experiment -- real, reviewable work -- can sit on a
branch indefinitely, invisible next to every other branch that did get
opened for review. Only holding the repository's own Activity feed (which
`branch_creation` events fired, and when) against the live PR list at the
same instant, and checking whether ANY pull request -- open, closed, or
merged -- ever named that ref as its `head_ref`, surfaces it at all.

Two fixtures, no live account --
[`../../fixtures/stale_branch_no_pr/activities.json`](../../fixtures/stale_branch_no_pr/activities.json)
and
[`.../pull_requests.json`](../../fixtures/stale_branch_no_pr/pull_requests.json)
-- shaped like what `ListRepositoryActivities`/`ListPullRequests` would
actually return. Both scopes already sit on `SCOPES.md`'s cleared oath
table, the same pairing `deleted-branch-pr-still-open` already
established -- no new scope is asked for anywhere in this recipe.

Confidence is age-gated on how long the branch has existed with no PR
ever pointing at it, mirroring `merged-pr-never-released`'s and
`issue-closed-never-released`'s own 96-hour bar rather than
`deleted-branch-pr-still-open`'s shorter 24-hour one: under 96 hours may
just be in-progress work nobody has opened for review yet, weighed in the
tail at 0.5; at or past 96 hours it is unambiguous, a flat 0.85. The
repository's own default branch (`main`/`master`) is excluded outright --
there is no promise a default branch makes to become a pull request
against itself. A branch already claimed by a pull request in ANY state
(open, closed, or merged) is excluded too, named not hidden -- the
promise being watched here ("was this ever turned into reviewable work at
all") is already kept the moment one exists, whatever happened to it
since.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/stale-branch-no-pr/detector.py
```

The shipped fixture (`spike/rate-limit-cache`, created five days before
the scan with no PR ever opened from it) elects the primary gap for real:

```json
{
  "slug": "stale-branch-no-pr-spike-rate-limit-cache",
  "headline": "Branch 'spike/rate-limit-cache' exists, but no pull request has ever been opened from it",
  "confidence": 0.85
}
```
