# unblocked-issue-still-open

The sixty-first real recipe (ROADMAP.md #593).
[`../duplicate-issue-still-open/`](../duplicate-issue-still-open/) (task
376) proved a self-declared, pure-prose marker inside an issue's own body
is a real seam GitHub gives no automation to at all. This recipe reads a
genuinely different marker on the same surface: not "duplicate of #N"
(a claim of equivalence — closing the original really should have closed
this one too) but "blocked by #N" / "blocked on #N" (a claim of
dependency — closing the blocker doesn't mean this issue is done, it
means this issue's own work just became possible again).

**The seam it watches:** an issue's own body says it is blocked by
another issue, that other issue has since closed, and the blocked issue
was never revisited — no comment, no state change, nothing. GitHub gives
a "blocked by" note no wiring of any kind: no auto-close (rightly — a
dependency clearing is not the same as the dependent work being done),
no auto-comment, no flag anywhere in the API that would tell anyone the
wait is over. Only holding the blocked issue's own claim and the
blocker's own live state at once, and comparing them, surfaces it at
all — a human would have to remember which issue was waiting on which,
and re-check by hand.

This recipe is careful not to overreach into `duplicate-issue-still-open`'s
own seam: it never claims the blocked issue *should* close now that its
blocker has. It claims only the narrower, more honest fact — a
dependency the issue itself named has resolved, and nothing shows anyone
noticed. The no-grading law holds exactly as it does for every sibling:
the headline names two issue numbers and a timestamp, never a person.

One fixture, no live account —
[`../../fixtures/unblocked_issue_still_open/issues.json`](../../fixtures/unblocked_issue_still_open/issues.json)
— shaped like what `ListIssues`/`GetIssue` would actually return. Both
scopes already sit on `SCOPES.md`'s cleared oath table, the identical
pairing `duplicate-issue-still-open` already established for this exact
shape of self-referencing-record/target-record recipe — no new scope is
asked for anywhere in this recipe.

Confidence is age-gated on how long the named blocker has been closed
while the blocked issue still sits open, reusing
`duplicate-issue-still-open`'s and `overdue-milestone-still-open`'s own
24-hour bar rather than inventing a new number for a structurally similar
family: under 24 hours may just be a human who hasn't circled back yet,
weighed in the tail at 0.5; at or past 24 hours it is unambiguous, a flat
0.85. An issue naming no blocker marker, naming a blocker that is still
open, or naming a blocker this fixture doesn't carry at all is excluded,
named not hidden. See `recipe.json`'s `confidence_notes` for the full
reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/unblocked-issue-still-open/detector.py
```

Run bare like this it uses the real wall clock, so the fixture issues'
ages (and therefore which ones clear 24 hours) will drift as real time
passes — expected for a manual demo, not a bug, the same documented
property every age-gated MOCK-only fixture in this repo already carries.
The test suite always pins `now` explicitly so the result stays
deterministic in CI.

It finds one real gap in its own fixture (issue #901, confidence 0.85 —
its named blocker #900 closed well over 24 hours before the pinned clock)
and correctly excludes issue #904 (named blocker #905 is still open — the
ordinary, unremarkable case), issue #906 (no blocker marker at all),
issue #907 (already closed itself, so there's no gap left to surface even
though it also names a closed blocker), issue #909 (names #999, a blocker
this fixture doesn't carry), and issue #910 (names #911, a blocker that
reads closed but carries no close timestamp — a malformed record, not an
unresolved seam), while issue #902 (named blocker closed only hours before
the pinned clock) is weighed and shown in the tail as a coincidence, not
hidden and not electing itself.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/unblocked-issue-still-open/recipe.json
```
