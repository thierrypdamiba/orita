# calendar-event-claims-unmerged-pr

The hundred-third real recipe, and the second leg the Calendar toolkit's
own `claims-X` grid has grown. [`../calendar-event-claims-unfixed-issue/`](../calendar-event-claims-unfixed-issue/)
(task 1258, the hundred-second real recipe) opened the first leg — a
calendar event's closing-keyword claim against the issue tracker. This
recipe closes a second, separate cell: a calendar event's own
`ships`/`includes`/`merges`/`via #N` claim against the PR tracker. Two
different GitHub number spaces, two different claim grammars — one
recipe's clean bill never speaks for the other's.

**The seam it watches:** the Calendar-side twin of
[`../mention-claims-unmerged-pr/`](../mention-claims-unmerged-pr/) (the
X-mention leg), [`../slack-message-claims-unmerged-pr/`](../slack-message-claims-unmerged-pr/)
(the Slack-channel leg), and [`../linear-comment-claims-unmerged-pr/`](../linear-comment-claims-unmerged-pr/)
(the Linear-comment leg) of the `claims-unmerged-pr` family. A calendar
event's own title or description invokes a real "ships/includes/merges/via
#N" claim phrase against a pull request — "ships #601 finally", "heard
this merges #603" — but PR #N is not actually merged. A meeting note or
agenda line sitting on a connected calendar is exactly as durable and
readable-later as a Slack message, a Linear comment, a tweet, or a
mention once created, and nothing on either platform ever checks it
against the PR tracker's real state. Two fixtures, no live calendar —
[`../../fixtures/calendar_event_claims_unmerged_pr/events.json`](../../fixtures/calendar_event_claims_unmerged_pr/events.json)
and
[`.../pulls.json`](../../fixtures/calendar_event_claims_unmerged_pr/pulls.json)
— shaped like what a real `ListEvents`/`ListPullRequests` read would
return.

`ListPullRequests` is already cleared on `SCOPES.md`'s oath table under
the `github` row. `ListEvents` is not a new scope either — it has sat on
`SCOPES.md`'s "Google Calendar (v0.2)" row since
`milestone-deadline-no-calendar-event` first declared it, and
`calendar-event-claims-unfixed-issue` already asks for it too. Zero
Google Calendar tools are exposed on the-hand gateway today, the same WIP
shape `SCOPES.md` already documents. This recipe is fixture-only, MOCK
ONLY, and never attempts a live network call.

A claimed PR that doesn't exist at all is excluded here, named not
hidden — that broken reference is a future calendar-side
dangling-reference recipe's own seam, not this one's. A claimed PR that
IS merged is excluded too — the claim was simply true. An event with no
`ships`/`includes`/`merges`/`via` claim phrase at all never becomes a
candidate either — it never claims anything about a second record, so
there is no seam to weigh. Nothing in this recipe's own `headline`/
`detail` text ever names or grades whoever created the event —
`CONTRIBUTING.md`'s "No grading, ever" law, same as every recipe in this
engine.

Reuses `seam_engine.pr_claims.claimed_pr_numbers` verbatim — the same
shared "ships/includes/merges/via #N" grammar every `claims-unmerged-pr`
sibling already imports — rather than a ninth independently retyped copy
of the identical pattern.

**Confidence holds `calendar-event-claims-unfixed-issue`'s own 0.85/0.5
bar exactly** — not an independently re-reasoned number just because the
target changed from an issue to a PR. Age-gated by hours since the
event's own `start`: a claim checked within 24 hours of the meeting might
still be a race (the real merge landing moments after) rather than a
settled overclaim (0.5, below the confidence bar, shown as a weighed
coincidence, not hidden). At or past 24 hours with the named PR still
unmerged, it is unambiguous (flat 0.85). The check itself is objective:
the claimed PR's own live `merged`/`state` fields, verified against
`ListPullRequests`, not a guess about which tracker the organizer meant.
See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/calendar-event-claims-unmerged-pr/detector.py
```

Run bare like this it uses the real wall clock, so the fixture events'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (`EVT-4201`'s claim
about #601, confidence 0.85, its own duplicated "ships #601 ... via #601"
claim deduplicated to a single candidate, not two) and weighs one
coincidence in the tail (`EVT-4202`'s claim about #603, confidence 0.5,
timed a few hours before the pinned test clock), while correctly
excluding `EVT-4203`'s claim about #602 (true — merged), `EVT-4204`'s
claim about #999 (no such PR exists), and `EVT-4205` (no claim phrase at
all, just a bare "#605" mention).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/calendar-event-claims-unmerged-pr/recipe.json
```
