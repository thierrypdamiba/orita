# merged-pr-not-tweeted

The twentieth real recipe (ROADMAP.md #398). Watches a seam none of the
nineteen recipes before it touch directly: `release-not-tweeted` (task 110)
and `milestone-closed-not-tweeted` (task 390) both catch shipped work never
announced, but both gate the check behind a second GitHub record — a
release, a milestone — that a merged pull request never has to acquire at
all. Most merged PRs in this town's own history carry neither. This recipe
watches the seam underneath both siblings: the PR itself, the moment it
merges.

**The seam it watches:** a pull request merges into `main`, but no tweet
from the connected X account ever names its number. Two fixtures, no live
account —
[`../../fixtures/merged_pr_not_tweeted/pulls.json`](../../fixtures/merged_pr_not_tweeted/pulls.json)
and
[`../../fixtures/merged_pr_not_tweeted/tweets.json`](../../fixtures/merged_pr_not_tweeted/tweets.json)
— shaped like what `ListPullRequests` and `GetUserTweets` would actually
return. Both declared scopes already sit on `SCOPES.md`'s cleared oath
table under their own toolkit rows. No new scope is asked for anywhere in
this recipe.

Matching is by exact, digit-boundary PR-number substring — `#1301` must not
be considered mentioned by a tweet naming the unrelated, longer `#13010` —
the same short-inside-long collision `release-not-tweeted`'s own tag
matcher already guards against, in numeral form. A PR that never merged
(still open, or closed without merging) is never a candidate at all — there
is nothing shipped yet to announce.

Confidence is age-gated, mirroring `release-not-tweeted`'s own reasoning: a
merge with no matching tweet within 24 hours scores 0.55 (below the bar — a
human may simply not have tweeted yet); at or past 24 hours it scores 0.85
(an unambiguous, non-fuzzy number match). See `recipe.json`'s
`confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src:../RECIPES/merged-pr-not-tweeted uv run python ../RECIPES/merged-pr-not-tweeted/detector.py
```

Run bare like this it uses the real wall clock, so the fixture PRs' ages
will drift as real time passes — expected for a manual demo, not a bug; the
test suite always pins `now` explicitly so the result stays deterministic
in CI.

It finds one real gap in its own fixture (#1301, confidence 0.85 — merged
stale, never tweeted) and correctly excludes #1303 (tweeted by exact
number) and #1304/#1305 (never merged at all), while #1302 (fresh, <24h)
is weighed and shown in the tail as a coincidence, not hidden and not
electing itself primary.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/merged-pr-not-tweeted/recipe.json
```
