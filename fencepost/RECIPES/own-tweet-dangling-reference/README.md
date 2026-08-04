# own-tweet-dangling-reference

The forty-second real recipe (ROADMAP.md #527), and the sixth leg of the
dangling-reference family — the first to read the connected X account's OWN
tweets rather than a mortal's mention of it
([`../mention-dangling-reference/`](../mention-dangling-reference/)), a
commit message
([`../dangling-issue-reference/`](../dangling-issue-reference/)), an
issue/PR body
([`../issue-body-dangling-reference/`](../issue-body-dangling-reference/)),
a milestone description
([`../milestone-body-dangling-reference/`](../milestone-body-dangling-reference/)),
or a release note
([`../release-note-dangling-reference/`](../release-note-dangling-reference/)).

**The seam it watches:** GitHub renders `#N` inside any piece of text as a
clickable link without ever checking it resolves to anything — the same
mechanical fact every leg of this family already proves for its own
surface. This recipe asks it of the town's own outbound tweets: a `#N` the
account itself published, sitting live and public and permanent, that
matches no real issue or pull request in this repo. A typo, a reference to
something later deleted, or digits meant for a different repo — the town's
own public claim already out of sync with GitHub's real number space, and
nobody proofread it before it went out.

Three fixture lists, no live account —
[`../../fixtures/own_tweet_dangling_reference/tweets.json`](../../fixtures/own_tweet_dangling_reference/tweets.json),
[`.../issues.json`](../../fixtures/own_tweet_dangling_reference/issues.json),
and [`.../pulls.json`](../../fixtures/own_tweet_dangling_reference/pulls.json)
— shaped like what `GetUserTweets`/`ListIssues`/`ListPullRequests` would
actually return. All three declared scopes already sit on `SCOPES.md`'s
cleared oath table. No new scope is asked for anywhere in this recipe.

A `#N` reference is checked against BOTH the issue list and the PR list —
GitHub shares one number sequence between them, so checking only one would
misfire on a perfectly good reference to a merged PR. A cross-repo
reference (`owner/repo#N`) is never even extracted as a candidate, and a
tweet with no `#N` reference at all never becomes one either. See
`recipe.json`'s `confidence_notes` for the full reasoning behind the flat
0.8 score — the same as `dangling-issue-reference`'s own commit-sourced
twin, deliberately higher than `mention-dangling-reference`'s 0.75: this
town authored the tweet on purpose, following its own convention, not a
stranger guessing at a number in their own head.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src:../RECIPES/own-tweet-dangling-reference uv run python ../RECIPES/own-tweet-dangling-reference/detector.py
```

It finds one real gap in its own fixture (a tweet pointing at "#412" when
neither issue nor PR #412 exists, confidence 0.8) and correctly excludes
two references that DO resolve (#219 named twice, an issue; #300, a merged
PR), while a cross-repo reference (`arcadeai/gasstation#42`) and a tweet
with no reference at all never become candidates in the first place.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/own-tweet-dangling-reference/recipe.json
```
