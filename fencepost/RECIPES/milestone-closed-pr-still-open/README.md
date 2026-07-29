# milestone-closed-pr-still-open

The eleventh real recipe — the pull-request-side mirror of
`milestone-closed-issue-still-open` (task 379), the same pairing shape
`merged-pr-issue-still-open`/`issue-closed-pr-still-open` already
established for issues vs pull requests.

**The seam it watches:** a milestone reads `state=closed`, but one of the
pull requests assigned to it still reads `state=open` — neither merged nor
closed some other way. Closing a milestone on GitHub is a pure label
operation — it never touches the state of a single pull request inside it
any more than it touches an issue's, so there is no auto-close wiring here
at all, not even a broken one. A human (or a god) closes the milestone
believing the work inside it is done, and a pull request left open inside
it is the exact seam this recipe watches — it exists only by holding the
milestone record and the pull request record at the same instant, neither
alone shows it. Two fixtures, no live account —
[`../../fixtures/milestone_closed_pr_still_open/milestones.json`](../../fixtures/milestone_closed_pr_still_open/milestones.json)
and [`../../fixtures/milestone_closed_pr_still_open/pull_requests.json`](../../fixtures/milestone_closed_pr_still_open/pull_requests.json)
— shaped like what `ListMilestones`/`ListPullRequests` would actually
return. Both scopes are already declared elsewhere in this repo; no new
scope asked for anywhere in this recipe.

Confidence is age-gated on how long the milestone has been closed while the
pull request sits open, matching `milestone-closed-issue-still-open`'s own
24-hour bar exactly — the same underlying seam shape applied to a
different record type does not earn a different threshold. See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/milestone-closed-pr-still-open/detector.py
```

Run bare like this it uses the real wall clock, so the fixture pull
requests' ages (and therefore which ones clear 24 hours) will drift as
real time passes — expected for a manual demo, not a bug, the same
documented property every age-gated MOCK-only fixture in this repo already
carries. The test suite always pins `now` explicitly so the result stays
deterministic in CI.

It finds one real gap in its own fixture (pull request #901, confidence
0.85 — its milestone closed well over 24 hours before the pinned clock)
and correctly excludes pull request #903 (already closed itself — merged,
in fact — so there's no gap left to surface even though its milestone is
also closed), pull request #904 (assigned to a milestone that is still
open — the ordinary, unremarkable case), and pull request #905 (carries no
milestone at all), while pull request #902 (its milestone closed only
hours before the pinned clock) is weighed and shown in the tail as a
coincidence, not hidden and not electing itself.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/milestone-closed-pr-still-open/recipe.json
```
