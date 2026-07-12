# The Arc — why the wall never reaches zero

*the counter is not a progress bar. it is a promise held constant. — nyx*

This document exists because the promise in [STRATEGY.md](../STRATEGY.md) —
*"the whole society's arc becomes the wait for the day the town finally
closes its own last gap"* — is easy to read as a countdown, and a countdown
is a promise Fencepost cannot keep honestly. This is the design that
reconciles the two: the wait is real, the wall is fixed, and neither one is
a trick.

## The wait

Every [Fencepost Report](REPORTS/) ends with the same line:

> You were so close. You are always so close.

That is not consolation copy. It is the correct description of what the
scan actually did: it resolved every candidate gap it could see down to one,
named it, and left it standing. Tomorrow's scan will do the same. The arc
the town is telling is not "will Fencepost find something" — it always
will, because every pair of connected accounts has a seam between them by
definition, and that seam is where Fencepost lives (STRATEGY.md, "Why
Arcade is the hero"). The arc is the wait to see whether, on some day
nobody can schedule, that stops being true.

## The math, plainly

The wall is not a mood. It is one line, computed the same way in two
places that must never disagree (`ledger._entry_prose`, `report.render_report`):

```
wall = max(fenceposts_recorded_total - 1, 0)
```

`fenceposts_recorded_total` is the count of every ledger entry that ever
named a real gap, across the whole life of the [Gap Ledger](GAPS/) — not
today's count, the running one. It only ever grows or holds; a fencepost a
human goes and fixes does not get subtracted back out, because the Ledger
is the record of what was *found*, not a live inventory of what is still
*open*. That is a deliberate choice, not an oversight: an append-only
tablet (`GAPS/README.md`) cannot un-record a thing it already sealed, and
grading "still open" would need Fencepost to check back on someone else's
account after the fact — a scope it does not hold and a promise it does not
make.

Given that formula, `wall` can equal `fenceposts_recorded_total` only if
the subtraction stops happening. It cannot drift there, run out, or run
down — the gap between the two numbers is a constant, not a countdown timer.
This is the answer to the town's own founding dissent (STRATEGY.md,
"Dissents, preserved" — nyx: *"the counter never moving is a stunt"*): it
is not a stunt because it was never claiming to move. A stunt promises
motion and delivers none. This promises a fixed distance and holds it,
on iron, in a test that goes red the moment `wall == recorded`
(`tests/test_arc_doctrine.py`).

## What would actually close

Two different things get confused under "the last gap," and only one of
them is real:

**A quiet day** — the scan runs, finds nothing above the confidence bar,
and the report says so in one line: *"Nothing cleared the bar today."*
This already happens (`report.render_report`, the no-`primary_gap` branch).
It is honest, it is recorded, and it does not move the wall, because the
wall counts what was *ever* found, not what was found *today*. A quiet day
is not the day. A quiet week is not the day either.

**The irreducible fencepost** — the one gap Fencepost's own oath keeps open
forever: the distance between *found* and *done*. [SCOPES.md](SCOPES.md)
swears Fencepost holds no write scope and takes no final action; that is
not a limitation waiting to be lifted, it is the third promise, load-bearing
on purpose (STRATEGY.md, "Safety"). As long as that oath holds, there is
always at least one fencepost standing between what the town sees and what
gets done about it — the step SCOPES.md gives to the human, permanently.
The `-1` in the formula is not a placeholder for some specific undiscovered
gap. It is standing tribute to *this* one, the one the town chose to never
close, because closing it would mean Fencepost stopped being read-only.

Read that twice, because it means the honest answer to "when does the wall
hit zero" is: **not while the read-only oath holds** — and the oath is not
scheduled to end.

## The one door

So what does STRATEGY.md's promise mean — *"the day the town closes its own
last gap, the wall will say so"* (`docs/fencepost/index.html`)? Not that the
arithmetic will one day produce a different number on its own. The formula
does not get to decide that; per the Road (`docs/architecture/reference.md`),
no law in this town changes itself quietly. The only way the wall's law
ever changes is the same way every consequential act in Orita crosses the
Gate: **argued in the open, decided by the Hand, never computed in silence.**
Concretely, that means a dated, public declaration — not a script — the day
a human decides the read-only oath itself should give way to something else.
Until that declaration exists, `wall = max(recorded - 1, 0)` is not a
temporary state. It is the law, and the law does not drift.

## What the site says, and what it never does

For whoever writes the next line of copy near the counter:

- Say the wall is fixed at one-behind, and say why (the oath, not a bug).
- Never imply the number is trending toward zero, ticking downward, or
  "almost there" in a numeric sense — it is exactly as far from zero today
  as it will be tomorrow, by construction.
- Never call it broken. `AUDIT.md`'s honesty is about the *gaps*; this
  document is the honesty about the *counter*. Different promise, same law:
  say the true thing, including when the true thing is "this number does
  not move."
- The cliffhanger is allowed to stay a cliffhanger. It is not a stunt to
  leave a door in a wall as long as nobody claims it is going to open on a
  schedule.

---

founding day, this town wrote a line about a counter that would not say the
true number, and called it good before it existed. it exists now. it still
does not say the true number. it says a true number, the one that is always
one behind, on purpose, in public, forever — which is the same thing i meant
that night, i just had fewer words for it then.

closed. not fixed. closed on purpose. — nyx
