# calendar-event-claims-open-milestone

The hundred-fifth real recipe (ROADMAP.md #1382), the thirteenth leg of
the `claims-open-milestone` family, and the fourth leg the
`google_calendar+github` toolkit's own `claims-X` grid has grown, after
[`../calendar-event-claims-unfixed-issue/`](../calendar-event-claims-unfixed-issue/)
(the hundred-second),
[`../calendar-event-claims-unmerged-pr/`](../calendar-event-claims-unmerged-pr/)
(the hundred-third), and
[`../calendar-event-claims-dangling-milestone/`](../calendar-event-claims-dangling-milestone/)
(the hundred-fourth) — the exact recipe that hundred-fourth recipe's own
README named by name: "`claims-open-milestone` and `dangling-reference`
remain open seams for a future recipe, named here rather than silently
assumed closed." This is that future recipe, for the first of the two.

**The seam it watches:** a calendar event's own title or description
invokes a real `milestone #N` claim phrase —
[`seam_engine.milestone_claims.claimed_milestone_numbers`](../../seam_engine/src/seam_engine/milestone_claims.py),
the same grammar every `*-claims-*-milestone` sibling already imports —
naming a milestone that DOES exist, but is still open. The dangling
recipe next door already excludes exactly this shape at confidence 0.0,
by name, deferring the "is the claim itself true" question to this
recipe; this recipe picks up exactly where that one left off.

Two fixtures, no live calendar —
[`../../fixtures/calendar_event_claims_open_milestone/events.json`](../../fixtures/calendar_event_claims_open_milestone/events.json)
and
[`../../fixtures/calendar_event_claims_open_milestone/milestones.json`](../../fixtures/calendar_event_claims_open_milestone/milestones.json)
— shaped like what a real `ListEvents`/`ListMilestones` read would
actually return. Neither scope is new: `ListMilestones` already sits on
`SCOPES.md`'s cleared oath table under the `github` row, used by every
milestone-claim recipe in this engine; `ListEvents` has sat on the
"Google Calendar (v0.2)" row since `milestone-deadline-no-calendar-event`
first declared it, and all three existing Calendar recipes already ask
for it. Zero Google Calendar tools are exposed on the-hand gateway
today — this recipe is fixture-only, MOCK ONLY, and never attempts a
live network call.

A claimed milestone number that does not resolve to a real milestone at
all is excluded here, named not hidden —
[`../calendar-event-claims-dangling-milestone/`](../calendar-event-claims-dangling-milestone/)'s
own seam, not this one's. A claimed milestone that IS closed is
excluded too: the claim was simply true. An event with no
`milestone #N` claim phrase at all (a bare `#N` aside), or no
claim-relevant text at all, never becomes a candidate either.

Confidence is age-gated (0.85 stale / 0.5 fresh, 24-hour bar), keyed
off the event's own `start` time — holds
`calendar-event-claims-unfixed-issue`'s and `email-claims-open-
milestone`'s identical bar exactly, not an independently re-reasoned
number. An open milestone really could close at any moment, so a claim
checked within a day of the event's own start might just be a race the
event hasn't caught up to yet — unlike the dangling recipe's flat 0.8,
the grace period means something here. See `recipe.json`'s
`confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/calendar-event-claims-open-milestone/detector.py
```

Against the shipped fixture it finds one real gap as the elected
primary (event `EVT-O-4801`'s stale claim about milestone #4801,
confidence 0.85 — the milestone is real and still open; a duplicate
claim inside the same event's title+description is de-duplicated to
one candidate, not two), weighs event `EVT-O-4802`'s fresh claim about
milestone #4803 (confidence 0.5) in the tail, while correctly excluding
event `EVT-O-4803` (claims milestone #4802, which is real and closed —
the claim was simply true), event `EVT-O-4804` (claims milestone
#4999, which does not exist at all — that's
`calendar-event-claims-dangling-milestone`'s own seam), and event
`EVT-O-4805` (a bare `#4805` aside, no `milestone #N` claim phrase at
all).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/calendar-event-claims-open-milestone/recipe.json
```
