# milestone-body-dangling-reference

The forty-first real recipe, and the fifth and final leg of the
dangling-reference family alongside
[`../dangling-issue-reference/`](../dangling-issue-reference/) (the fourth
real recipe, commit messages),
[`../mention-dangling-reference/`](../mention-dangling-reference/) (the
eighteenth, X mentions),
[`../release-note-dangling-reference/`](../release-note-dangling-reference/)
(the twenty-third, release notes), and
[`../issue-body-dangling-reference/`](../issue-body-dangling-reference/)
(the thirty-fourth, issue and PR bodies). All four ask the same question
of a different text surface — does this `#N` actually exist? — but none
of them ever looked at the one other place GitHub itself invites exactly
this same mistake: a milestone's own `description` field. "Tracks #501,
#502", "blocked on #N until that lands" are written directly into
milestone descriptions constantly, and GitHub renders every one of them
as a clickable link with no check that it resolves to anything at all.

**The seam it watches:** the same blind spot every sibling recipe already
proved, now on a text surface none of them had ever read. A `#N` inside a
milestone's own description is checked against BOTH the issue list and
the PR list — GitHub shares one number sequence between them, so checking
only one would misfire on a perfectly good reference to a merged PR
sitting inside a milestone's own notes, exactly the crying-wolf failure
Ogun's law calls fatal.

Three fixture lists, no live account —
[`../../fixtures/milestone_body_dangling_reference/milestones.json`](../../fixtures/milestone_body_dangling_reference/milestones.json),
[`.../issues.json`](../../fixtures/milestone_body_dangling_reference/issues.json),
and
[`.../pulls.json`](../../fixtures/milestone_body_dangling_reference/pulls.json)
— shaped like what `ListMilestones`, `ListIssues`, and `ListPullRequests`
would actually return. All three declared scopes already sit on
`SCOPES.md`'s cleared oath table. No new scope is asked for anywhere in
this recipe.

A cross-repo reference (`owner/repo#N`) is never even extracted as a
candidate — that names a different repo's own number space on purpose. A
milestone with no description at all (`null` or empty) never becomes a
candidate either — it never claims anything about a second record, so
there is no seam to weigh. This recipe imports
`seam_engine.references.referenced_numbers` rather than writing a fifth
copy of the same extraction regex — the same "one law, not a fifth copy
of it" discipline this whole family already pays for.

**Confidence mirrors `issue-body-dangling-reference` exactly, for the
same reason.** `dangling-issue-reference`, `mention-dangling-reference`,
and `release-note-dangling-reference` each score flat, because a commit
message, a stranger's tweet, and a published release note are all
permanent the instant they exist. A milestone's description, like an
issue or PR body, is the one kind of text surface in this family an
author can still edit at any time, and a typo'd `#N` gets corrected in
the ordinary course of triage constantly, so this recipe age-gates
against the milestone's own `updated_at`: a dangling reference touched
less than 24 hours ago scores 0.55 (may still get fixed), one that has
sat untouched for at least 24 hours scores 0.85 (nobody is coming back
for it). See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src:../RECIPES/milestone-body-dangling-reference uv run python ../RECIPES/milestone-body-dangling-reference/detector.py
```

Against its own fixture it elects exactly one primary gap (milestone
#21's stale reference to "#9999", 24+ hours since its own last update,
confidence 0.85) and weighs one coincidence in the tail (milestone #22's
fresh reference to "#8888", 2 hours since its own last update, confidence
0.55). It correctly excludes milestone #20's reference to the real issue
#501, milestone #25's reference to the real PR #510, a cross-repo
reference (`arcadeai/gasstation#42` in milestone #24), a milestone with
no description at all (#23), and a milestone whose description carries
no `#N` reference (#26).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/milestone-body-dangling-reference/recipe.json
```
