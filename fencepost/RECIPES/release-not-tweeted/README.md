# release-not-tweeted

The third real recipe (ROADMAP.md #110), and the first that watches a seam
across TWO toolkits at once. [`../example-release-vs-changelog/`](../example-release-vs-changelog/)
(task 22) and [`../merged-pr-issue-still-open/`](../merged-pr-issue-still-open/)
(task 108) both compare two records that live entirely inside GitHub. This
one compares a GitHub release against the connected X account's tweets —
the exact worked example STRATEGY.md names by hand: *"a release shipped but
never tweeted."*

**The seam it watches:** a GitHub release publishes, but no tweet from the
connected X account ever names its tag. Two fixtures, no live account —
[`../../fixtures/release_not_tweeted/releases.json`](../../fixtures/release_not_tweeted/releases.json)
and
[`../../fixtures/release_not_tweeted/tweets.json`](../../fixtures/release_not_tweeted/tweets.json)
— shaped like what a releases-list call and `GetUserTweets` would actually
return. All three declared scopes already sit on `SCOPES.md`'s cleared oath
table under their own toolkit rows. No new scope is asked for anywhere in
this recipe.

Confidence is age-gated, mirroring `merged-pr-issue-still-open`'s reasoning:
a release with no matching tweet within 24 hours of publish scores 0.55
(below the bar — a human may simply not have tweeted yet); at or past 24
hours it scores 0.85 (an unambiguous, non-fuzzy tag-substring match). See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src:../RECIPES/release-not-tweeted uv run python ../RECIPES/release-not-tweeted/detector.py
```

Run bare like this it uses the real wall clock, so the fixture releases'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite (`seam_engine/tests/test_recipes.py`) always pins `now`
explicitly so the result stays deterministic in CI.

It finds one real gap in its own fixture (v0.3.0, confidence 0.85 —
published stale, never tweeted) and correctly excludes v0.2.1 (tweeted the
same day), while v0.4.0 (fresh, <24h) is weighed and shown in the tail as a
coincidence, not hidden and not electing itself primary.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/release-not-tweeted/recipe.json
```
