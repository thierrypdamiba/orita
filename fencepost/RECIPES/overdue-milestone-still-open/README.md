# overdue-milestone-still-open

The thirty-third real recipe. Every recipe in the `*-still-open` family so
far watches a PROMISE: a "duplicate of #N" note, a closing keyword in a
commit, a merged PR, a released tag. This one watches a promise GitHub
itself lets you make and then never checks: a milestone's own `due_on`
date.

**The seam it watches:** a milestone carries a due date, that date has
passed, and the milestone is still open. GitHub's UI shows the date in
red once it's overdue, but nothing about that redness *does* anything —
no auto-close, no notification, no flag anywhere else in the API. A
milestone set for July 10th and still tracking three open issues on
August 2nd looks, to every other tool reading this repository, exactly
like a milestone due next month. Only holding the milestone's own two
fields — `due_on` and `state` — at once, and comparing them against the
clock, surfaces it at all.

This is a single-toolkit, structural gap, the same shape
[`duplicate-milestone-still-open`](../duplicate-milestone-still-open/)
(task 488) already established for this family: no cross-account join is
needed because GitHub's own API already carries both halves of the
promise (the date, and whether the work closed) and simply never
compares them itself.

One fixture, no live account —
[`../../fixtures/overdue_milestone_still_open/milestones.json`](../../fixtures/overdue_milestone_still_open/milestones.json)
— shaped like what `ListMilestones` would actually return (`due_on` is a
real field GitHub's milestone objects already carry). The one scope
declared, `ListMilestones`, already sits on `SCOPES.md`'s cleared oath
table since day one — no new scope is asked for anywhere in this recipe.

Confidence is age-gated on how long past `due_on` the milestone has run
while still open — mirroring the 24-hour bar every sibling in the
`*-still-open` family already uses rather than inventing a new number:
under 24 hours past due may just be a human closing out the last issue
right now, weighed in the tail at 0.5; at or past 24 hours it is
unambiguous, a flat 0.85. A milestone with no `due_on` set at all is
excluded outright — there is no promise to have broken. A milestone
already closed, or one whose due date hasn't arrived yet, is excluded
too, named not hidden.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/overdue-milestone-still-open/detector.py
```

The shipped fixture (milestone #20, due July 10th, still open with 3 open
issues) elects the primary gap for real:

```json
{
  "slug": "overdue-milestone-still-open-20",
  "headline": "Milestone #20 ('v1.3 Release') was due 2026-07-10, still open with 3 open issue(s)",
  "confidence": 0.85
}
```
