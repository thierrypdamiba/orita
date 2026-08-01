# tweet-claims-open-milestone

The twenty-ninth real recipe (ROADMAP.md #452). The tweet-side twin of
[`../release-claims-open-milestone/`](../release-claims-open-milestone/)
(the sixteenth real recipe): that one watches a GitHub release's own body
text claiming a milestone shipped that never actually closed; this one
watches the identical shape one platform over — a tweet from the connected
X account. It closes the milestone-claim half of the release-vs-tweet
split [`tweet-claims-unmerged-pr`](../tweet-claims-unmerged-pr/) (the
twenty-seventh real recipe) and
[`tweet-claims-unfixed-issue`](../tweet-claims-unfixed-issue/) (the
twenty-eighth) already opened for PR and issue claims.

**The seam it watches:** a tweet claims a milestone shipped ("milestone
#N"), but the named milestone is not actually closed. A tweet is as
permanent and public as a release note once posted, and nothing on X's
side (or GitHub's) ever checks it against the milestone tracker's own
truth. Two fixtures, no live account —
[`../../fixtures/tweet_claims_open_milestone/tweets.json`](../../fixtures/tweet_claims_open_milestone/tweets.json)
and
[`../../fixtures/tweet_claims_open_milestone/milestones.json`](../../fixtures/tweet_claims_open_milestone/milestones.json)
— shaped like what `GetUserTweets` and `ListMilestones` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table. No
new scope is asked for anywhere in this recipe.

A claimed milestone that doesn't exist at all is excluded here, named not
hidden — that broken reference is a dangling-reference seam, not this
one's. A claimed milestone that IS closed is excluded too — the claim was
simply true.

Confidence is age-gated by the tweet's own `created_at`, mirroring
`release-claims-open-milestone`'s and `tweet-claims-unfixed-issue`'s
reasoning exactly: a claim checked within 24 hours of posting scores 0.5
(below the bar — could be a real race, tweet posted moments before the
milestone closes out); at or past 24 hours it scores 0.85 (a posted tweet
is static, no keyword fuzziness left to misfire on). See `recipe.json`'s
`confidence_notes` for the full reasoning.

Reuses `seam_engine.milestone_claims.claimed_milestone_numbers` verbatim,
the same shared grammar `release-claims-open-milestone` and
`milestone-closed-not-tweeted` already import from there (task 389) — a
third independently retyped copy of the identical pattern was exactly the
drift that centralization exists to prevent.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/tweet-claims-open-milestone/detector.py
```

Run bare like this it uses the real wall clock, so the fixture tweets'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

It finds one real gap in its own fixture (tweet `T-1201`'s claim about
milestone #5001, confidence 0.85 — still open, 50 hours stale) and
correctly excludes milestone #5002 (claim holds, closed), `T-1204`'s claim
about milestone #5999 (no such milestone — a dangling reference), and
`T-1205` (no claim phrase at all), while `T-1202`'s claim about milestone
#5003 (4 hours old at the pinned test clock) is weighed and shown in the
tail as a coincidence, not hidden and not electing itself primary. A
duplicate claim inside `T-1201`'s own text ("Milestone #5001 shipped today
and milestone #5001 confirmed again") is de-duplicated to a single
candidate, not two.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/tweet-claims-open-milestone/recipe.json
```
