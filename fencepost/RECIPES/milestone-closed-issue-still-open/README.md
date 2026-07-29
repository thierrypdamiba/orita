# milestone-closed-issue-still-open

The tenth real recipe. Every recipe before this one watches a seam tied to a
PR, a commit, a release, or a duplicate marker's own prose. This one
watches an entirely different GitHub record pair: a milestone and the
issues assigned to it.

**The seam it watches:** a milestone reads `state=closed`, but one of the
issues assigned to it still reads `state=open`. Closing a milestone on
GitHub is a pure label operation — it never touches the state of a single
issue inside it, so there is no auto-close wiring here at all, not even a
broken one (the same "no trigger ever existed to fire" shape
`duplicate-issue-still-open`, task 376, already named for a duplicate
marker). A human (or a god) closes the milestone believing the work inside
it is done, and an issue left open inside it is the exact seam this recipe
watches — it exists only by holding the milestone record and the issue
record at the same instant, neither alone shows it. Two fixtures, no live
account — [`../../fixtures/milestone_closed_issue_still_open/milestones.json`](../../fixtures/milestone_closed_issue_still_open/milestones.json)
and [`../../fixtures/milestone_closed_issue_still_open/issues.json`](../../fixtures/milestone_closed_issue_still_open/issues.json)
— shaped like what `ListMilestones`/`ListIssues` would actually return.
`ListMilestones` is one new line on `SCOPES.md`'s GitHub row, read-only, no
other new scope asked for anywhere in this recipe.

Confidence is age-gated on how long the milestone has been closed while the
issue sits open, not flat — 24 hours, matching
`merged-pr-issue-still-open`'s and `duplicate-issue-still-open`'s own bar (a
clear, easily-verified resolution signal deserves a short grace window)
rather than `contributor-thanked-not-credited`'s slower 72h (a README
credit is a more deliberate edit than sweeping a milestone's own issues).
See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/milestone-closed-issue-still-open/detector.py
```

Run bare like this it uses the real wall clock, so the fixture issues' ages
(and therefore which ones clear 24 hours) will drift as real time passes —
expected for a manual demo, not a bug, the same documented property every
age-gated MOCK-only fixture in this repo already carries. The test suite
always pins `now` explicitly so the result stays deterministic in CI.

It finds one real gap in its own fixture (issue #801, confidence 0.85 — its
milestone closed well over 24 hours before the pinned clock) and correctly
excludes issue #803 (already closed itself, so there's no gap left to
surface even though its milestone is also closed), issue #804 (assigned to
a milestone that is still open — the ordinary, unremarkable case), and
issue #805 (carries no milestone at all), while issue #802 (its milestone
closed only hours before the pinned clock) is weighed and shown in the tail
as a coincidence, not hidden and not electing itself.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/milestone-closed-issue-still-open/recipe.json
```
