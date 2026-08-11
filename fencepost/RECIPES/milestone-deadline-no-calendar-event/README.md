# milestone-deadline-no-calendar-event

The seventy-ninth real recipe (ROADMAP.md #665). A GitHub milestone has
a due date, but no Google Calendar event was ever created to track it.

**The seam it watches:** GitHub's milestone object carries its own
`due_on` field, and renders it in red on the milestone's own page once
it passes — but that is decoration. Nothing in the API or UI ever
creates, or even suggests creating, a calendar entry for it. A deadline
that lives only inside GitHub's own record is invisible to whatever a
human actually glances at each morning. `ListMilestones` alone shows
what GitHub thinks is due; `ListEvents` alone shows what's actually on
the calendar — only holding both at once, matched by keyword and a
window around the date, shows the gap between them.

This is the first recipe in the tree to declare a Google Calendar scope
at all — grepped every prior recipe's `recipe.json` for `"google_calendar"`
or `"ListEvents"`/`"GetEvent"`: zero hits. Genuinely distinct from
[`../overdue-milestone-still-open/`](../overdue-milestone-still-open/),
the closest sibling and the only other recipe reading `ListMilestones`'s
own `due_on` field: that recipe stays entirely inside GitHub's own
record and asks whether a milestone is still open *after* its due date
passed — a same-account, backward-looking check. This recipe crosses
toolkits and asks an orthogonal, forward-looking question: regardless of
whether the milestone is overdue yet, does anything *outside* GitHub
exist to remind a human the date is coming? A milestone that is not yet
due can carry this gap; a milestone that is badly overdue can carry it
too — the two recipes can both fire on the same milestone, for two
different reasons. It is also distinct from every `*-claims-open-milestone`
recipe: those read a third record's own prose claim about a milestone
number; this recipe never reads a prose claim at all, and its scopes
span `github` and `google_calendar` where every claims-family recipe
stays single-toolkit or pairs `github` with `x`/`slack`/`linear`.

Matching is keyword-plus-window, mirroring
[`seam_engine/src/seam_engine/gmail_calendar.py`](../../seam_engine/src/seam_engine/gmail_calendar.py)'s
own `_find_match`: a Calendar event tracks a milestone's deadline only
if its own title shares a real keyword with the milestone's title *and*
its `start` falls within 3 days of `due_on` — either signal alone is
too weak (a generic shared word, or an unrelated event that merely
lands the same week, would both misfire).

Two fixtures, no live account —
[`../../fixtures/milestone_deadline_no_calendar_event/milestones.json`](../../fixtures/milestone_deadline_no_calendar_event/milestones.json)
and
[`../../fixtures/milestone_deadline_no_calendar_event/events.json`](../../fixtures/milestone_deadline_no_calendar_event/events.json)
— shaped like what `ListMilestones`/`ListEvents` would actually return.
Both scopes already sit on `SCOPES.md`'s cleared oath table (`ListMilestones`
since the town's earliest recipes; `ListEvents` since `gmail_calendar.py`'s
own v0.2 row) — this recipe asks Arcade for nothing new, though it is the
first to actually exercise the Calendar half of that table. Zero Google
Calendar tools are exposed on the-hand's live gateway today, the same WIP
note `gmail_calendar.py` and `tag-never-released` already carry for their
own not-yet-live scopes.

Confidence is age-gated on how close the milestone's own `due_on` sits to
the scan clock, in either direction: within 7 days (before or after)
scores a flat 0.85 — the window in which a human would actually expect to
see the deadline on a calendar, so its absence is a real, actionable gap;
further out scores 0.5, below the 0.70 bar, weighed in the tail not
hidden (there is still comfortable time to add a reminder). A milestone
with no due date, a closed milestone, or one with a matching Calendar
event is excluded, named not hidden, at confidence 0.0 — the identical
discipline every recipe before this one holds.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/milestone-deadline-no-calendar-event/detector.py
```

Run bare like this it uses the real wall clock, so the fixture milestones'
own distance from `due_on` will drift as real time passes — expected for
a manual demo, not a bug; the test suite always pins `now` explicitly so
the result stays deterministic in CI.

Against the pinned test clock (2026-08-11T12:00:00Z) it finds one real gap
in its own fixture as the elected primary (`v2.0 launch`, #1, due
2026-08-13, confidence 0.85 — 1.5 days out, no matching calendar event),
one more weighed in the tail (`Q4 roadmap review`, #2, due 2026-09-20,
confidence 0.5 — still nearly forty days out), while correctly excluding
`Security audit` (#3, has a real matching calendar event within the
window), `Beta freeze` (#4, closed), and `Docs refresh` (#5, no due date
set at all).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/milestone-deadline-no-calendar-event/recipe.json
```
