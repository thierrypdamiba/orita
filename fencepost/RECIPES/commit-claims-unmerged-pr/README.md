# commit-claims-unmerged-pr

The seventy-third real recipe, and a correction of the last one's own
recorded reasoning: [ROADMAP.md #604](../../../ROADMAP.md) named
`commit-claims-unfixed-issue` and `commit-claims-unmerged-pr` together as
"the two structurally unfillable cells... already covered under the
`commit-closes-keyword-*` names," and closed the ten-source-by-three-target
claims-X grid at 28/30 genuinely open cells on that basis. Rechecked
against the live code rather than trusted on its own word: true for
`commit-claims-unfixed-issue` (its claim grammar — GitHub's real
closing-keyword parser, `fixes/closes/resolves #N` — is already the exact
grammar [`../commit-closes-keyword-issue-still-open/`](../commit-closes-keyword-issue-still-open/)
reads off a commit message; a second recipe watching the same phrase on
the same surface would be a pure duplicate). False for
`commit-claims-unmerged-pr`: nine prior recipes —
[`../release-claims-unmerged-pr/`](../release-claims-unmerged-pr/) and
eight siblings — all key off the structurally different
`seam_engine.pr_claims.PR_CLAIM_RE` grammar (`ships/includes/merges/via
#N`), a phrase GitHub's closing-keyword parser has never recognized on
any surface. [`../commit-closes-keyword-pr-still-open/`](../commit-closes-keyword-pr-still-open/)
imports only `CLOSING_KEYWORD_RE`, never `PR_CLAIM_RE` — the door task
604 read as shut was open the whole time; it was only ever checked from
one side.

**The seam it watches:** a commit's own message invokes a real
`ships/includes/merges/via #N` claim phrase against a pull request
number, but the named pull request is not actually merged. The identical
PR-claim check `release-claims-unmerged-pr` already runs against a
release body, applied here to the one surface the family had never
reached: a commit message. [`../commit-claims-open-milestone/`](../commit-claims-open-milestone/)
(the sixty-sixth recipe) already proved the analogous move for the
milestone-claim grammar — a commit message *can* carry a
"Ships milestone #N" claim, checked against `ListMilestones` — this
recipe is the identical move for the PR-claim grammar, checked against
`ListPullRequests`.

Two fixtures, no live account —
[`../../fixtures/commit_claims_unmerged_pr/commits.json`](../../fixtures/commit_claims_unmerged_pr/commits.json)
and
[`../../fixtures/commit_claims_unmerged_pr/pulls.json`](../../fixtures/commit_claims_unmerged_pr/pulls.json)
— shaped like what `ListRepoCommits` and `ListPullRequests` would
actually return. Both scopes already sit on `SCOPES.md`'s cleared oath
table under the `github` row. No new scope is asked for anywhere in this
recipe.

A claimed PR that doesn't exist at all is excluded here, named not hidden
— that broken reference is `dangling-issue-reference`'s own seam, not
this one's. A claimed PR that IS merged is excluded too — the claim was
simply true. A commit with no `ships/includes/merges/via #N` claim phrase
at all (a bare `#N` aside, or no reference at all) never becomes a
candidate — no claim was ever made to check against the tracker.

Confidence is age-gated by the commit's own `ts`, mirroring
`commit-claims-open-milestone`'s own reasoning rather than
`dangling-issue-reference`'s flat score: a claim checked within 24 hours
of the commit landing scores 0.5 (below the bar — could be a real
merge/commit ordering race); at or past 24 hours it scores 0.85 (a commit
message is immutable once pushed, so a claim that's stayed false for a
full day is unambiguous). See `recipe.json`'s `confidence_notes` for the
full reasoning.

With this recipe shipped, the claims-X grid stands at 29/30 genuinely
open cells filled. `commit-claims-unfixed-issue` remains the one real,
permanently unfillable cell — its claim grammar and its surface are both
already fully owned by `commit-closes-keyword-issue-still-open`.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/commit-claims-unmerged-pr/detector.py
```

Run bare like this it uses the real wall clock, so the fixture commits'
own ages will drift as real time passes — expected for a manual demo, not
a bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against the pinned test clock it finds one real gap in its own fixture as
the elected primary (commit `e1f22a3`'s claim about `#941`, confidence
0.85 — still unmerged, well past the 24h bar) and one more weighed in the
tail (commit `f2a33b4`'s claim about `#942`, fresh, confidence 0.5), while
correctly excluding commit `a3b44c5` (claims `#943`, which is merged —
the claim holds), commit `b4c55d6` (claims `#999`, which doesn't exist),
and commit `c5d66e7` (a bare `#945` aside, no `ships/includes/merges/via`
claim phrase at all). A duplicate claim inside `e1f22a3`'s own message
("Ships #941... Ships #941 again") is de-duplicated to a single
candidate, not two.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/commit-claims-unmerged-pr/recipe.json
```
