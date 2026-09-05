# calendar-event-claims-unfixed-issue

The hundred-second real recipe, and the first to read a Google Calendar
event's own title/description as a claim-bearing text surface. Grepped
every one of the 101 recipes before it (`python3 -c "..."` over every
`RECIPES/*/recipe.json`'s own `toolkit` field): `google_calendar` appears
in exactly one place —
[`../milestone-deadline-no-calendar-event/`](../milestone-deadline-no-calendar-event/)'s
own `github+google_calendar` — and that recipe never parses an event's own
free text at all; it only matches an event's title against a milestone's
`due_on` date by keyword-overlap and a time window. This recipe proposes
the same `google_calendar+github` toolkit for a different seam:
[`../../CONTRIBUTING.md`](../../CONTRIBUTING.md)'s own "New toolkits"
section sanctions exactly this, the same way
[`../email-claims-unfixed-issue/`](../email-claims-unfixed-issue/) opened
Gmail's own first text-reading recipe.

**The seam it watches:** the Calendar-side twin of
[`../mention-claims-unfixed-issue/`](../mention-claims-unfixed-issue/) (the
X-mention leg), [`../slack-message-claims-unfixed-issue/`](../slack-message-claims-unfixed-issue/)
(the Slack-channel leg), [`../linear-comment-claims-unfixed-issue/`](../linear-comment-claims-unfixed-issue/)
(the Linear-comment leg), and [`../email-claims-unfixed-issue/`](../email-claims-unfixed-issue/)
(the Gmail leg) of the `claims-unfixed-issue` family. A calendar event's
own title or description uses a real GitHub closing-keyword phrase against
an issue number — "quick sync -- fixes #4101 and closes #4101 again,
should be all set now", "resolves #4103 with the migration script, nice"
— but issue #N is still open. A meeting note or agenda line sitting on a
connected calendar is exactly as durable and readable-later as a tweet, a
mention, a Slack message, a Linear comment, or an email once created, and
nothing on Calendar's side (or GitHub's) ever checks it against the issue
tracker's real state. Two fixtures, no live calendar —
[`../../fixtures/calendar_event_claims_unfixed_issue/events.json`](../../fixtures/calendar_event_claims_unfixed_issue/events.json)
and
[`.../issues.json`](../../fixtures/calendar_event_claims_unfixed_issue/issues.json)
— shaped like what a real `ListEvents`/`ListIssues` read would return.

`ListIssues` is already cleared on `SCOPES.md`'s oath table under the
`github` row. `ListEvents` is not a new scope — it has sat on `SCOPES.md`'s
"Google Calendar (v0.2)" row since `milestone-deadline-no-calendar-event`
first declared it — but this is the first recipe to actually read an
event's own text rather than only its start time. Zero Google Calendar
tools are exposed on the-hand gateway today, the same WIP shape `SCOPES.md`
already documents. This recipe is fixture-only, MOCK ONLY, and never
attempts a live network call.

A claimed issue that doesn't exist at all is excluded here, named not
hidden — that broken reference is a future calendar-side dangling-reference
recipe's own seam, not this one's. A claimed issue that IS closed is
excluded too — the claim was simply true. An event with no closing-keyword
phrase at all (a bare "see #N" mention, or no `#N` at all) never becomes a
candidate either — it never claims anything about a second record, so
there is no seam to weigh. Nothing in this recipe's own `headline`/`detail`
text ever names or grades whoever created the event —
`CONTRIBUTING.md`'s "No grading, ever" law, same as every recipe in this
engine.

Reuses `seam_engine.closing_keywords.CLOSING_KEYWORD_RE` verbatim — the
same shared grammar `email-claims-unfixed-issue` and its
`claims-unfixed-issue` siblings already import — rather than a
seventeenth independently retyped copy of the identical pattern.
"Closing #N" (present participle) never matches either tense here either,
same as everywhere else this grammar is used. The claim is extracted from
`title + " " + description` combined: a short claim can sit in either
field, and nothing about one is less durable than the other.

**Confidence holds `email-claims-unfixed-issue`'s/`mention-claims-unfixed-
issue`'s/`slack-message-claims-unfixed-issue`'s/`linear-comment-claims-
unfixed-issue`'s own 0.85/0.5 bar exactly — not an independently
re-reasoned number just because the toolkit's text-reading door is new.**
Age-gated by hours since the event's own `start`: a claim checked within
24 hours of the meeting might still be a race (the real fix landing
moments after) rather than a settled overclaim (0.5, below the confidence
bar, shown as a weighed coincidence, not hidden). At or past 24 hours with
the named issue still open, it is unambiguous (flat 0.85). The check
itself is objective: the claimed issue's own live `state` field, verified
against `ListIssues`, not a guess about which tracker the organizer meant.
See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/calendar-event-claims-unfixed-issue/detector.py
```

Run bare like this it uses the real wall clock, so the fixture events'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture it elects one primary gap (`EVT-4101`'s claim
about #4101, confidence 0.85, its own duplicated "fixes #4101 ... closes
#4101" claim deduplicated to a single candidate, not two) and weighs one
coincidence in the tail (`EVT-4102`'s claim about #4103, confidence 0.5,
timed a few hours before the pinned test clock), while correctly excluding
`EVT-4103`'s claim about #4102 (true — closed), `EVT-4104`'s claim about
#4999 (no such issue exists), and `EVT-4105` (no closing-keyword claim at
all, just a bare "#4105" mention).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/calendar-event-claims-unfixed-issue/recipe.json
```
