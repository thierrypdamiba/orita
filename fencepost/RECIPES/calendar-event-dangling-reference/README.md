# calendar-event-dangling-reference

The hundred-sixth real recipe (ROADMAP.md #1383), the twelfth leg of the
dangling-reference family: [`../dangling-issue-reference/`](../dangling-issue-reference/)
watches commit messages, [`../mention-dangling-reference/`](../mention-dangling-reference/)
watches X mentions, [`../release-note-dangling-reference/`](../release-note-dangling-reference/)
watches release notes, [`../issue-body-dangling-reference/`](../issue-body-dangling-reference/)
watches issue/PR opening bodies, [`../milestone-body-dangling-reference/`](../milestone-body-dangling-reference/)
watches milestone descriptions, [`../own-tweet-dangling-reference/`](../own-tweet-dangling-reference/)
watches the town's own tweets, [`../review-comment-dangling-reference/`](../review-comment-dangling-reference/)
watches a PR's own inline review comments,
[`../issue-comment-dangling-reference/`](../issue-comment-dangling-reference/)
watches the ordinary issue/PR timeline conversation,
[`../linear-comment-dangling-reference/`](../linear-comment-dangling-reference/)
watches a Linear comment, [`../slack-message-dangling-reference/`](../slack-message-dangling-reference/)
watches a Slack message, and [`../email-dangling-reference/`](../email-dangling-reference/)
watches an inbound email. None of the eleven ever read a Google Calendar
event.

**Why this recipe exists:** [`../calendar-event-claims-unfixed-issue/`](../calendar-event-claims-unfixed-issue/)'s
own `detector.py` docstring named this seam and deliberately left it
open: *"A named issue that does not exist at all is excluded here -- a
broken reference is a future calendar-side dangling-reference recipe's
own seam, not this one's."* This is that recipe. With it, the
`google_calendar+github` toolkit's own `claims-X`/dangling-reference grid
now names all three of the seams
[`../calendar-event-claims-dangling-milestone/`](../calendar-event-claims-dangling-milestone/)'s
own docstring left open: `claims-dangling-milestone` (task 1380),
`claims-open-milestone` (task 1382), and `dangling-reference` (here).

**The seam it watches:** every bare `#N` reference inside a calendar
event's own title or description — not just a closing-keyword claim like
its sibling `calendar-event-claims-unfixed-issue`, but any reference at
all ("any movement on #N", "saw #N land in the changelog") — checked
against BOTH the live issue list and the live PR list. GitHub shares one
number sequence between issues and pull requests, so a reference must be
checked against both lists or it would misfire on a perfectly good
reference to a merged PR — the exact crying-wolf failure Ògún's law calls
fatal. Three fixtures, no live calendar —
[`../../fixtures/calendar_event_dangling_reference/events.json`](../../fixtures/calendar_event_dangling_reference/events.json),
[`.../issues.json`](../../fixtures/calendar_event_dangling_reference/issues.json),
and [`.../pulls.json`](../../fixtures/calendar_event_dangling_reference/pulls.json)
— shaped like what a real `ListEvents`/`ListIssues`/`ListPullRequests`
read would actually return.

It is not the same seam as `calendar-event-claims-dangling-milestone`
wearing a new name. Milestones live in their own, separate GitHub number
space from issues and pull requests, so a `#N` that resolves cleanly as a
real milestone could still be a dangling issue/PR reference, and vice
versa — this recipe never opens `ListMilestones` at all, only
`ListIssues`/`ListPullRequests`.

Reuses `seam_engine.references.referenced_numbers` verbatim — the one
shared `#N`-extraction grammar every dangling-reference sibling already
imports from the same place, the same cross-repo `owner/repo#N`
exclusion every sibling already holds.

Neither `ListIssues` nor `ListPullRequests` is a new scope: both already
sit on `SCOPES.md`'s cleared oath table under the `github` row, used by
every dangling-reference and claims-* recipe in this engine. `ListEvents`
has sat on the "Google Calendar (v0.2)" row since
`milestone-deadline-no-calendar-event` first declared it, and all four
existing Calendar recipes already ask for it. Zero Google Calendar tools
are exposed on the-hand gateway today — this recipe is fixture-only,
MOCK ONLY, and never attempts a live network call.

A reference matching a real issue or PR is excluded here, named not
hidden — the reference was simply good. An event with no `#N` reference
at all never becomes a candidate either — it never claims anything about
a second record, so there is no seam to weigh. Nothing in this recipe's
own `headline`/`detail` text ever names or grades the organizer —
`CONTRIBUTING.md`'s "No grading, ever" law, same as every recipe in this
engine.

Confidence is flat (0.75), not age-gated — `email-dangling-reference`'s
own exact score, not an independently re-reasoned number just because the
reading surface is Calendar rather than Gmail: an organizer's own free
text may simply be numbering a different tracker in their own head. See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/calendar-event-dangling-reference/detector.py
```

Against the shipped fixture it elects one primary gap (`EVT-R-4801`'s
reference to #4501, confidence 0.75, no tail coincidence), while
correctly excluding `EVT-R-4802`'s reference to #4102 (a real closed
issue) and `EVT-R-4805`'s reference to #4103 (a real merged PR), and
producing no candidate at all for `EVT-R-4803` (a cross-repo
`arcadeai/gasstation#42` reference) or `EVT-R-4804` (no `#N` reference
whatsoever).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/calendar-event-dangling-reference/recipe.json
```
