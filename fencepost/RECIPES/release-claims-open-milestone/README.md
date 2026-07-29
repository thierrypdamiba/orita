# release-claims-open-milestone

The sixteenth real recipe (ROADMAP.md #385). The milestone-side third leg
of the release-claims-X family, alongside
[`../release-claims-unmerged-pr/`](../release-claims-unmerged-pr/) (task
378, a release's false claim about a PR that never merged) and
[`../release-claims-unfixed-issue/`](../release-claims-unfixed-issue/)
(task 382, a release's false claim about an issue that never closed). All
three watch the identical "a release's own permanent record disagrees with
a second record's real state" shape, applied to a third record type in
turn.

**The seam it watches:** a GitHub release's own body text invokes a
`milestone #N` claim phrase — [`../milestone-closed-never-released/`](../milestone-closed-never-released/)
(task 383)'s own grammar, reused verbatim rather than inventing a fourth
copy of the same word's claim regex — but milestone #N is still open. A
release is a permanent public statement; nothing on GitHub's side ever
checks it against the milestone tracker's own truth — closing a milestone
is a pure label operation with no wiring back to any release at all. Two
fixtures, no live account —
[`../../fixtures/release_claims_open_milestone/releases.json`](../../fixtures/release_claims_open_milestone/releases.json)
and
[`../../fixtures/release_claims_open_milestone/milestones.json`](../../fixtures/release_claims_open_milestone/milestones.json)
— shaped like what a releases read and `ListMilestones` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table. No new
scope is asked for anywhere in this recipe.

A claimed milestone that doesn't exist at all is excluded here, named not
hidden — a broken reference is not this recipe's own seam. A claimed
milestone that IS closed is excluded too — the claim was simply true.

Confidence is age-gated by the release's own publish time: a claim checked
within 24 hours of publish scores 0.5 (below the bar — could be a real
close/release ordering race); at or past 24 hours it scores 0.85 (the
release body is static once published, so a claim that's stayed false for
a full day is unambiguous). See `recipe.json`'s `confidence_notes` for the
full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/release-claims-open-milestone/detector.py
```

Run bare like this it uses the real wall clock, so the fixture releases'
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

It finds one real gap in its own fixture (release `v1.6.0`'s claim about
milestone #4001, confidence 0.85 — still open, stale) and correctly
excludes milestone #4004 (claim holds, closed), `v1.6.2`'s claim about
#4999 (no such milestone), and `v1.6.3` (no claim phrase at all), while
`v1.6.1`'s claim about #4003 (a few hours old) is weighed and shown in the
tail as a coincidence, not hidden and not electing itself primary. A
duplicate claim inside `v1.6.0`'s own body ("Ships milestone #4001 and
ships milestone #4001 again") is de-duplicated to a single candidate, not
two.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/release-claims-open-milestone/recipe.json
```
