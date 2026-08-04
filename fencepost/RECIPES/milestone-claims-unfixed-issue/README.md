# milestone-claims-unfixed-issue

The forty-fifth real recipe: the issue leg of the claims-X family,
applied to the one text surface it had never reached. README, a release
body, and a tweet each already carry all three claims-X legs —
[`../readme-claims-unfixed-issue/`](../readme-claims-unfixed-issue/) +
`readme-claims-unmerged-pr` +
[`../readme-claims-open-milestone/`](../readme-claims-open-milestone/),
[`../release-claims-unfixed-issue/`](../release-claims-unfixed-issue/) +
`release-claims-unmerged-pr` + `release-claims-open-milestone`, and
`tweet-claims-unfixed-issue` + `tweet-claims-unmerged-pr` +
`tweet-claims-open-milestone` — but a milestone's own `description`
field, already read for *dangling* references by
[`../milestone-body-dangling-reference/`](../milestone-body-dangling-reference/)
(task 504/511), had never been checked for this different, sibling
shape: not "does `#N` exist at all" but "this text claims `#N` is FIXED,
and it is not."

**The seam it watches:** a milestone description routinely says "fixes
#40, tracking here" the same way a README changelog line does, and
nothing on GitHub's side ever checks it against the issue tracker's own
state. `milestone-closed-issue-still-open` and `milestone-closed-pr-
still-open` check a genuinely different mechanism — the milestone's own
`state` FLAG against its issue membership — never a keyword phrase
sitting inside its free-text description. This recipe closes that gap
the same way `readme-claims-unfixed-issue` closed it for README: the
identical closing-keyword grammar, checked against a different permanent
public record.

Deliberately reuses
[`seam_engine.closing_keywords.CLOSING_KEYWORD_RE`](../../seam_engine/src/seam_engine/closing_keywords.py)
verbatim — the same shared grammar
[`../commit-closes-keyword-issue-still-open/`](../commit-closes-keyword-issue-still-open/),
[`../issue-closed-never-released/`](../issue-closed-never-released/),
`release-claims-unfixed-issue`, and `readme-claims-unfixed-issue` already
import from — rather than a sixth independently-retyped copy of the
identical pattern.

Two fixture lists, no live account —
[`../../fixtures/milestone_claims_unfixed_issue/milestones.json`](../../fixtures/milestone_claims_unfixed_issue/milestones.json)
and
[`.../issues.json`](../../fixtures/milestone_claims_unfixed_issue/issues.json)
— shaped like what `ListMilestones` and `ListIssues` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table. No
new scope is asked for anywhere in this recipe.

A claimed issue that doesn't exist at all is excluded here, named not
hidden — that broken reference is `milestone-body-dangling-reference`'s
own seam, not this one's. A claimed issue that IS closed is excluded too
— the claim was simply true. A milestone with no description at all
never becomes a candidate — it never claims anything about a second
record, so there is no seam to weigh. "closing #N" (present participle,
Iron Rule #8's own prescribed safe phrasing) never matches either tense
— proven live in the fixture (milestone #66), not just claimed.

**Confidence is age-gated off the milestone's own `updated_at`,**
mirroring `milestone-body-dangling-reference`'s own reasoning rather than
`readme-claims-unfixed-issue`'s flat 0.85: a `GetFileContents` read of
README returns CURRENT text with no per-line edit timestamp to weigh, but
a milestone object carries a real `updated_at` — and, like an issue or PR
body, its description is a text surface its author can still edit at any
time. A claim less than 24 hours old scores 0.55 (may still get fixed); one
untouched for at least 24 hours scores 0.85 (nobody is coming back for
it). See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src:../RECIPES/milestone-claims-unfixed-issue uv run python ../RECIPES/milestone-claims-unfixed-issue/detector.py
```

Against its own fixture it elects one primary gap (milestone #60's stale
claim that "fixes #601", 24+ hours since its own last update, confidence
0.85) and weighs one coincidence in the tail (milestone #61's fresh claim
that "closes #602", confidence 0.55). It correctly excludes milestone
#62's claim about the real, already-closed issue #603 (the claim was
true), milestone #63's claim about #9999 (no such issue exists — that's
`milestone-body-dangling-reference`'s own seam), a milestone with no
description at all (#64), a milestone whose description carries no
closing-keyword claim (#65), and a milestone that only ever writes
"closing #601" — present participle, which never matches either tense
(#66).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/milestone-claims-unfixed-issue/recipe.json
```
