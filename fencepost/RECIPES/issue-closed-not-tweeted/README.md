# issue-closed-not-tweeted

The twenty-first real recipe. Completes the closed-but-not-tweeted family
alongside `release-not-tweeted` (task 110), `milestone-closed-not-tweeted`
(task 390), and `merged-pr-not-tweeted` (task 398): all three siblings
watch shipped work never announced on X, each for a different GitHub
artifact type -- a release, a milestone, a merged pull request. An issue is
the one artifact type in that family without this check, even though
closing one is its own real, user-facing event (a bug fixed, a feature
delivered) with no second GitHub record it has to acquire before it
becomes announceable, the identical shape `merged-pr-not-tweeted`'s own
docstring already made for a merged PR.

**The seam it watches:** a GitHub issue closes, but no tweet from the
connected X account ever names its number. Two fixtures, no live account —
[`../../fixtures/issue_closed_not_tweeted/issues.json`](../../fixtures/issue_closed_not_tweeted/issues.json)
and
[`../../fixtures/issue_closed_not_tweeted/tweets.json`](../../fixtures/issue_closed_not_tweeted/tweets.json)
— shaped like what `ListIssues` and `GetUserTweets` would actually return.
Both declared scopes already sit on `SCOPES.md`'s cleared oath table under
their own toolkit rows. No new scope is asked for anywhere in this recipe.

Matching is by exact, digit-boundary issue-number substring — `#12` must
not be considered mentioned by a tweet naming the unrelated, longer `#123`
— the same short-inside-long collision `release-not-tweeted`'s own tag
matcher already guards against, in numeral form, mirroring
`merged-pr-not-tweeted`'s own copy of the same guard. An issue that is
still open is never a candidate at all — there is nothing shipped yet to
announce.

Confidence is age-gated, matching every sibling in this family exactly (no
stated reason to weigh an issue closing differently than a release, a
milestone, or a merged PR): a close with no matching tweet within 24 hours
scores 0.55 (below the bar — a human may simply not have tweeted yet); at
or past 24 hours it scores 0.85 (an unambiguous, non-fuzzy number match).
See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src:../RECIPES/issue-closed-not-tweeted uv run python ../RECIPES/issue-closed-not-tweeted/detector.py
```

Run bare like this it uses the real wall clock, so the fixture issues' ages
will drift as real time passes — expected for a manual demo, not a bug; the
test suite always pins `now` explicitly so the result stays deterministic
in CI.

It finds one real gap in its own fixture (#12, confidence 0.85 — closed
stale, never tweeted) and correctly excludes #13 (tweeted by exact number)
and #15 (still open, never a candidate), while #14 (fresh, <24h) is weighed
and shown in the tail as a coincidence, not hidden and not electing itself
primary. A decoy tweet naming the unrelated, longer #123 proves the match
is digit-boundary-exact, not substring-fuzzy — it does not falsely exclude
the real gap at #12.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/issue-closed-not-tweeted/recipe.json
```
