# duplicate-milestone-still-open

The thirty-second real recipe, and the third leg of the
`duplicate-*-still-open` family alongside
[`../duplicate-issue-still-open/`](../duplicate-issue-still-open/) (task
376, the seventh real recipe) and
[`../duplicate-pr-still-open/`](../duplicate-pr-still-open/) (task 400, the
twenty-second). Both of those watch an explicit PROMISE: a mortal, or a
god, writes "duplicate of #N" in an issue or PR's own body, and GitHub
gives that promise no auto-close wiring at all, so it can sit unresolved
forever. Milestones have no equivalent convention — nobody writes
"duplicate of milestone #N" in a milestone description in real practice, so
there is no prose marker here to extract.

**The seam it watches is structural instead, and arguably more
surprising:** GitHub enforces **no uniqueness constraint on milestone
titles whatsoever**. Two, three, any number of open milestones in the same
repository can carry the byte-identical title indefinitely, and nothing in
GitHub's own UI or API ever flags it. A milestone gets created, forgotten,
and quietly re-created under the same name weeks later — now the same body
of work is tracked in two open places at once, issues and PRs split
between them, and neither milestone alone shows this. Only holding the
full milestone list at once does. One fixture, no live account —
[`../../fixtures/duplicate_milestone_still_open/milestones.json`](../../fixtures/duplicate_milestone_still_open/milestones.json)
— shaped like what `ListMilestones` would actually return, already on
`SCOPES.md`'s cleared oath table. No new scope is asked for anywhere in
this recipe.

Only currently-**open** milestones are ever compared against each other for
a live duplicate pair. A title reused after the first milestone bearing it
already closed is the ordinary, unremarkable case — whatever redundancy
existed already resolved itself, or the name was deliberately reused for
the next cycle of work — not this recipe's seam. A title held by exactly
one milestone in the whole repo, open or closed, is excluded too, named
not hidden: there is nothing for it to collide with.

Confidence is age-gated on how long the later (duplicate) milestone has
existed, matching both siblings' own 24-hour bar rather than inventing a
new number for a structurally similar family: under 24 hours since it was
created scores 0.5 (below the 0.70 bar, weighed in the tail not hidden — a
human may be mid-cleanup, about to close or rename one of the two within
the day); at or past 24 hours it scores a flat 0.85. See `recipe.json`'s
`confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/duplicate-milestone-still-open/detector.py
```

Run bare like this it uses the real wall clock, so the fixture milestones'
ages will drift as real time passes — expected for a manual demo, not a
bug, the same documented property every age-gated MOCK-only fixture in
this repo already carries. The test suite
(`seam_engine/tests/test_duplicate_milestone_still_open_detector.py`)
always pins `now` explicitly so the result stays deterministic in CI.

It finds one real gap in its own fixture (milestone #9 duplicating #8's
title "Fencepost v0.2", both open, #9 created well over 24 hours before the
pinned clock — confidence 0.85) and correctly excludes #1/#5 ("v1.0
Launch" — #1 already closed, so at most one of the pair currently reads
open) and #12 ("Beta feedback" — the only milestone with that title), while
#14 (duplicating #13's "Docs cleanup" title, created only hours before the
pinned clock) is weighed and shown in the tail as a coincidence, not hidden
and not electing itself primary.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/duplicate-milestone-still-open/recipe.json
```
