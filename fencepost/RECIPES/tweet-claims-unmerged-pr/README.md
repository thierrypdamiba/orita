# tweet-claims-unmerged-pr

The twenty-seventh real recipe (ROADMAP.md #450). The tweet-side twin of
[`../release-claims-unmerged-pr/`](../release-claims-unmerged-pr/) (the
ninth real recipe): that one watches a GitHub release's own body text
making a permanent, public "it shipped" claim about a PR that never
actually merged; this one watches the identical shape one platform over —
a tweet from the connected X account.

**The seam it watches:** a tweet says a PR shipped ("ships #N" /
"includes #N" / "merges #N" / "via #N"), but PR #N is not actually merged —
still open, or closed without merging. A tweet is as permanent and public
as a release note once posted, and nothing on X's side (or GitHub's) ever
checks it against the PR tracker's own truth. Two fixtures, no live
account —
[`../../fixtures/tweet_claims_unmerged_pr/tweets.json`](../../fixtures/tweet_claims_unmerged_pr/tweets.json)
and
[`../../fixtures/tweet_claims_unmerged_pr/pulls.json`](../../fixtures/tweet_claims_unmerged_pr/pulls.json)
— shaped like what `GetUserTweets` and `ListPullRequests` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table. No new
scope is asked for anywhere in this recipe.

A claimed PR that doesn't exist at all is excluded here, named not hidden —
that broken reference belongs to `dangling-issue-reference`'s/`mention-
dangling-reference`'s own seam, not this one's. A claimed PR that IS merged
is excluded too — the claim was simply true.

Confidence is age-gated by the tweet's own `created_at`, mirroring
`release-claims-unmerged-pr`'s reasoning exactly: a claim checked within 24
hours of posting scores 0.5 (below the bar — could be a real race, tweet
posted moments before the merge lands); at or past 24 hours it scores 0.85
(a posted tweet is static, no keyword fuzziness left to misfire on). See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/tweet-claims-unmerged-pr/detector.py
```

Run bare like this it uses the real wall clock, so the fixture tweets'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

It finds one real gap in its own fixture (tweet `T-901`'s claim about PR
#901, confidence 0.85 — still open, 50 hours stale) and correctly excludes
PR #902 (claim holds, merged), `T-904`'s claim about #999 (no such PR —
dangling-issue-reference's/mention-dangling-reference's seam), and `T-905`
(no claim phrase at all), while `T-902`'s claim about #903 (4 hours old at
the pinned test clock) is weighed and shown in the tail as a coincidence,
not hidden and not electing itself primary. A duplicate claim inside
`T-901`'s own text ("Ships #901 today and via #901 again") is
de-duplicated to a single candidate, not two.

The claim regex (`ships?|includes?|merges?|via #N`) is shared with
[`../release-claims-unmerged-pr/`](../release-claims-unmerged-pr/) and
[`../merged-pr-never-released/`](../merged-pr-never-released/) via
[`seam_engine/pr_claims.py`](../../seam_engine/src/seam_engine/pr_claims.py)
— this recipe imports `claimed_pr_numbers` from there rather than carrying
a third, independently typed copy of the identical regex, the exact drift
task 393 already found and fixed once between the first two.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/tweet-claims-unmerged-pr/recipe.json
```
