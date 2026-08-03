# milestone-complete-still-open

The thirty-ninth real recipe. The mirror image of
[`overdue-milestone-still-open`](../overdue-milestone-still-open/) (task
489): that recipe watches a milestone's own CLOCK promise go unchecked
(a due date passes, nobody closes it); this one watches its own
COMPLETION promise go unchecked (every issue inside closes, nobody
closes the milestone).

**The seam it watches:** a milestone reads `open_issues == 0` — every
issue or PR assigned to it has closed — while the milestone itself still
reads `state: "open"`. GitHub tracks both counts live, for free, on the
milestone object itself, but never compares them to the state field.
Closing a milestone is always a separate, manual click; nothing on
GitHub's side ever fires it automatically when the last item inside
closes. A milestone finished a month ago and one finished five minutes
ago look, to every other tool reading this repository, exactly alike.
Only holding `open_issues` and `state` at once, and asking whether the
first hit zero while the second still says open, surfaces it at all.

This is a single-toolkit, structural gap, the same shape the rest of the
milestone family (`milestone-closed-issue-still-open`,
`duplicate-milestone-still-open`, `overdue-milestone-still-open`) already
established: no cross-account join is needed because GitHub's own API
already carries both halves of the promise and simply never compares
them itself.

Real milestone objects carry no `completed_at` field — nothing
timestamps the instant `open_issues` hit zero. `updated_at` (which moves
whenever an attached issue changes, including the closing of the last
one) is the closest real signal GitHub actually exposes, so confidence is
age-gated on how long `updated_at` has sat still since — mirroring the
24-hour bar every `*-still-open` sibling already uses rather than
inventing a new number or a new field: under 24 hours may just be a
human who hasn't noticed yet, weighed in the tail at 0.5; at or past 24
hours it's unambiguous, a flat 0.85.

A milestone with zero open AND zero closed issues is excluded outright —
nothing was ever tracked inside it, so there's no completion to have
missed, just an empty milestone. A milestone still carrying open issues
is excluded — it isn't complete yet. A milestone already closed is
excluded too, named not hidden — whatever the timing, the wrap-up
promise was kept.

One fixture, no live account —
[`../../fixtures/milestone_complete_still_open/milestones.json`](../../fixtures/milestone_complete_still_open/milestones.json)
— shaped like what `ListMilestones` would actually return (`open_issues`,
`closed_issues`, and `updated_at` are all real fields GitHub's milestone
objects already carry). The one scope declared, `ListMilestones`,
already sits on `SCOPES.md`'s cleared oath table since day one — no new
scope is asked for anywhere in this recipe.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/milestone-complete-still-open/detector.py
```

The shipped fixture (milestone #30, all 11 issues closed, last touched
2026-07-25) elects the primary gap for real:

```json
{
  "slug": "milestone-complete-still-open-30",
  "headline": "Milestone #30 ('v2.0 Cutover') has all 11 issue(s) closed, but the milestone itself is still open",
  "confidence": 0.85
}
```
