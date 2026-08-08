# commit-closes-keyword-issue-closed-not-planned

The sixty-second real recipe (ROADMAP.md #594).
[`../commit-closes-keyword-issue-still-open/`](../commit-closes-keyword-issue-still-open/)
(task 388) proved a commit's own closing keyword is a real, live GitHub
auto-close trigger worth watching independent of any pull request -- but
that recipe, like every one of the sixty-one recipes shipped before this
one, only ever asks "did the target close at all?" This recipe asks a
sharper question of the same surface, off a field none of them has ever
read: **why** did it close?

**The seam it watches:** a commit already on the default branch names a
real GitHub closing keyword ("fixes/closes/resolves #N") for an issue.
The issue really did close, so a check that stops at `state == "closed"`
would call the promise kept. But GitHub records a second fact alongside
`state` -- `state_reason`, one of `"completed"`, `"not_planned"`, or
`null` -- and when it reads `"not_planned"`, the issue closed for a
reason that has nothing to do with the commit's own claim: a maintainer
declined it, folded it into a duplicate, or ruled it out of scope. The
commit's permanent message still says it fixed something it never fixed,
and nothing on GitHub's side ever revisits that commit once the issue
closes for the unrelated reason -- closing `not_planned` touches no
commit, no changelog, no release note that once named the issue.

This is careful not to re-litigate `commit-closes-keyword-issue-still-
open`'s own seam: that recipe's whole surfaced set is issues that are
still open; this recipe's whole surfaced set is issues that are closed,
specifically with `state_reason=not_planned`. The two sets are provably
disjoint -- the same commit/issue pair can never appear in both recipes'
output, since one requires `state == "open"` and the other requires
`state == "closed"`. Nor does it overreach into `dangling-issue-
reference`'s seam (a target that does not exist) or make any claim about
who closed the issue or why they chose to -- the no-grading law holds
exactly as it does for every sibling: the headline names a commit, an
issue number, and a recorded reason, never a person.

Two fixtures, no live account --
[`../../fixtures/commit_closes_keyword_issue_closed_not_planned/commits.json`](../../fixtures/commit_closes_keyword_issue_closed_not_planned/commits.json)
and
[`../../fixtures/commit_closes_keyword_issue_closed_not_planned/issues.json`](../../fixtures/commit_closes_keyword_issue_closed_not_planned/issues.json)
-- shaped like what `ListRepoCommits`/`ListIssues` would actually return,
the issues fixture carrying the real `state_reason` field GitHub's own
Issues API returns. Both scopes already sit on `SCOPES.md`'s cleared oath
table, the identical pair `commit-closes-keyword-issue-still-open`
already established for this exact shape of recipe -- no new scope is
asked for anywhere in this recipe.

Confidence is age-gated on how long the issue has sat closed
`not_planned` while the commit's own message still credits it, reusing
`commit-closes-keyword-issue-still-open`'s and `unblocked-issue-still-
open`'s own 24-hour bar rather than inventing a new number for a
structurally similar family: under 24 hours may just be a mismatch nobody
has had time to notice yet, weighed in the tail at 0.5; at or past 24
hours it is unambiguous, a flat 0.85. A commit naming no closing keyword,
naming an issue that does not exist, or naming an issue that is still
open is excluded, named not hidden. A closed issue with
`state_reason=completed` is excluded too -- the promise actually held. A
closed issue with no recorded reason, or an unrecognized one, is excluded
as unproven rather than guessed into either bucket. See `recipe.json`'s
`confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/commit-closes-keyword-issue-closed-not-planned/detector.py
```

Run bare like this it uses the real wall clock, so the fixture issues'
ages (and therefore which ones clear 24 hours) will drift as real time
passes -- expected for a manual demo, not a bug, the same documented
property every age-gated MOCK-only fixture in this repo already carries.
The test suite always pins `now` explicitly so the result stays
deterministic in CI.

It finds one real gap in its own fixture as the elected primary (commit
`a1c701d`'s claim on issue #701, confidence 0.85 -- closed `not_planned`
well over 24 hours before the pinned clock), a second real gap weighed in
the tail (commit `b2c702d`'s claim on issue #702, closed `not_planned`
only hours before the pinned clock) alongside a third (commit `j1c708d`'s
own claim on issue #710, closed `not_planned` even more recently), and
correctly excludes: issue #703 (closed `completed` -- the promise
actually held, referenced by two different commits, `c3c703d` and
`j1c708d`), issue #704 (still open -- the sibling recipe's own seam),
issue #999 (referenced but does not exist -- `dangling-issue-reference`'s
own seam), commits `f6c705d` and `i9c701d` (no real closing keyword at
all), issue #706 (closed with no recorded `state_reason`), issue #707
(closed `not_planned` but with no close timestamp -- a malformed record),
and issue #709 (closed with an unrecognized `state_reason`, `"duplicate"`
-- not guessed into either bucket).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/commit-closes-keyword-issue-closed-not-planned/recipe.json
```
