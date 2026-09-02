# issue-body-claims-unmerged-pr

The ninety-seventh real recipe.

**The seam it watches:** an issue or pull request's own OPENING BODY
invokes a real GitHub closing-keyword claim ("fixes #N" / "closes #N" /
"resolves #N", both tenses —
[`seam_engine.closing_keywords.closing_keyword_numbers`](../../seam_engine/src/seam_engine/closing_keywords.py),
the same shared grammar the issue-tracker-side sibling already imports)
against a PULL REQUEST, but the named pull request never actually
merged.
[`../issue-body-claims-unfixed-issue/`](../issue-body-claims-unfixed-issue/)
(the ninety-sixth real recipe) drew this exact line and left it open on
purpose, by name, in its own docstring: it "deliberately checks only
the issue list, never the PR list ... a closing-keyword claim naming a
real pull request is a future `issue-body-claims-unmerged-pr`'s own
remit, not this one's." This recipe is that remit, kept — the PR-side
twin of that recipe, built the same way
[`../commit-closes-keyword-pr-still-open/`](../commit-closes-keyword-pr-still-open/)
was already built as
[`../commit-closes-keyword-issue-still-open/`](../commit-closes-keyword-issue-still-open/)'s
own twin: same fixture shape (one sibling fixture directory, swap the
target record type from issue to PR), same shared-module import
discipline, same test rigor.

The seam is the identical shape the issue-tracker-side sibling's own
docstring already proved, applied here to the PR tracker: GitHub only
ever honors a closing keyword when it reads one inside a pull request's
own body or a commit message, and only once that PR actually merges to
the default branch (`commit-closes-keyword-pr-still-open`'s own seam,
on the commit-message side). An issue's own opening body carries no
merge event of its own to trigger on at all — GitHub never honors a
closing keyword sitting there, full stop — and a still-open PR's own
opening body is exactly as inert as an issue's, right up until the
moment (if ever) it merges. A claim sitting in either object's
still-open body, naming a PR that stays open too, was never going to
resolve itself while both stay open.

Two fixtures, no live account —
[`../../fixtures/issue_body_claims_unmerged_pr/issues.json`](../../fixtures/issue_body_claims_unmerged_pr/issues.json)
and
[`pulls.json`](../../fixtures/issue_body_claims_unmerged_pr/pulls.json)
— shaped like what `ListIssues` and `ListPullRequests` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table,
already live, read-only tools on the-hand gateway today; `source:
"fixture"` in `run_recipe_scan`'s own output is the honest MOCK ONLY
marker CONTRIBUTING.md requires of every recipe on the day it merges,
not a claim the underlying scopes are unavailable.

A claimed pull request that doesn't exist at all is excluded here,
named not hidden — including a claim that happens to land on a real
ISSUE number instead of a PR: out of this recipe's own remit either
way, the mirror image of the issue-tracker-side sibling's own boundary
(that recipe excludes a claim naming a real PR number the same way).
The two recipes never collide on the same candidate — each covers
exactly its own half of the shared number space. A claimed PR that IS
resolved — merged OR closed without merging — is excluded too, mirroring
[`../commit-closes-keyword-pr-still-open/`](../commit-closes-keyword-pr-still-open/)'s
own `_RESOLVED_STATES` reasoning: the claim was simply true, or moot. A
body with no closing-keyword phrase at all, or no body at all, never
becomes a candidate either — neither claims anything about a second
record, so there is no seam to weigh.

Confidence is age-gated off the claiming record's own `updated_at`,
mirroring the issue-tracker-side sibling's identical reasoning: an
issue or PR body is a text surface its own author can still edit at any
time, so a fresh claim earns a 24-hour grace period before being scored
as a confirmed gap (0.55 within the window, 0.85 past it). See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/issue-body-claims-unmerged-pr/detector.py
```

Run bare like this it uses the real wall clock, so the fixture records'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against its own fixture, at the pinned test clock, it elects one
primary gap (issue `#40`'s claim that it closes PR `#501`, confidence
0.85, last updated well past the 24h bar) and weighs two coincidences
in the tail (issue `#45`'s fresher duplicate claim about PR `#501`, and
PR `#60`'s own claim about PR `#501` — its own doubled "fixes #501 ...
fixes #501" collapsed to one candidate by the same de-duplication the
issue-tracker-side sibling holds — both at confidence 0.55, both
updated inside the 24h window at the pinned test clock), while
correctly excluding issue `#41`'s claim about PR `#502` (true — merged),
PR `#61`'s claim about PR `#503` (true — closed without merging),
issue `#42`'s claim about `#999` (no such pull request), and issue
`#46`'s claim about `#40` (a real ISSUE number, not a PR — out of this
recipe's remit, excluded the same as a genuinely dangling number).
Issue `#43` (no body at all) and PR `#62` (a bare `#998` aside, no
closing-keyword phrase) never become candidates at all.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/issue-body-claims-unmerged-pr/recipe.json
```
