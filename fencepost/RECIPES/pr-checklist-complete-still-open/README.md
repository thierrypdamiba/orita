# pr-checklist-complete-still-open

The fifty-second real recipe (ROADMAP.md #579). [`issue-checklist-complete-still-open`](../issue-checklist-complete-still-open/)
(task 558) proved the shape: a checklist promise nothing ever compares
against the thing that made it. That recipe watches an ISSUE whose own
checklist names OTHER issues by number (`- [ ] #N`). This one watches a
pull request's own checklist instead — a different, and in real use far
more common, grammar: a self-contained list of plain-text tasks an author
writes for themself or a reviewer ("- [ ] Add tests", "- [ ] Update docs"),
naming no other GitHub object at all.

**The seam it watches:** GitHub renders every box on a PR's own checklist
and tallies a live "N of M tasks done" progress count on the PR's own page
— and does precisely nothing with the moment the count reaches M of M.
Merging is always a separate, human, forgettable step, the identical "no
trigger ever existed to fire" shape [`overdue-milestone-still-open`](../overdue-milestone-still-open/)
and [`stale-branch-no-pr`](../stale-branch-no-pr/) already proved for
their own single-object seams. This recipe watches that specific silence:
a checklist an author declared complete, on a PR that is not.

One fixture, no live account —
[`../../fixtures/pr_checklist_complete_still_open/pull_requests.json`](../../fixtures/pr_checklist_complete_still_open/pull_requests.json)
— shaped like what `ListPullRequests` (with bodies) would actually return.
The one scope already sits on `SCOPES.md`'s cleared oath table — no new
scope is asked for anywhere in this recipe.

Deliberately its own checkbox grammar, not `seam_engine.checklist`'s
shared `CHECKLIST_RE` — that module's own docstring is explicit about the
shape it covers (a checkbox that names another GitHub object by number)
and just as explicit that a bare checkbox with no `#N` after it is a
different recipe's seam, not its grammar's. Reusing it here would silently
match zero items on every real PR checklist in the wild (none of them read
`- [ ] #N`), not extend coverage — so this recipe's own `_TASK_ITEM_RE`
stays a separate, named grammar rather than a false extension of a
grammar built for a different question.

Confidence is age-gated on how long the PR's own `updated_at` has sat
still while every box reads checked — 24 hours, mirroring
`issue-checklist-complete-still-open`'s own bar exactly, since a pull
request carries no real "went-complete-at" timestamp either; `updated_at`
is the closest real signal the object exposes. Under 24h scores 0.5 (below
the 0.70 confidence bar, weighed in the tail not hidden — the author may
simply not have merged yet). At or past 24h scores a flat 0.85 — a
checkbox's own checked/unchecked mark is an unambiguous, non-fuzzy
structural read, not a guess. A PR with at least one unchecked box is
excluded at confidence 0.0, not complete yet, named not hidden. A PR that
is already merged or closed is excluded at confidence 0.0 too — the door
already resolved, whatever its checklist says. A PR with no real
task-list checkbox anywhere in its body is skipped entirely, not even
excluded — it never made a completeness promise, so there is nothing to
have missed.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/pr-checklist-complete-still-open/detector.py
```

The shipped fixture (PR #201, four checklist items, all checked, last
updated well over 24h before the scan) elects the primary gap for real:

```json
{
  "slug": "pr-checklist-complete-still-open-201",
  "headline": "PR #201's own checklist is all checked off, but the PR itself never merged",
  "confidence": 0.85
}
```
