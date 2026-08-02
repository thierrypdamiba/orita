# readme-claims-unfixed-issue

The thirty-sixth real recipe (ROADMAP.md #492). The issue-side twin of
[`../readme-claims-open-milestone/`](../readme-claims-open-milestone/)
(task 491, a `milestone #N` claim): README's own `claims-X` family had a
milestone leg and no issue leg, unlike the release and tweet families,
which each already carry all three
([`../release-claims-open-milestone/`](../release-claims-open-milestone/) +
[`../release-claims-unfixed-issue/`](../release-claims-unfixed-issue/) /
[`../tweet-claims-open-milestone/`](../tweet-claims-open-milestone/) +
[`../tweet-claims-unfixed-issue/`](../tweet-claims-unfixed-issue/)). This
recipe closes the missing leg for README the same way
`release-claims-unfixed-issue` closed it for a release body: the
identical closing-keyword grammar, checked against a different permanent
public record.

**The seam it watches:** README.md's own text invokes a real GitHub
closing keyword against an issue ("fixes #N" / "closes #N" / "resolves
#N", both tenses —
[`tools/closing_keyword_guard.py`](../../../tools/closing_keyword_guard.py)'s
own grammar, reused via
[`seam_engine.closing_keywords`](../../seam_engine/src/seam_engine/closing_keywords.py),
the same shared module
[`../commit-closes-keyword-issue-still-open/`](../commit-closes-keyword-issue-still-open/),
[`../issue-closed-never-released/`](../issue-closed-never-released/), and
`release-claims-unfixed-issue` already import from), but issue #N is
still open. A README is as public and as easy to leave stale as a
release note, and nothing on GitHub's side ever checks its prose against
the issue tracker's own truth — a "fixes #N" line in a README's own
changelog section carries no auto-close wiring at all, unlike the same
phrase in a commit or PR body merged to the default branch. Two
fixtures, no live account —
[`../../fixtures/readme_claims_unfixed_issue/readme.json`](../../fixtures/readme_claims_unfixed_issue/readme.json)
and
[`../../fixtures/readme_claims_unfixed_issue/issues.json`](../../fixtures/readme_claims_unfixed_issue/issues.json)
— shaped like what a read-only `GetFileContents` call on this repo's own
README and `ListIssues` would actually return. Both scopes already sit
on `SCOPES.md`'s cleared oath table. No new scope is asked for anywhere
in this recipe.

A claimed issue that doesn't exist at all is excluded here, named not
hidden — that broken reference is
[`../dangling-issue-reference/`](../dangling-issue-reference/)'s own
seam, not this one's. A claimed issue that IS closed is excluded too —
the claim was simply true. "closing #N" (present participle, Iron Rule
#8's own prescribed safe phrasing) never matches either tense — proven
live, not just claimed.

Confidence is deliberately **not** age-gated, unlike
`release-claims-unfixed-issue`, which weighs a claim against the
release's own publish time. A `GetFileContents` read returns README.md's
current text, not a change history, so there is no per-claim "when was
this written" timestamp to weigh a staleness window against — the same
absence `readme-claims-open-milestone`'s own docstring already named for
its own README read. There is also no race to guard against: a README is
read live, right now, so a claim it currently makes and the issue's
currently-open state are both true at the same instant the scan runs. A
flat 0.85 applies to every surfaced claim. See `recipe.json`'s
`confidence_notes` for the full reasoning.

Reuses `seam_engine.closing_keywords.closing_keyword_numbers` verbatim,
the same shared grammar three other recipes already import from there
(task 394) — a fifth independently retyped copy of the identical pattern
was exactly the drift that centralization exists to prevent.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/readme-claims-unfixed-issue/detector.py
```

The shipped fixture elects the primary gap for real:

```json
{
  "slug": "readme-claims-unfixed-issue-202",
  "headline": "README.md claims #202 fixed, but #202 is still open",
  "confidence": 0.85
}
```

...and correctly excludes #201 (claim holds, closed) and #299 (no such
issue — a dangling reference, not this recipe's seam), while #205 (named
only as background, no closing-keyword phrase attached) is never even a
candidate.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/readme-claims-unfixed-issue/recipe.json
```
