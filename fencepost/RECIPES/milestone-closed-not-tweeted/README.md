# milestone-closed-not-tweeted

The nineteenth real recipe (ROADMAP.md #390) — the milestone-side twin of
[`../release-not-tweeted/`](../release-not-tweeted/) (task 110, the third
real recipe and the first cross-toolkit one).

**The seam it watches:** a GitHub milestone closes, but no tweet from the
connected X account ever names it. `release-not-tweeted` matches by exact
tag substring; a milestone has no tag, so this recipe reuses the
`milestone #N` claim phrase
[`milestone-closed-never-released`](../milestone-closed-never-released/)
(task 383) and
[`release-claims-open-milestone`](../release-claims-open-milestone/)
(task 385) already established for milestones — checked against a tweet's
own text instead of a release's own body, the same claim grammar, a third
data source.

That claim phrase used to live as two textually-identical, independently
typed copies (comment-linked but never import-linked — the exact
"reused verbatim... not a second copy of it drifting apart" gap task 389
found and fixed for `#N` extraction). Rather than writing a third copy for
this recipe, both existing detectors were refactored to import
`claimed_milestone_numbers` from a new shared module,
[`seam_engine/milestone_claims.py`](../../seam_engine/src/seam_engine/milestone_claims.py),
and this recipe imports the same function from the start. See
`seam_engine/tests/test_milestone_claims.py`'s `TestAllThreeDetectorsShareTheLaw`
for the regression test that would go red if any of the three ever went
back to a local copy.

Two fixtures, no live account —
[`../../fixtures/milestone_closed_not_tweeted/milestones.json`](../../fixtures/milestone_closed_not_tweeted/milestones.json)
and
[`../../fixtures/milestone_closed_not_tweeted/tweets.json`](../../fixtures/milestone_closed_not_tweeted/tweets.json)
— shaped like what `ListMilestones` and `GetUserTweets` would actually
return. Both declared scopes already sit on `SCOPES.md`'s cleared oath
table. No new scope is asked for anywhere in this recipe.

Confidence is age-gated, mirroring `release-not-tweeted`'s own 24-hour
announce window exactly: a milestone closed under 24 hours ago with no
announcing tweet yet scores 0.55 (below the bar — a human may simply not
have tweeted yet); at or past 24 hours it scores 0.85. See `recipe.json`'s
`confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src:../RECIPES/milestone-closed-not-tweeted uv run python ../RECIPES/milestone-closed-not-tweeted/detector.py
```

Run bare like this it uses the real wall clock, so the fixture milestones'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite pins `now` explicitly so the result stays
deterministic in CI.

It finds one real gap in its own fixture (#4001, confidence 0.85 —
closed stale, never tweeted) and correctly excludes #4003 (tweeted the
day it closed) and #4004 (still open), while #4002 (closed <24h ago) is
weighed and shown in the tail as a coincidence, not hidden and not
electing itself primary.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/milestone-closed-not-tweeted/recipe.json
```
