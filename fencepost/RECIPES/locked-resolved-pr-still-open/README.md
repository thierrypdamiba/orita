# locked-resolved-pr-still-open

The ninety-first real recipe (ROADMAP.md #876). The PR-side twin of
[`../locked-resolved-issue-still-open/`](../locked-resolved-issue-still-open/)
(task 596, the sixty-fourth real recipe): the identical field pair,
`locked` and its own `active_lock_reason`, checked against `state`, this
time on a pull request's own record instead of an issue's — because a
pull request IS an issue under GitHub's own REST numbering and locking
machinery, and GitHub's Lock API (`PUT .../lock`) works identically on
both.

**The seam it watches:** a pull request is locked with `active_lock_reason`
reading `"resolved"` — GitHub's own record of a maintainer's explicit
claim that the matter is settled — but the PR's own `state` still reads
`"open"`. Locking a PR's conversation and actually merging or closing the
PR it belongs to are two independent GitHub actions: a maintainer, or a
bot, can lock with reason `resolved` while the PR itself sits open the
whole time, exactly the same way `locked-resolved-issue-still-open`
already established for issues. Nothing on GitHub's side ever compares
the two fields to each other — no auto-close, no auto-merge, wired to a
lock reason, the same "no forcing function, only a human notices" shape
the rest of the `*-still-open` family already established for other
field pairs. `ListPullRequests`/`GetPullRequest` alone already carries
both halves of the promise; no second toolkit, no cross-account join, is
needed to see it — the record simply never gets checked against itself.

This is not [`unblocked-pr-still-open`](../unblocked-pr-still-open/)'s
seam — no prose "blocked by #N" marker is parsed here at all, the same
distinction `locked-resolved-issue-still-open`'s own README already drew
against the claims-X and dangling-reference grids. It shares only the
general shape of
[`commit-closes-keyword-issue-closed-not-planned`](../commit-closes-keyword-issue-closed-not-planned/)
— a single record's own two fields disagreeing with each other, read off
one list, no second source needed — but watches `locked`/
`active_lock_reason` against `state`, the exact pair `locked-resolved-
issue-still-open` already reads, carried onto the PR object it also
happens to sit on.

The claim stays narrow on purpose, the same no-grading law every sibling
holds: this recipe never claims anyone forgot or dropped the ball — a
maintainer may have locked the PR's thread the moment they posted the
resolution, fully intending to merge or close it next, and simply
navigated away. It claims only that two fields on the same record
disagree.

Only `active_lock_reason == "resolved"` is treated as a claim about the
PR's own resolution at all. `"off-topic"`, `"spam"`, and `"too heated"`
are excluded outright — none of them says anything about whether the
underlying PR is done. A locked PR with no lock reason recorded at all
(`active_lock_reason` is `null`, a real, valid GitHub state) is excluded
too — no explicit "resolved" claim was ever made. A PR that isn't locked
at all is excluded — nothing to compare. A PR that already reads anything
other than `"open"` is excluded — unlike an issue, a real GitHub pull
request's own `state` is not two-valued:
[`unblocked-pr-still-open`](../unblocked-pr-still-open/) and
[`duplicate-pr-still-open`](../duplicate-pr-still-open/) (this library's
current PR-fixture convention) both already read a merged PR's `state` as
`"merged"` and a closed-without-merging PR's `state` as `"closed"`, two
distinct terminal values rather than a single `"closed"` plus a separate
boolean — whichever of the two a given PR reached, and whichever order
locking and reaching it happened in, the two fields already agree. A
record with `locked == false` but a non-null `active_lock_reason` is
excluded as malformed — GitHub's own API never produces that combination
for real.

One fixture, no live account —
[`../../fixtures/locked_resolved_pr_still_open/pulls.json`](../../fixtures/locked_resolved_pr_still_open/pulls.json)
— shaped like what `ListPullRequests`/`GetPullRequest` would actually
return. Both scopes already sit on `SCOPES.md`'s cleared oath table under
the `github` row — no new scope is asked for anywhere in this recipe.

Confidence is age-gated on how long `updated_at` has sat still while the
contradiction holds. There is no `locked_at` field on a real GitHub pull
request object either, so `updated_at` (the closest real signal GitHub
exposes) stands in, the same way
[`locked-resolved-issue-still-open`](../locked-resolved-issue-still-open/)
already uses it in place of a missing `locked_at`. Under 24 hours scores
0.5, weighed in the tail — the same person who just locked it may simply
not have merged or closed it yet. At or past 24 hours it scores a flat
0.85. See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/locked-resolved-pr-still-open/detector.py
```

Run bare like this it uses the real wall clock, so the fixture PRs' own
ages (and therefore which ones clear 24 hours) will drift as real time
passes — expected for a manual demo, not a bug, the same documented
property every age-gated MOCK-only fixture in this repo already carries.
The test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against the pinned test clock (`2026-08-15T12:00:00Z`) it finds one real
gap in its own fixture as the elected primary (PR #1301, locked as
resolved 175 hours before the pinned clock while still reading open,
confidence 0.85), one more weighed in the tail (PR #1302, locked as
resolved only 6 hours before the pinned clock), and correctly excludes:
PR #1303 (locked as resolved, but already merged), PR #1304 (locked as
resolved, but already closed without merging — the two fields agree
either way), PRs #1305/#1306/#1307 (locked for `off-topic`/`spam`/`too
heated` — none of those reasons claims a resolution), PR #1308 (locked
with no reason recorded at all), PR #1309 (not locked), PR #1310 (a
malformed record: `locked=false` with a non-null `active_lock_reason`),
and PR #1311 (not locked, and closed).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/locked-resolved-pr-still-open/recipe.json
```
