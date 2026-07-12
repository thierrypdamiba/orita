# example-release-vs-changelog

The reference recipe. Read this directory before writing your own —
[`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) is the schema in prose,
this is the schema as a working example.

**The seam it watches:** a GitHub release goes out, but this project's own
`CHANGELOG.md` never got the matching entry. Two fixtures, no live account —
[`../../fixtures/example_recipe/releases.json`](../../fixtures/example_recipe/releases.json)
and
[`../../fixtures/example_recipe/changelog.json`](../../fixtures/example_recipe/changelog.json)
— shaped like what `ListRepoCommits` / `GetLatestRelease` would actually
return, the same "fixture today, live scope tomorrow" shape as
[`gmail_calendar.py`](../../seam_engine/src/seam_engine/gmail_calendar.py).

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/example-release-vs-changelog/detector.py
```

It finds one real gap in its own fixture (`v0.3.0`, confidence 0.80 — above
`CONFIDENCE_BAR`) and one honestly-excluded match (`v0.2.0`, already in the
changelog). That is what "an example recipe that passes" means here: not
just a manifest that clears the validator, a detector that actually finds
the thing it claims to find.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/example-release-vs-changelog/recipe.json
```
