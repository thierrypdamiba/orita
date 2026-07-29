# release-claims-unfixed-issue

The thirteenth real recipe (ROADMAP.md #382). The issue-side twin of
[`../release-claims-unmerged-pr/`](../release-claims-unmerged-pr/) (task
378) — that recipe watches a release's own body making a false claim about
a PR that never merged; this one watches the same permanent-record shape
against an **issue's** open/closed state, using a real GitHub closing
keyword rather than a looser claim phrase.

**The seam it watches:** a GitHub release's own body text invokes a real
closing keyword against an issue ("fixes #N" / "closes #N" / "resolves
#N", both tenses — [`tools/closing_keyword_guard.py`](../../../tools/closing_keyword_guard.py)'s
own grammar, reused verbatim, the same discipline
[`../commit-closes-keyword-issue-still-open/`](../commit-closes-keyword-issue-still-open/)
(task 377) already established), but issue #N is still open. A release is
a permanent public statement; nothing on GitHub's side ever checks it
against the issue tracker's own truth — GitHub's auto-close wiring only
ever fires on a merge or a direct push carrying the keyword, never on a
release body. Two fixtures, no live account —
[`../../fixtures/release_claims_unfixed_issue/releases.json`](../../fixtures/release_claims_unfixed_issue/releases.json)
and
[`../../fixtures/release_claims_unfixed_issue/issues.json`](../../fixtures/release_claims_unfixed_issue/issues.json)
— shaped like what a releases read and `ListIssues` would actually return.
Both scopes already sit on `SCOPES.md`'s cleared oath table. No new scope
is asked for anywhere in this recipe.

A claimed issue that doesn't exist at all is excluded here, named not
hidden — that broken reference belongs to
[`../dangling-issue-reference/`](../dangling-issue-reference/)'s own seam,
not this one's. A claimed issue that IS closed is excluded too — the claim
was simply true. "closing #N" (present participle, Iron Rule #8's own
prescribed safe phrasing) never matches either tense — proven live, not
just claimed.

Confidence is age-gated by the release's own publish time: a claim checked
within 24 hours of publish scores 0.5 (below the bar — could be a real
fix/release ordering race); at or past 24 hours it scores 0.85 (the
release body is static once published, so a claim that's stayed false for
a full day is unambiguous). See `recipe.json`'s `confidence_notes` for the
full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/release-claims-unfixed-issue/detector.py
```

Run bare like this it uses the real wall clock, so the fixture releases'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

It finds one real gap in its own fixture (release `v1.1.0`'s claim about
issue #1101, confidence 0.85 — still open, stale) and correctly excludes
issue #1102 (claim holds, closed), `v1.1.2`'s claim about #1999 (no such
issue — dangling-issue-reference's seam), and `v1.1.3` (no closing-keyword
phrase at all), while `v1.1.1`'s claim about #1103 (a few hours old) is
weighed and shown in the tail as a coincidence, not hidden and not
electing itself primary. A duplicate claim inside `v1.1.0`'s own body
("Fixes #1101 and fixes #1101 again") is de-duplicated to a single
candidate, not two.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/release-claims-unfixed-issue/recipe.json
```
