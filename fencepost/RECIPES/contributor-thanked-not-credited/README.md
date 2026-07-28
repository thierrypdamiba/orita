# contributor-thanked-not-credited

The fifth real recipe (ROADMAP.md #371), and the second that watches a seam
across TWO toolkits at once. [`../release-not-tweeted/`](../release-not-tweeted/)
(task 110) built the first half of a sentence STRATEGY.md's own Growth notes
state together: *"a release shipped but never tweeted; a contributor thanked
on X but missing from the README."* This recipe builds the second half.

**The seam it watches:** the connected X account thanks a contributor by
`@handle`, but that handle never lands in the repo's own README. Two
fixtures, no live account —
[`../../fixtures/contributor_thanked_not_credited/tweets.json`](../../fixtures/contributor_thanked_not_credited/tweets.json)
and
[`../../fixtures/contributor_thanked_not_credited/readme.json`](../../fixtures/contributor_thanked_not_credited/readme.json)
— shaped like what `GetUserTweets` and a read-only `GetFileContents` call on
this repo's own README would actually return. `GetUserTweets` already sits
on `SCOPES.md`'s cleared X row; `GetFileContents` is new, and clears the
same oath everything else does (`Get*` prefix, no forbidden word inside it).

Not every `@mention` is a thank-you: the detector only considers a tweet a
candidate if "thanks"/"thank you" appears near an `@handle` in the same
tweet — the same "no fuzzy matching to misfire on" discipline
`release-not-tweeted` already holds for its exact-tag match.

Confidence is age-gated, mirroring `release-not-tweeted`'s reasoning, with a
genuinely different number: a thanked handle not yet credited within 72
hours scores 0.5 (below the bar — a human may simply not have gotten to the
README edit yet); at or past 72 hours it scores 0.85. 72h, not
`release-not-tweeted`'s 24h, because crediting a README is a slower,
more deliberate edit than posting an announcement tweet. See `recipe.json`'s
`confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src:../RECIPES/contributor-thanked-not-credited uv run python ../RECIPES/contributor-thanked-not-credited/detector.py
```

Run bare like this it uses the real wall clock, so the fixture tweets' ages
will drift as real time passes — expected for a manual demo, not a bug; the
test suite (`seam_engine/tests/test_contributor_thanked_not_credited_detector.py`)
always pins `now` explicitly so the result stays deterministic in CI.

It finds one real gap in its own fixture (`@newcomer99`, thanked 2026-07-18,
stale by the pinned test clock — confidence 0.85) and correctly excludes
`@mortal-fixer` (already credited in the README fixture), while
`@freshcontributor` (thanked <72h before the pinned clock) is weighed and
shown in the tail as a coincidence, not hidden and not electing itself
primary. The report-only tweet with no thanks-shaped language never becomes
a candidate at all.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/contributor-thanked-not-credited/recipe.json
```
