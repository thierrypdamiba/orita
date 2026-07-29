# milestone-closed-never-released

The fourteenth real recipe — the milestone-side twin of
`merged-pr-never-released` (task 381, the twelfth real recipe). That
recipe watches a merged pull request sitting stale, uncredited by any
release's own claim phrase; this one watches the identical shape one level
up the same project's own record hierarchy: a milestone closed long ago
that no release published since has ever claimed.

**The seam it watches:** a milestone reads `state=closed`, but its own
number never appears inside any release's `milestone #N` claim phrase (a
claim grammar of its own — a milestone is neither a PR nor an issue, so
this recipe does not overload `merged-pr-never-released`'s
`ships`/`includes`/`merges`/`via #N` regex or the issue-side recipes'
`fixes`/`closes`/`resolves #N` closing-keyword grammar; naming its own
phrase keeps three genuinely different seams from drifting into one
shared, over-general regex). Like `merged-pr-never-released`, this recipe
checks a closed milestone against EVERY release read so far, not just the
newest one — a milestone can go uncredited across several releases in a
row just as easily as a single PR can. Two fixtures, no live account —
[`../../fixtures/milestone_closed_never_released/milestones.json`](../../fixtures/milestone_closed_never_released/milestones.json)
and [`../../fixtures/milestone_closed_never_released/releases.json`](../../fixtures/milestone_closed_never_released/releases.json)
— shaped like what `ListMilestones` and repeated `GetLatestRelease` reads
over time would actually return. Both scopes are already declared
elsewhere in this repo; no new scope asked for anywhere in this recipe.

Confidence is age-gated by hours since the milestone's own `closed_at`,
not any one release's publish time — this seam is about a milestone
sitting stale with no release ever having picked it up, so the clock
starts at the close. The bar is 96 hours (four days), matching
`merged-pr-never-released`'s own bar exactly: the same "waiting on the
project's own release cadence to catch up" reasoning applies one level up
— a milestone bundles multiple issues and pull requests, so it is at
least as plausible as a single PR that the release naming it simply
hasn't shipped yet. See `recipe.json`'s `confidence_notes` for the full
reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/milestone-closed-never-released/detector.py
```

Run bare like this it uses the real wall clock, so the fixture milestones'
ages (and therefore which ones clear 96 hours) will drift as real time
passes — expected for a manual demo, not a bug, the same documented
property every age-gated MOCK-only fixture in this repo already carries.
The test suite always pins `now` explicitly so the result stays
deterministic in CI.

It finds one real gap in its own fixture (milestone #2002 "v1.2 seam
widening", confidence 0.85 — closed well over 96 hours before the pinned
clock, and no release read so far names it) and correctly excludes
milestone #2001 "v1.0 launch bundle" (closed, but the OLDER release
`v1.0.0` — not the newest one read — already claims it, proving the
"scans every release read so far" property this recipe exists for) and
milestone #2004 "v2.0 future" (still open — nothing for a release to have
missed yet), while milestone #2003 "v1.4 hotfix batch" (closed only hours
before the pinned clock) is weighed and shown in the tail as a
coincidence, not hidden and not electing itself.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/milestone-closed-never-released/recipe.json
```
