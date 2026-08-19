# unblocked-pr-still-open

The eighty-fifth real recipe (ROADMAP.md #869). The PR-side twin of
[`../unblocked-issue-still-open/`](../unblocked-issue-still-open/) (task
593), the same pairing shape
[`../duplicate-issue-still-open/`](../duplicate-issue-still-open/)/
[`../duplicate-pr-still-open/`](../duplicate-pr-still-open/) already
established for a different marker word. This recipe reads the identical
"blocked by #N" / "blocked on #N" marker, this time on a pull request's
own body instead of an issue's.

**The seam it watches:** a PR's own body says it is blocked by another
PR, that other PR has since merged or closed, and the blocked PR was
never revisited — no comment, no state change, nothing. GitHub gives a
"blocked by" note no wiring of any kind: no auto-close (rightly — a
dependency clearing is not the same as the dependent work being done), no
auto-comment, no flag anywhere in the API that would tell anyone the wait
is over. Only holding the blocked PR's own claim and the blocker's own
live state at once, and comparing them, surfaces it at all — a human
would have to remember which PR was waiting on which, and re-check by
hand.

This recipe is careful not to overreach into `duplicate-pr-still-open`'s
own seam: it never claims the blocked PR *should* close now that its
blocker has. It claims only the narrower, more honest fact — a
dependency the PR itself named has resolved, and nothing shows anyone
noticed. The no-grading law holds exactly as it does for every sibling:
the headline names two PR numbers and a timestamp, never a person.

The "blocked by/on #N" grammar itself lives in
[`../../seam_engine/src/seam_engine/blocker_markers.py`](../../seam_engine/src/seam_engine/blocker_markers.py)
(ROADMAP.md #869) — this is the SECOND recipe to need it, the exact
threshold `unblocked-issue-still-open`'s own docstring named as the
moment to extract it to a shared module, mirroring `duplicate_markers.py`'s
own two-user extraction. `unblocked-issue-still-open/detector.py` was
refactored in the same commit to import the same function.

One fixture, no live account —
[`../../fixtures/unblocked_pr_still_open/pulls.json`](../../fixtures/unblocked_pr_still_open/pulls.json)
— shaped like what `ListPullRequests`/`GetPullRequest` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table, the
identical pairing `duplicate-pr-still-open` already established for this
exact shape of self-referencing-record/target-record recipe — no new
scope is asked for anywhere in this recipe.

Confidence is age-gated on how long the named blocker has been resolved
while the blocked PR still sits open, reusing
`unblocked-issue-still-open`'s and `duplicate-pr-still-open`'s own
24-hour bar rather than inventing a new number for a structurally similar
family: under 24 hours may just be a human who hasn't circled back yet,
weighed in the tail at 0.5; at or past 24 hours it is unambiguous, a flat
0.85. A PR naming no blocker marker, naming a blocker that is still open,
or naming a blocker this fixture doesn't carry at all is excluded, named
not hidden. See `recipe.json`'s `confidence_notes` for the full
reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/unblocked-pr-still-open/detector.py
```

Run bare like this it uses the real wall clock, so the fixture PRs' ages
(and therefore which ones clear 24 hours) will drift as real time passes
— expected for a manual demo, not a bug, the same documented property
every age-gated MOCK-only fixture in this repo already carries. The test
suite always pins `now` explicitly so the result stays deterministic in
CI.

It finds one real gap in its own fixture (PR #901, confidence 0.85 — its
named blocker #900 merged well over 24 hours before the pinned clock) and
correctly excludes PR #904 (named blocker #905 is still open — the
ordinary, unremarkable case), PR #906 (no blocker marker at all), PR #907
(already closed itself, so there's no gap left to surface even though it
also names a resolved blocker), PR #909 (names #999, a blocker this
fixture doesn't carry), and PR #910 (names #911, a blocker that reads
merged but carries no close timestamp — a malformed record, not an
unresolved seam), while PR #902 (named blocker closed only hours before
the pinned clock) is weighed and shown in the tail as a coincidence, not
hidden and not electing itself.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/unblocked-pr-still-open/recipe.json
```
