# issue-body-dangling-reference

The twenty-fourth real recipe, and the fourth and final leg of the
dangling-reference family alongside
[`../dangling-issue-reference/`](../dangling-issue-reference/) (the fourth
real recipe, commit messages),
[`../mention-dangling-reference/`](../mention-dangling-reference/) (the
eighteenth, X mentions), and
[`../release-note-dangling-reference/`](../release-note-dangling-reference/)
(the twenty-third, release notes). All three ask the same question of a
different text surface — does this `#N` actually exist? — but none of
them ever looked at the single most common place a stray `#N` actually
gets typed in this town's own history: an issue or pull request's own
description. "Related to #N", "see #N for context", "same root cause as
#N" are written directly into issue and PR bodies constantly, and GitHub
renders every one of them as a clickable link with no check that it
resolves to anything at all.

**The seam it watches:** the same blind spot every sibling recipe already
proved, now on the text surface this engine reads the most and had never
checked for THIS. A `#N` inside an issue or PR body is checked against
BOTH the issue list and the PR list — GitHub shares one number sequence
between them, so checking only one would misfire on a perfectly good
reference to a merged PR sitting inside an issue, or to a closed issue
sitting inside a PR, exactly the crying-wolf failure Ogun's law calls
fatal.

Two fixture lists, no live account —
[`../../fixtures/issue_body_dangling_reference/issues.json`](../../fixtures/issue_body_dangling_reference/issues.json)
and
[`.../pulls.json`](../../fixtures/issue_body_dangling_reference/pulls.json)
— shaped like what `ListIssues` and `ListPullRequests` would actually
return, each row now carrying its own `body` and `updated_at` (the two
fields this recipe needs that no earlier recipe's fixture for these same
two scopes ever had to carry). Both declared scopes already sit on
`SCOPES.md`'s cleared oath table. No new scope is asked for anywhere in
this recipe.

A cross-repo reference (`owner/repo#N`) is never even extracted as a
candidate — that names a different repo's own number space on purpose. A
record with no `#N` reference at all never becomes a candidate either —
it never claims anything about a second record, so there is no seam to
weigh. This recipe imports `seam_engine.references.referenced_numbers`
rather than writing a fourth copy of the same extraction regex — the same
"one law, not a fourth copy of it" discipline tasks
389/390/393/394/396/400 already paid for on five other shared patterns in
this engine.

**Confidence is where this recipe reasons differently than its three
siblings, on purpose.** `dangling-issue-reference`,
`mention-dangling-reference`, and `release-note-dangling-reference` each
score flat, because a commit message, a stranger's tweet, and a published
release note are all permanent the instant they exist — there is no
"give it a chance to get fixed" grace period that means anything for any
of them. An issue or PR body is the one text surface in this family an
author can still edit at any time, and a typo'd `#N` gets corrected in
the ordinary course of triage constantly, so this recipe age-gates
against the record's own `updated_at`: a dangling reference in a body
touched less than 24 hours ago scores 0.55 (may still get fixed), one
that has sat untouched for at least 24 hours scores 0.85 (nobody is
coming back for it). See `recipe.json`'s `confidence_notes` for the full
reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src:../RECIPES/issue-body-dangling-reference uv run python ../RECIPES/issue-body-dangling-reference/detector.py
```

Against its own fixture (pinned clock 2026-07-30T12:00:00Z) it elects
exactly one primary gap (issue #502's stale reference to "#9999," 72
hours since its own last update, confidence 0.85) and weighs one
coincidence in the tail (issue #503's reference to "#8888," only 2 hours
since its own last update, confidence 0.55). It correctly excludes issue
#501's reference to the real PR #504, PR #504's own references back to
the real issues #501 and #502, a cross-repo reference
(`arcadeai/gasstation#42`), and two bodies with no reference at all.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/issue-body-dangling-reference/recipe.json
```
