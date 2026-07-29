# mention-dangling-reference

The eighteenth real recipe, and the first that reads `GetMyMentions` —
INBOUND signal from mortals, not the town's own outbound tweets. Every
prior cross-toolkit recipe
([`../release-not-tweeted/`](../release-not-tweeted/),
[`../contributor-thanked-not-credited/`](../contributor-thanked-not-credited/),
[`../readme-credited-not-thanked/`](../readme-credited-not-thanked/)) reads
what the connected X account *said*. This one reads what a stranger said
*to* it.

**The seam it watches:** GitHub renders `#N` inside any piece of text as a
clickable link without ever checking it resolves to anything — the same
seam [`../dangling-issue-reference/`](../dangling-issue-reference/) already
proved for a commit message. This recipe asks the identical question of a
mortal's own X mention of the account: does the issue or pull request they
just referenced actually exist? A mortal following up on "#99" when no
issue or PR #99 exists in this repo is a genuine cross-account confusion —
their own belief, sitting on X, is already out of sync with GitHub's real
number space, and nothing on either platform alone would ever show that.

Three fixture lists, no live account —
[`../../fixtures/mention_dangling_reference/mentions.json`](../../fixtures/mention_dangling_reference/mentions.json),
[`.../issues.json`](../../fixtures/mention_dangling_reference/issues.json),
and [`.../pulls.json`](../../fixtures/mention_dangling_reference/pulls.json)
— shaped like what `GetMyMentions`/`ListIssues`/`ListPullRequests` would
actually return. All three declared scopes already sit on `SCOPES.md`'s
cleared oath table (`GetMyMentions` since founding, never used by a recipe
until now). No new scope is asked for anywhere in this recipe.

A `#N` reference is checked against BOTH the issue list and the PR list —
GitHub shares one number sequence between them, so checking only one would
misfire on a perfectly good reference to a merged PR, exactly the
crying-wolf failure Ogun's law calls fatal. A cross-repo reference
(`owner/repo#N`) is never even extracted as a candidate — that names a
different repo's own number space on purpose, a seam for a recipe watching
*that* repo, not a gap in this one. A mention with no `#N` reference at all
never becomes a candidate either — it never claims anything about a second
record, so there is no seam to weigh. See `recipe.json`'s `confidence_notes`
for the full reasoning behind the flat 0.75 score — deliberately lower than
`dangling-issue-reference`'s own 0.8, an honest, reasoned gap, not a
copy-pasted number.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src:../RECIPES/mention-dangling-reference uv run python ../RECIPES/mention-dangling-reference/detector.py
```

It finds one real gap in its own fixture (a mention following up on "#99"
when neither issue nor PR #99 exists, confidence 0.75) and correctly
excludes two references that DO resolve (#12, an open issue; #15, a closed
one — existing is what matters, not open-vs-closed), while a cross-repo
reference (`arcadeai/gasstation#42`) and a mention with no reference at all
never become candidates in the first place.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/mention-dangling-reference/recipe.json
```
