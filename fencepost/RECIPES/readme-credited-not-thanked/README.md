# readme-credited-not-thanked

The fifteenth real recipe (ROADMAP.md #384), and the deliberate inverse of
[`../contributor-thanked-not-credited/`](../contributor-thanked-not-credited/)
(task 371). That recipe watches a tweet thanking a handle the README does
not yet credit; this one watches the exact opposite direction of the same
two-toolkit seam.

**The seam it watches:** a contributor is already credited in the repo's
own README "## Thanks" section, but the connected X account has never once
thanked that handle, anywhere in its read tweet history. Two fixtures, no
live account —
[`../../fixtures/readme_credited_not_thanked/readme.json`](../../fixtures/readme_credited_not_thanked/readme.json)
and
[`../../fixtures/readme_credited_not_thanked/tweets.json`](../../fixtures/readme_credited_not_thanked/tweets.json)
— shaped like what a read-only `GetFileContents` call on this repo's own
README and `GetUserTweets` would actually return. Both scopes are already
cleared on `SCOPES.md`'s oath table — no new scope needed.

Only handles credited inside the README's own "## Thanks" section are ever
considered — the fixture README also carries a "## Houses" section naming
gods by handle, on purpose, to prove the section-scoping actually holds and
doesn't just get lucky on a small fixture.

Confidence is gated by two factors, neither a copy-pasted number from the
twin recipe: (1) **coverage** — a credited handle that never appears in any
read tweet at all scores 0.85 once the read tweet history spans at least 96
hours (wider than the twin's 72h credit-lag window, since absence-of-evidence
needs a longer bar to trust than a real tweet's own lag); below that
coverage bar it scores 0.5, shown not hidden. (2) a credited handle that
DOES appear somewhere in the tweet text, just never in thanks-shaped
language, is treated as a weaker signal (0.5) — a maintainer who already
mentioned them is plausibly aware and just hasn't phrased a thanks yet. See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src:../RECIPES/readme-credited-not-thanked uv run python ../RECIPES/readme-credited-not-thanked/detector.py
```

Run bare like this it uses the real wall clock, so the fixture tweets' ages
will drift as real time passes — expected for a manual demo, not a bug; the
test suite (`seam_engine/tests/test_readme_credited_not_thanked_detector.py`)
always pins `now` explicitly so the result stays deterministic in CI.

It finds one real gap in its own fixture (`@quiet-helper`, credited, never
mentioned anywhere in the read tweet history, coverage window past the bar
— confidence 0.85) and correctly excludes `@mortal-fixer` (already thanked
in the tweets fixture), while `@early-scout` (credited, mentioned in a
non-thanks tweet) is weighed and shown in the tail as a coincidence, not
hidden and not electing itself primary. `@off-by-one` and `@nisaba`, named
under the fixture's own "## Houses" section, never become candidates at all
— they are not credited in the "## Thanks" section the detector actually
reads.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/readme-credited-not-thanked/recipe.json
```
