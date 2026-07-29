# issue-closed-never-released

The seventeenth real recipe — the issue-side twin of
`merged-pr-never-released` (task 381, the twelfth real recipe) and
`milestone-closed-never-released` (task 383, the fourteenth). Those two
recipes watch a merged pull request and a closed milestone, each sitting
stale, uncredited by any release published since. This one watches the
same shape against the third GitHub record type a release's own body can
claim credit for: an issue.

**The seam it watches:** an issue reads `state=closed`, but its own number
never appears inside any release's real GitHub closing-keyword claim
(`fixes`/`closes`/`resolves #N`, both tenses — the identical grammar
`tools/closing_keyword_guard.py` and `release-claims-unfixed-issue`'s own
detector already use). Unlike its two siblings, this recipe does not name
a new claim phrase of its own — an issue already has a real, canonical
credit phrase GitHub itself recognizes, so reusing it is the honest move,
not a third invented regex. Like its siblings, this recipe checks a closed
issue against EVERY release read so far, not just the newest one — an
issue can go uncredited across several releases in a row just as easily as
a PR or milestone can. Two fixtures, no live account —
[`../../fixtures/issue_closed_never_released/issues.json`](../../fixtures/issue_closed_never_released/issues.json)
and [`../../fixtures/issue_closed_never_released/releases.json`](../../fixtures/issue_closed_never_released/releases.json)
— shaped like what `ListIssues` and repeated `GetLatestRelease` reads over
time would actually return. Both scopes are already declared elsewhere in
this repo; no new scope asked for anywhere in this recipe.

Confidence is age-gated by hours since the issue's own `closed_at`, not
any one release's publish time — this seam is about an issue sitting
stale with no release ever having picked it up, so the clock starts at the
close. The bar is 96 hours (four days), matching `merged-pr-never-released`'s
and `milestone-closed-never-released`'s own bar exactly: the same "waiting
on the project's own release cadence to catch up" reasoning, the third
record type. See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/issue-closed-never-released/detector.py
```

Run bare like this it uses the real wall clock, so the fixture issues'
ages (and therefore which ones clear 96 hours) will drift as real time
passes — expected for a manual demo, not a bug, the same documented
property every age-gated MOCK-only fixture in this repo already carries.
The test suite always pins `now` explicitly so the result stays
deterministic in CI.

It finds one real gap in its own fixture (issue #5002 "Correct the n-1
counter's off-by-one at midnight UTC rollover", confidence 0.85 — closed
well over 96 hours before the pinned clock, and no release read so far
claims it) and correctly excludes issue #5001 "Fix broken pagination on
the archive index" (closed, but release `v1.0.0` claims it with a real
"fixes #5001") and issue #5004 "Investigate flaky test_the_tithe roll"
(still open — nothing for a release to have missed yet), while issue #5003
"Typo in ONBOARDING.md step 3" (closed only hours before the pinned clock)
is weighed and shown in the tail as a coincidence, not hidden and not
electing itself. Release `v1.2.0`'s bare "see #5002 for background"
mention is proven to NOT clear issue #5002 — no real closing keyword, so
it is not a credit claim.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/issue-closed-never-released/recipe.json
```
