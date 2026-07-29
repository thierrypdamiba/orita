# release-claims-unmerged-pr

The ninth real recipe (ROADMAP.md #378). Every recipe before this one either
compared two honest records against each other
([`../merged-pr-issue-still-open/`](../merged-pr-issue-still-open/),
[`../release-not-tweeted/`](../release-not-tweeted/)) or checked a single
record's claim about a second, MISSING one
([`../dangling-issue-reference/`](../dangling-issue-reference/)). This one
watches a third shape: a single record's claim about a second record that
DOES exist, but whose real state contradicts the claim.

**The seam it watches:** a GitHub release's own body text says a PR shipped
in it ("ships #N" / "includes #N" / "merges #N" / "via #N"), but PR #N is
not actually merged — still open, or closed without merging. A release is
a permanent public statement; nothing on GitHub's side ever checks it
against the PR tracker's own truth. Two fixtures, no live account —
[`../../fixtures/release_claims_unmerged_pr/releases.json`](../../fixtures/release_claims_unmerged_pr/releases.json)
and
[`../../fixtures/release_claims_unmerged_pr/pulls.json`](../../fixtures/release_claims_unmerged_pr/pulls.json)
— shaped like what a releases read and `ListPullRequests` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table. No new
scope is asked for anywhere in this recipe.

A claimed PR that doesn't exist at all is excluded here, named not hidden —
that broken reference belongs to `dangling-issue-reference`'s own seam, not
this one's. A claimed PR that IS merged is excluded too — the claim was
simply true.

Confidence is age-gated by the release's own publish time: a claim checked
within 24 hours of publish scores 0.5 (below the bar — could be a real
merge/release ordering race); at or past 24 hours it scores 0.85 (the
release body is static once published, so a claim that's stayed false for
a full day is unambiguous). See `recipe.json`'s `confidence_notes` for the
full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/release-claims-unmerged-pr/detector.py
```

Run bare like this it uses the real wall clock, so the fixture releases'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

It finds one real gap in its own fixture (release `v0.9.0`'s claim about
PR #901, confidence 0.85 — still open, 50 hours stale) and correctly
excludes PR #902 (claim holds, merged), `v0.9.2`'s claim about #999 (no
such PR — dangling-issue-reference's seam), and `v0.9.3` (no claim phrase
at all), while `v0.9.1`'s claim about #903 (4 hours old) is weighed and
shown in the tail as a coincidence, not hidden and not electing itself
primary. A duplicate claim inside `v0.9.0`'s own body ("Ships #901 and via
#901 again") is de-duplicated to a single candidate, not two.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/release-claims-unmerged-pr/recipe.json
```
