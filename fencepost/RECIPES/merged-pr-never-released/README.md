# merged-pr-never-released

The twelfth real recipe — the inverse of `release-claims-unmerged-pr`
(task 378, the ninth real recipe). That recipe watches a release's own
body making a FALSE claim about a PR that exists but never merged; this
one watches the opposite direction: a PR that genuinely merged, sitting
stale, that no release published since has ever claimed at all.

**The seam it watches:** a pull request reads `merged=true`, but its own
number never appears inside any release's claim phrase ("ships #N" /
"includes #N" / "merges #N" / "via #N", the identical regex
`release-claims-unmerged-pr` already uses — one law, not two copies of it
drifting apart between the two recipes that both read release bodies).
Unlike that recipe, which only ever needs to check one release's own body
against the PR tracker, this one checks a merged PR against EVERY release
read so far — a PR can go uncredited across several releases in a row, not
only the newest one, so clearing the latest release alone is not enough to
prove it isn't a gap. Two fixtures, no live account —
[`../../fixtures/merged_pr_never_released/pull_requests.json`](../../fixtures/merged_pr_never_released/pull_requests.json)
and [`../../fixtures/merged_pr_never_released/releases.json`](../../fixtures/merged_pr_never_released/releases.json)
— shaped like what `ListPullRequests` and repeated `GetLatestRelease` reads
over time would actually return. Both scopes are already declared
elsewhere in this repo; no new scope asked for anywhere in this recipe.

Confidence is age-gated by hours since the pull request's own `merged_at`,
not any one release's publish time — this seam is about a PR sitting
stale with no release ever having picked it up, so the clock starts at the
merge. The bar is 96 hours (four days), longer than
`release-claims-unmerged-pr`'s 24h same-body check and longer than
`contributor-thanked-not-credited`'s 72h README-edit window too — this
recipe is genuinely waiting on the project's own release cadence to catch
up, a slower real-world signal than either. See `recipe.json`'s
`confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/merged-pr-never-released/detector.py
```

Run bare like this it uses the real wall clock, so the fixture pull
requests' ages (and therefore which ones clear 96 hours) will drift as
real time passes — expected for a manual demo, not a bug, the same
documented property every age-gated MOCK-only fixture in this repo already
carries. The test suite always pins `now` explicitly so the result stays
deterministic in CI.

It finds one real gap in its own fixture (pull request #1001, confidence
0.85 — merged well over 96 hours before the pinned clock, and no release
read so far names it) and correctly excludes pull request #1003 (merged,
but release v0.9.4's own body claims it — the promise was kept), pull
request #1004 (still open — nothing for a release to have missed yet),
and pull request #1005 (closed without merging — same reason), while pull
request #1002 (merged only hours before the pinned clock) is weighed and
shown in the tail as a coincidence, not hidden and not electing itself.

The claim regex (`ships?|includes?|merges?|via #N`) is shared with
[`../release-claims-unmerged-pr/`](../release-claims-unmerged-pr/), the
mirror recipe that reads the same claim phrase from the other direction.
Both detectors now import `claimed_pr_numbers` from
[`seam_engine/pr_claims.py`](../../seam_engine/src/seam_engine/pr_claims.py)
rather than each carrying its own independently typed copy — this recipe's
own docstring used to claim the regex was "identical... on purpose" but
never actually imported it; task 393 fixed that, the same "two copies that
happen to agree today" gap tasks 389 and 390 already fixed for `#N`
extraction and the "milestone #N" claim phrase. See
`seam_engine/tests/test_pr_claims.py`'s `TestBothDetectorsShareTheLaw` for
the regression test that would go red if either detector ever went back
to a local copy.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/merged-pr-never-released/recipe.json
```
