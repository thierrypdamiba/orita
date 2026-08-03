# readme-claims-unmerged-pr

The thirty-seventh real recipe (ROADMAP.md #493). The PR-side twin of
[`../readme-claims-open-milestone/`](../readme-claims-open-milestone/) (task
491, a `milestone #N` claim) and
[`../readme-claims-unfixed-issue/`](../readme-claims-unfixed-issue/) (task
492, a closing-keyword claim): README's own `claims-X` family had a
milestone leg and an issue leg but no PR leg, unlike both siblings in the
wider `claims-*` family, which each already carry all three —
`release-claims-open-milestone` + `release-claims-unfixed-issue` +
`release-claims-unmerged-pr`, and `tweet-claims-open-milestone` +
`tweet-claims-unfixed-issue` + `tweet-claims-unmerged-pr`. This is the last
missing leg.

**The seam it watches:** README.md says a PR shipped ("ships #N" /
"includes #N" / "merges #N" / "via #N"), but PR #N is not actually merged —
still open, or closed without merging. A README is as permanent and public
as a release note or a tweet once pushed, and nothing on GitHub's side ever
checks it against the PR tracker's own truth. Two fixtures, no live
account —
[`../../fixtures/readme_claims_unmerged_pr/readme.json`](../../fixtures/readme_claims_unmerged_pr/readme.json)
and
[`../../fixtures/readme_claims_unmerged_pr/pulls.json`](../../fixtures/readme_claims_unmerged_pr/pulls.json)
— shaped like what `GetFileContents` and `ListPullRequests` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table. No new
scope is asked for anywhere in this recipe.

A claimed PR that doesn't exist at all is excluded here, named not hidden —
that broken reference belongs to `dangling-issue-reference`'s own seam, not
this one's. A claimed PR that IS merged is excluded too — the claim was
simply true.

Confidence is deliberately NOT age-gated, the same reasoning
`readme-claims-open-milestone` and `readme-claims-unfixed-issue` already
gave for their own README reads: a `GetFileContents` call returns
README's current text, not a change history, so there is no per-claim
timestamp to weigh a staleness window against, and no race applies either
— a README is read live, so a claim it currently makes and the PR's
currently-unmerged state are both true at the same instant the scan runs.
Flat 0.85 on every surfaced claim. See `recipe.json`'s `confidence_notes`
for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/readme-claims-unmerged-pr/detector.py
```

It finds one real gap in its own fixture (README's claim about PR #901,
confidence 0.85 — still open) and correctly excludes #902 (claim holds,
merged) and #999 (no such PR — dangling-issue-reference's own seam), while
`#905` in "Background discussion lives in #905" is never extracted at all
(no claim verb precedes it). A duplicate claim about #902 inside README's
own text ("Includes #902 ... merges #902 again") is de-duplicated to a
single excluded candidate, not two.

The claim regex (`ships?|includes?|merges?|via #N`) is shared with
[`../release-claims-unmerged-pr/`](../release-claims-unmerged-pr/),
[`../merged-pr-never-released/`](../merged-pr-never-released/), and
[`../tweet-claims-unmerged-pr/`](../tweet-claims-unmerged-pr/) via
[`seam_engine/pr_claims.py`](../../seam_engine/src/seam_engine/pr_claims.py)
— this recipe imports `claimed_pr_numbers` from there rather than carrying
a fourth, independently typed copy of the identical regex.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/readme-claims-unmerged-pr/recipe.json
```
