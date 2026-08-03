# merged-pr-pr-still-open

The twenty-sixth real recipe (ROADMAP.md #419) — the pull-request-target
twin of [`../merged-pr-issue-still-open/`](../merged-pr-issue-still-open/),
which explicitly, deliberately, only ever checked a merged PR's
closing-keyword number against the repo's ISSUE set. GitHub's real
auto-close trigger does not care which record type the named number
belongs to: a merged PR's own body naming `closes #N` / `fixes #N` /
`resolves #N` against a number that is itself a pull request fires the
identical mechanism, and that promise can silently never hold exactly the
same way it can for an issue. This recipe closes the last open cell of the
2x2 matrix `commit-closes-keyword-issue-still-open` /
`commit-closes-keyword-pr-still-open` / `merged-pr-issue-still-open` had
already built three-quarters of — see the detector's own module docstring
for the full matrix.

**The seam it watches:** a pull request merges naming a GitHub closing
keyword (`closes #N` / `fixes #N` / `resolves #N`), but the PR it named is
still open. Two fixtures, no live account —
[`../../fixtures/merged_pr_pr_still_open/pulls.json`](../../fixtures/merged_pr_pr_still_open/pulls.json)
and
[`../../fixtures/merged_pr_pr_still_open/prs.json`](../../fixtures/merged_pr_pr_still_open/prs.json)
— shaped like what `ListPullRequests` would actually return, already on
`SCOPES.md`'s cleared oath table. One scope, nothing new asked for.

Confidence is age-gated, not flat: a promised close under 24 hours old
scores 0.55 (below the bar — auto-close can lag, or nobody's looked yet);
at or past 24 hours it scores 0.85 (an unambiguous, non-fuzzy signal) — the
identical shape `merged-pr-issue-still-open` uses on the issue side, no
deviation. See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/merged-pr-pr-still-open/detector.py
```

Run bare like this it uses the real wall clock, so the fixture PRs' ages
(and therefore which ones clear 24 hours) will drift as real time passes —
that is expected for a manual demo, not a bug; the test suite
(`seam_engine/tests/test_merged_pr_pr_still_open_detector.py`) always pins
`now` explicitly so the result stays deterministic in CI.

It finds one real gap in its own fixture (PR #201, referencing PR #150,
confidence 0.85 — merged stale, target still open) and correctly excludes:
a target already resolved (merged or closed without merging), a
referencing PR with no closing keyword at all, a PR naming its own number
(a self-reference — GitHub's own UI never treats that as a real closing
trigger), and a referencing PR naming a target number that doesn't exist
in this fixture's PR set at all (a broken link, not this recipe's own
seam) — every excluded case named, not hidden.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/merged-pr-pr-still-open/recipe.json
```
