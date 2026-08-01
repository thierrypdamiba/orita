# tweet-claims-unfixed-issue

The twenty-eighth real recipe (ROADMAP.md #451). The tweet-side twin of
[`../release-claims-unfixed-issue/`](../release-claims-unfixed-issue/) (the
thirteenth real recipe): that one watches a GitHub release's own body text
invoking a real closing keyword against an issue that never actually
closed; this one watches the identical shape one platform over — a tweet
from the connected X account. It closes the matching issue-claim half of
the release-vs-tweet split [`tweet-claims-unmerged-pr`](../tweet-claims-unmerged-pr/)
(the twenty-seventh real recipe) already opened for PR claims.

**The seam it watches:** a tweet invokes a real GitHub closing keyword
("fixes #N" / "closes #N" / "resolves #N", both tenses), but issue #N is
not actually closed. A tweet is as permanent and public as a release note
once posted, and nothing on X's side (or GitHub's) ever checks it against
the issue tracker's own truth. Two fixtures, no live account —
[`../../fixtures/tweet_claims_unfixed_issue/tweets.json`](../../fixtures/tweet_claims_unfixed_issue/tweets.json)
and
[`../../fixtures/tweet_claims_unfixed_issue/issues.json`](../../fixtures/tweet_claims_unfixed_issue/issues.json)
— shaped like what `GetUserTweets` and `ListIssues` would actually return.
Both scopes already sit on `SCOPES.md`'s cleared oath table. No new scope
is asked for anywhere in this recipe.

A claimed issue that doesn't exist at all is excluded here, named not
hidden — that broken reference belongs to `dangling-issue-reference`'s/
`mention-dangling-reference`'s own seam, not this one's. A claimed issue
that IS closed is excluded too — the claim was simply true.

Confidence is age-gated by the tweet's own `created_at`, mirroring
`release-claims-unfixed-issue`'s and `tweet-claims-unmerged-pr`'s
reasoning exactly: a claim checked within 24 hours of posting scores 0.5
(below the bar — could be a real race, tweet posted moments before the fix
lands); at or past 24 hours it scores 0.85 (a posted tweet is static, no
keyword fuzziness left to misfire on). See `recipe.json`'s
`confidence_notes` for the full reasoning.

Reuses `seam_engine.closing_keywords.CLOSING_KEYWORD_RE` verbatim, the
same shared grammar `release-claims-unfixed-issue`,
`commit-closes-keyword-issue-still-open`, and `issue-closed-never-released`
already import from there (task 394) — a fourth independently retyped copy
of the identical pattern was exactly the drift that centralization exists
to prevent.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/tweet-claims-unfixed-issue/detector.py
```

Run bare like this it uses the real wall clock, so the fixture tweets'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

It finds one real gap in its own fixture (tweet `T-1101`'s claim about
issue #1101, confidence 0.85 — still open, 50 hours stale) and correctly
excludes issue #1102 (claim holds, closed), `T-1104`'s claim about #1999
(no such issue — dangling-issue-reference's/mention-dangling-reference's
seam), and `T-1105` (no claim phrase at all), while `T-1102`'s claim about
#1103 (4 hours old at the pinned test clock) is weighed and shown in the
tail as a coincidence, not hidden and not electing itself primary. A
duplicate claim inside `T-1101`'s own text ("Fixes #1101 today and closes
#1101 again") is de-duplicated to a single candidate, not two.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/tweet-claims-unfixed-issue/recipe.json
```
