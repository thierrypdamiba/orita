# issue-checklist-complete-still-open

The forty-sixth real recipe (ROADMAP.md #558, closing the town's own
[issue #7](https://github.com/thierrypdamiba/orita/issues/7): "Good first
issue: write a seam recipe nobody's built yet"). The missing third quadrant
next to [`../milestone-complete-still-open/`](../milestone-complete-still-open/)
(task 493: a milestone whose own issues all closed, but the milestone never
did) and [`../issue-closed-subissue-still-open/`](../issue-closed-subissue-still-open/)
(task 530: a CLOSED parent whose own checklist target is still open).

**The seam it watches:** an issue reads `state=open`, and its own body
carries one or more real GitHub task-list checkboxes (`- [ ] #N` / `- [x] #N`)
naming other issues — every one of them now closed — but the parent issue
itself never closed. GitHub tracks each checklist target's own live state for
free; it never once compares that against the parent that made the
checklist promise. Closing the parent is always a separate, manual,
forgettable step — the identical "no trigger ever existed to fire" shape
`milestone-complete-still-open` already named for milestone membership, one
layer down. One fixture, no live account —
[`../../fixtures/issue_checklist_complete_still_open/issues.json`](../../fixtures/issue_checklist_complete_still_open/issues.json)
— shaped like what `ListIssues` (with bodies) would actually return. The one
scope already sits on `SCOPES.md`'s cleared oath table. No new scope is asked
for anywhere in this recipe.

Deliberately keyed on GitHub's own task-list checkbox syntax, not a bare
`#N` mention anywhere in the body — a bare mention with no checkbox in front
of it is [`issue-body-dangling-reference`](../issue-body-dangling-reference/)'s
own seam (does the number even resolve), not this one's (does the parent's
own declared checklist actually finish). The checkbox's own checked/unchecked
mark is read only to find the reference at all — whether a target counts as
done is decided by the target issue's own live `state`, never by which box a
human ticked, the same "trust the record, not the label" discipline every
sibling in this family already holds. A checklist target that doesn't exist
at all makes the parent's own completeness claim unverifiable — the whole
parent is excluded here, named not hidden, rather than guessed at (Ògún's
law). A parent with at least one still-open checklist target is excluded
too — not complete yet, nothing missed.

Confidence is age-gated on how long the parent's own `updated_at` has sat
still while every checklist target reads closed — 24 hours, mirroring
`milestone-complete-still-open`'s own bar exactly, since neither a milestone
nor an issue carries a real "went-complete-at" timestamp. See `recipe.json`'s
`confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/issue-checklist-complete-still-open/detector.py
```

It finds one primary gap in its own fixture (#1001's checklist — #1010 and
#1011, both closed — confidence 0.85, parent last touched ~69h ago) and two
lower-confidence tail candidates (#1002, confidence 0.5, touched ~3h ago;
#1007, confidence 0.5, whose checklist names #1010 twice — deduplicated to a
single evidence entry, not two), while correctly excluding #1003 (still
names one open target, #1013 — not complete) and #1004 (names #9999, which
does not exist — unverifiable, withheld). #1005's identical-looking checklist
is never considered at all (the parent itself is already closed), and
#1006's bare "See #1010 for context" mention is never extracted at all (no
checkbox precedes it).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/issue-checklist-complete-still-open/recipe.json
```
