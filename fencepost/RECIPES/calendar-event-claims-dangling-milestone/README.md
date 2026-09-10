# calendar-event-claims-dangling-milestone

The hundred-fourth real recipe (ROADMAP.md #1380), the thirteenth leg of
the `claims-dangling-milestone` family, and the third leg the
`google_calendar+github` toolkit's own `claims-X` grid has grown, after
[`../calendar-event-claims-unfixed-issue/`](../calendar-event-claims-unfixed-issue/)
(the hundred-second) and
[`../calendar-event-claims-unmerged-pr/`](../calendar-event-claims-unmerged-pr/)
(the hundred-third).

**The seam it watches:** a calendar event's own title or description
invokes a real `milestone #N` claim phrase —
[`seam_engine.milestone_claims.claimed_milestone_numbers`](../../seam_engine/src/seam_engine/milestone_claims.py),
the same grammar every `*-claims-*-milestone` sibling already imports —
but no milestone with that number exists at all.
[`../email-claims-dangling-milestone/`](../email-claims-dangling-milestone/)
(task 1364, the hundred-first) drew the identical line for the Gmail
toolkit: "every other `claims-*` source in this engine ... already
carries all five legs of its own family ... email was the one source
stuck at four." Calendar is the newer toolkit — two legs grown so far,
not five — and this recipe closes one of the three still missing
(`claims-dangling-milestone`; `claims-open-milestone` and
`dangling-reference` remain open seams for a future recipe, named here
rather than silently assumed closed).

It is not a future calendar-side dangling-reference recipe's seam
wearing a new name. Milestones live in their own, separate GitHub number
space from issues and pull requests, so a `#N` that resolves cleanly as
a real issue could still be a dangling *milestone* claim — this recipe
never opens `ListIssues` or `ListPullRequests` at all, only
`ListMilestones`.

Two fixtures, no live calendar —
[`../../fixtures/calendar_event_claims_dangling_milestone/events.json`](../../fixtures/calendar_event_claims_dangling_milestone/events.json)
and
[`../../fixtures/calendar_event_claims_dangling_milestone/milestones.json`](../../fixtures/calendar_event_claims_dangling_milestone/milestones.json)
— shaped like what a real `ListEvents`/`ListMilestones` read would
actually return. Neither scope is new: `ListMilestones` already sits on
`SCOPES.md`'s cleared oath table under the `github` row, used by every
milestone-claim recipe in this engine; `ListEvents` has sat on the
"Google Calendar (v0.2)" row since `milestone-deadline-no-calendar-event`
first declared it, and both existing Calendar recipes already ask for
it. Zero Google Calendar tools are exposed on the-hand gateway today —
this recipe is fixture-only, MOCK ONLY, and never attempts a live
network call.

A claimed milestone number that DOES resolve to a real milestone is
excluded here, named not hidden, whether that milestone is open or
closed — whether the claim itself is true is a future
`calendar-event-claims-open-milestone`'s own seam, not this one's. An
event with no `milestone #N` claim phrase at all (a bare `#N` aside), or
no claim-relevant text at all, never becomes a candidate either.

Confidence is flat (0.8), not age-gated, mirroring every other
`*-claims-dangling-milestone` sibling's own reasoning rather than
`calendar-event-claims-unfixed-issue`'s/`calendar-event-claims-unmerged-pr`'s
24-hour edit-grace bar: an open milestone could close at any moment, so
a fresh claim about it might just be a race the event hasn't caught up
to yet — but a milestone number that does not exist right now will not
spontaneously start existing later, so there is no grace period that
means anything here. See `recipe.json`'s `confidence_notes` for the full
reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/calendar-event-claims-dangling-milestone/detector.py
```

Against the shipped fixture it finds one real gap as the elected primary
(event `EVT-D-4701`'s claim about milestone #4701, confidence 0.8 — no
such milestone exists; a duplicate claim inside the same event's title
+description is de-duplicated to one candidate, not two), while correctly
excluding event `EVT-D-4702` (claims milestone #4702, which is real and
open — no seam, that's a future `calendar-event-claims-open-milestone`'s
own remit), event `EVT-D-4703` (claims milestone #4703, which is real
and closed — the claim was simply true), event `EVT-D-4704` (a bare
`#4704` aside, no `milestone #N` claim phrase at all), and event
`EVT-D-4705` (no claim-relevant text at all).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/calendar-event-claims-dangling-milestone/recipe.json
```
