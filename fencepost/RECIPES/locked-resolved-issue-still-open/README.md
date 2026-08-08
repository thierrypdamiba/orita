# locked-resolved-issue-still-open

The sixty-fourth real recipe (ROADMAP.md #596). It reads a field pair none of the sixty-three
prior recipes has ever read: an issue's own `locked` and `active_lock_reason`
fields — GitHub's real, structured record of whether a conversation was
locked, and why.

**The seam it watches:** an issue is locked with `active_lock_reason` reading
`"resolved"` — GitHub's own record of a maintainer's explicit claim that the
matter is settled — but the issue's own `state` still reads `"open"`.
Locking a conversation and closing the issue it belongs to are two
independent GitHub actions: the UI offers a combined "Close as resolved and
lock conversation" button that fires both, but its API exposes each on its
own too, and a maintainer, or a bot, can lock with reason `resolved` while
the issue itself sits open the whole time. Nothing on GitHub's side ever
compares the two fields to each other — no auto-close wired to a lock
reason, the same "no forcing function, only a human notices" shape the rest
of the `*-still-open` family already established for other field pairs.
`ListIssues` alone already carries both halves of the promise; no second
toolkit, no cross-account join, is needed to see it — the record simply
never gets checked against itself.

This is a genuinely different axis from every family this repo has already
saturated. It is not the claims-X grid — no claim phrase, no body text
parsed at all, two structured fields compared against each other, entirely
within one record. It is not the dangling-reference grid — no `#N`
reference read anywhere. It is not a checklist recipe — no task-list syntax
parsed here. It shares only the general *shape* of
[`commit-closes-keyword-issue-closed-not-planned`](../commit-closes-keyword-issue-closed-not-planned/)
— a single record's own two fields disagreeing with each other, read off
one list, no second source needed — but watches `locked`/`active_lock_reason`
against `state`, a pair that recipe never reads, rather than `state_reason`
against a commit's own closing-keyword claim.

The claim stays narrow on purpose, the same no-grading law every sibling
holds: this recipe never claims anyone forgot or dropped the ball — a
maintainer may have locked the thread the moment they posted the
resolution, fully intending to close it next, and simply navigated away.
It claims only that two fields on the same record disagree.

Only `active_lock_reason == "resolved"` is treated as a claim about the
issue's own resolution at all. `"off-topic"`, `"spam"`, and `"too heated"`
are excluded outright — none of them says anything about whether the
underlying issue is done. A locked issue with no lock reason recorded at
all (`active_lock_reason` is `null`, a real, valid GitHub state) is
excluded too — no explicit "resolved" claim was ever made. An issue that
isn't locked at all is excluded — nothing to compare. A closed issue is
excluded — whichever order locking and closing happened in, the two
fields already agree. A record with `locked == false` but a non-null
`active_lock_reason` is excluded as malformed — GitHub's own API never
produces that combination for real.

One fixture, no live account —
[`../../fixtures/locked_resolved_issue_still_open/issues.json`](../../fixtures/locked_resolved_issue_still_open/issues.json)
— shaped like what `ListIssues` would actually return. `ListIssues` already
sits on `SCOPES.md`'s cleared oath table under the `github` row — no new
scope is asked for anywhere in this recipe.

Confidence is age-gated on how long `updated_at` has sat still while the
contradiction holds. There is no `locked_at` field on a real GitHub issue
object, so `updated_at` (the closest real signal GitHub exposes) stands in,
the same way
[`milestone-complete-still-open`](../milestone-complete-still-open/)
already uses it in place of a missing `completed_at`. Under 24 hours scores
0.5, weighed in the tail — the same person who just locked it may simply
not have closed it yet. At or past 24 hours it scores a flat 0.85. See
`recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/locked-resolved-issue-still-open/detector.py
```

Run bare like this it uses the real wall clock, so the fixture issues' own
ages (and therefore which ones clear 24 hours) will drift as real time
passes — expected for a manual demo, not a bug, the same documented
property every age-gated MOCK-only fixture in this repo already carries.
The test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against the pinned test clock (`2026-08-08T12:00:00Z`) it finds one real
gap in its own fixture as the elected primary (issue #1201, locked as
resolved 171 hours before the pinned clock while still reading open,
confidence 0.85), one more weighed in the tail (issue #1202, locked as
resolved only 6 hours before the pinned clock), and correctly excludes:
issue #1203 (locked as resolved, but already closed — the two fields
agree), issues #1204/#1205/#1206 (locked for `off-topic`/`spam`/`too
heated` — none of those reasons claims a resolution), issue #1207 (locked
with no reason recorded at all), issue #1208 (not locked), issue #1209 (a
malformed record: `locked=false` with a non-null `active_lock_reason`),
and issue #1210 (not locked, and closed).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/locked-resolved-issue-still-open/recipe.json
```
