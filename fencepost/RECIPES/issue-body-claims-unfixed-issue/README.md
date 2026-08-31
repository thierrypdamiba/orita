# issue-body-claims-unfixed-issue

The ninety-sixth real recipe.

**The seam it watches:** an issue or pull request's own OPENING BODY
invokes a real GitHub closing-keyword claim ("fixes #N" / "closes #N" /
"resolves #N", both tenses —
[`seam_engine.closing_keywords.closing_keyword_numbers`](../../seam_engine/src/seam_engine/closing_keywords.py),
the same shared grammar nine prior siblings already import) against an
issue, but the named issue never actually closed.
[`../issue-comment-claims-unfixed-issue/`](../issue-comment-claims-unfixed-issue/)
(the fifty-eighth real recipe) checks the identical claim grammar
against an issue or PR's ordinary TIMELINE COMMENT thread — a genuinely
different GitHub object from the OPENING BODY
[`../issue-body-dangling-reference/`](../issue-body-dangling-reference/)
(the twenty-fourth) and
[`../issue-body-claims-open-milestone/`](../issue-body-claims-open-milestone/)
(the ninety-second) already watch for two other claim shapes on this
exact surface. Neither of those two ever checks a closing-keyword claim
against the issue tracker's own state, so the unfixed-issue leg of this
surface had never actually been built anywhere until now. This recipe
is that seam — the issue/PR-body-sourced sibling of
`issue-comment-claims-unfixed-issue`, applying its identical grammar to
the opening body instead of a timeline comment.

The seam is as sharp here as on `issue-comment-claims-unfixed-issue`'s
own: a closing keyword only ever auto-closes an issue when GitHub reads
it in a pull request's own body or a commit message merged to the
default branch
([`../commit-closes-keyword-issue-still-open/`](../commit-closes-keyword-issue-still-open/)'s
and
[`../merged-pr-issue-still-open/`](../merged-pr-issue-still-open/)'s own
seam) — for an ORDINARY ISSUE's own opening body, GitHub never honors
the closing keyword at all (issues carry no merge event to trigger on),
and even on a PULL REQUEST's own opening body, the keyword only fires
once that PR actually merges. A claim sitting in either object's
still-open body was never going to resolve itself while it stays open.

Two fixtures, no live account —
[`../../fixtures/issue_body_claims_unfixed_issue/issues.json`](../../fixtures/issue_body_claims_unfixed_issue/issues.json)
and
[`pulls.json`](../../fixtures/issue_body_claims_unfixed_issue/pulls.json)
— shaped like what `ListIssues` and `ListPullRequests` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table,
already live, read-only tools on the-hand gateway today; `source:
"fixture"` in `run_recipe_scan`'s own output is the honest MOCK ONLY
marker CONTRIBUTING.md requires of every recipe on the day it merges,
not a claim the underlying scopes are unavailable.

A claimed issue that doesn't exist at all is excluded here, named not
hidden — that broken reference belongs to `issue-body-dangling-
reference`'s own seam, not this one's (a bare `#N` reference and a
closing-keyword `#N` claim name the same number space, but that recipe
only ever asks whether the reference resolves, never whether a
closing-keyword claim about it holds). A claimed issue that IS closed
is excluded too — the claim was simply true. A body with no closing-
keyword phrase at all, or no body at all, never becomes a candidate
either — neither claims anything about a second record, so there is no
seam to weigh. Deliberately checks only the issue list, never the PR
list — the identical scope every sibling `*-claims-unfixed-issue`
recipe already holds itself to; a closing-keyword claim naming a real
pull request is a future `issue-body-claims-unmerged-pr`'s own remit,
not this one's.

Confidence is age-gated off the claiming record's own `updated_at`,
mirroring `issue-body-dangling-reference`'s, `issue-body-claims-open-
milestone`'s, and `issue-comment-claims-unfixed-issue`'s identical
reasoning: an issue or PR body is a text surface its own author can
still edit at any time, so a fresh claim earns a 24-hour grace period
before being scored as a confirmed gap (0.55 within the window, 0.85
past it). See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/issue-body-claims-unfixed-issue/detector.py
```

Run bare like this it uses the real wall clock, so the fixture records'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture, at the pinned test clock, it elects one
primary gap (issue `#2203`'s claim that it fixes `#2201`, confidence
0.85, last updated well past the 24h bar) and weighs three coincidences
in the tail (issue `#2207`'s fresher duplicate claim about `#2201`, PR
`#52`'s claim about `#2201` — its own doubled "fixes #2201 ... fixes
#2201" collapsed to one candidate by the same de-duplication every
sibling recipe holds — and PR `#53`'s claim about `#2205`, all three at
confidence 0.55, all updated inside the 24h window at the pinned test
clock), while correctly excluding issue `#2204`'s claim about `#2202`
(true — closed) and issue `#2205`'s claim about `#2999` (no such issue
— `issue-body-dangling-reference`'s own seam). Issue `#2206` (no body
at all) and PR `#55` (a bare `#2998` aside, no closing-keyword phrase)
never become candidates at all.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/issue-body-claims-unfixed-issue/recipe.json
```
