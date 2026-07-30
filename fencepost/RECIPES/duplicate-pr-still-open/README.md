# duplicate-pr-still-open

The twenty-second real recipe. [`duplicate-issue-still-open`](../duplicate-issue-still-open/)
(the seventh real recipe) watches an issue that marks itself a duplicate of
another issue whose original has since closed. This recipe watches the same
shape of seam on the other side of GitHub's shared number space: a pull
request, not an issue, marking itself a duplicate.

**The seam it watches:** a PR's own body reads `duplicate of #N` (or
`dup of #N`), and #N has since merged or closed — but GitHub gives a
duplicate marker no auto-close mechanism at all, on either side of the
issue/PR divide. Unlike a PR's `closes #N` against an *issue*, which at
least *would* close that issue on merge (even if that trigger sometimes
misfires, per `merged-pr-issue-still-open` and `issue-closed-pr-still-
open`), a duplicate marker naming another *PR* is pure prose. Nothing was
ever wired to fire on it. So the duplicate PR can sit open, referencing an
already-resolved original, indefinitely, with no automation anywhere that
could have caught it — only a human re-reading both PRs side by side would
notice. That is exactly the seam a read-only cross-record scan is for. One
fixture, no live account —
[`../../fixtures/duplicate_pr_still_open/pulls.json`](../../fixtures/duplicate_pr_still_open/pulls.json)
— shaped like what `ListPullRequests`/`GetPullRequest` would actually
return, both already on `SCOPES.md`'s cleared oath table. No new scope is
asked for anywhere in this recipe.

The duplicate-marker extraction itself (`named_duplicate_of`) now lives in
`seam_engine.duplicate_markers` (task 400) — this recipe and its issue-side
twin both import the same function rather than each hand-typing an
identical regex, closing the exact "second file, second copy" gap
`tools/duplicate_regex_check.py` (task 397) exists to catch before it can
reach a sixth instance.

Confidence is age-gated on how long the named original has been resolved
while the duplicate sits open, not flat — 24 hours, matching
`duplicate-issue-still-open`'s own bar exactly (a clear, easily-verified
resolution signal deserves a short grace window, whichever side of the
issue/PR divide it sits on). See `recipe.json`'s `confidence_notes` for the
full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/duplicate-pr-still-open/detector.py
```

Run bare like this it uses the real wall clock, so the fixture PRs' ages
(and therefore which ones clear 24 hours) will drift as real time passes —
expected for a manual demo, not a bug, the same documented property every
age-gated MOCK-only fixture in this repo already carries. The test suite
always pins `now` explicitly so the result stays deterministic in CI.

It finds one real gap in its own fixture (PR #801, confidence 0.85 — its
named original #800 merged well over 24 hours before the pinned clock) and
correctly excludes PR #804 (named original #805 is still open — the
ordinary, unremarkable case), PR #806 (no duplicate marker at all), PR #807
(already closed itself, so there's no gap left to surface even though it
also names a resolved original), and PR #809 (names #999, an original this
fixture doesn't carry), while PR #802 (named original closed only hours
before the pinned clock) is weighed and shown in the tail as a coincidence,
not hidden and not electing itself.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/duplicate-pr-still-open/recipe.json
```
