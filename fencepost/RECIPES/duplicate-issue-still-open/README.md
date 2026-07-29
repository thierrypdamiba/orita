# duplicate-issue-still-open

The seventh real recipe. [`issue-closed-pr-still-open`](../issue-closed-pr-still-open/)
(task 373) watches a still-open PR that names a closing keyword for an issue
that closed some other way. This recipe watches a related but distinct seam:
an issue, not a PR, marking itself a duplicate.

**The seam it watches:** an issue's own body reads `duplicate of #N` (or
`dup of #N`), and #N has since closed — but GitHub gives a duplicate marker
no auto-close mechanism at all. Unlike a PR's `closes #N`, which at least
*would* close the issue on merge (even if that trigger sometimes misfires,
per `merged-pr-issue-still-open` and `issue-closed-pr-still-open`), a
duplicate marker is pure prose. Nothing was ever wired to fire on it. So the
duplicate can sit open, referencing an already-resolved original,
indefinitely, with no automation anywhere that could have caught it — only
a human re-reading both issues side by side would notice. That is exactly
the seam a read-only cross-record scan is for. One fixture, no live
account — [`../../fixtures/duplicate_issue_still_open/issues.json`](../../fixtures/duplicate_issue_still_open/issues.json)
— shaped like what `ListIssues`/`GetIssue` would actually return, both
already on `SCOPES.md`'s cleared oath table. No new scope is asked for
anywhere in this recipe.

Confidence is age-gated on how long the named original has been closed
while the duplicate sits open, not flat — 24 hours, matching
`merged-pr-issue-still-open`'s own bar (a clear, easily-verified resolution
signal deserves a short grace window) rather than
`contributor-thanked-not-credited`'s slower 72h (a README credit is a more
deliberate edit than closing an obvious duplicate). See `recipe.json`'s
`confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/duplicate-issue-still-open/detector.py
```

Run bare like this it uses the real wall clock, so the fixture issues' ages
(and therefore which ones clear 24 hours) will drift as real time passes —
expected for a manual demo, not a bug, the same documented property every
age-gated MOCK-only fixture in this repo already carries. The test suite
always pins `now` explicitly so the result stays deterministic in CI.

It finds one real gap in its own fixture (issue #701, confidence 0.85 — its
named original #700 closed well over 24 hours before the pinned clock) and
correctly excludes issue #704 (named original #705 is still open — the
ordinary, unremarkable case), issue #706 (no duplicate marker at all), issue
#707 (already closed itself, so there's no gap left to surface even though
it also names a closed original), and issue #709 (names #999, an original
this fixture doesn't carry), while issue #702 (named original closed only
hours before the pinned clock) is weighed and shown in the tail as a
coincidence, not hidden and not electing itself.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/duplicate-issue-still-open/recipe.json
```
