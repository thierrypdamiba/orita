# issue-closed-subissue-still-open

The forty-third real recipe (ROADMAP.md #530). One level down from
[`../milestone-closed-issue-still-open/`](../milestone-closed-issue-still-open/)
(task 379): that recipe watches a milestone's own membership; this one
watches an issue's own self-declared GitHub task-list checklist.

**The seam it watches:** an issue reads `state=closed`, and its own body
carries a real GitHub task-list checkbox (`- [ ] #N` / `- [x] #N`) naming
another issue, but that named issue is still open. Closing the parent is a
pure state operation — it never touches a checklist target's own state, so
there is no auto-close wiring here at all, the identical "no trigger ever
existed to fire" shape `milestone-closed-issue-still-open` already named
for milestone membership. A human (or a god) closes the parent believing
every listed sub-task is done; a checklist item left open inside it is the
exact seam this recipe watches, and it exists only by holding the parent's
own closed state and the target's own live state at the same instant —
neither record alone shows it. One fixture, no live account —
[`../../fixtures/issue_closed_subissue_still_open/issues.json`](../../fixtures/issue_closed_subissue_still_open/issues.json)
— shaped like what `ListIssues` (with bodies) would actually return. The
one scope already sits on `SCOPES.md`'s cleared oath table. No new scope is
asked for anywhere in this recipe.

Deliberately keyed on GitHub's own task-list checkbox syntax, not a bare
`#N` mention anywhere in the body — a bare mention with no checkbox in
front of it is
[`issue-body-dangling-reference`](../issue-body-dangling-reference/)'s own
seam (does the number even resolve), not this one's (does the parent's own
declared sub-task still sit open). The checkbox's own checked/unchecked
mark is read only to find the reference at all — whether a target counts
as a real gap is decided by the target issue's own live `state`, never by
which box a human ticked. A checklist target that doesn't exist at all is
excluded here, named not hidden — that broken reference belongs to
`issue-body-dangling-reference`'s own seam, not this one's. A checklist
target that IS closed is excluded too — the claim was simply true,
whatever its own checkbox reads.

Confidence is age-gated on how long the parent has been closed while the
target still sits open — 24 hours, mirroring
`milestone-closed-issue-still-open`, `merged-pr-issue-still-open`, and
`duplicate-issue-still-open`'s own bar exactly: a parent closed under 24h
ago may not have had its own checklist swept yet. See `recipe.json`'s
`confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/issue-closed-subissue-still-open/detector.py
```

It finds one primary gap in its own fixture (#901's checklist item #904,
confidence 0.85 — closed 51.2h ago, still open) and one lower-confidence
tail candidate (#902's checklist item #905, confidence 0.5 — closed only
4.2h ago), while correctly excluding #901's other two checklist items
(#906, already closed — claim holds; #999, doesn't exist — dangling, not
this seam) and #909 (closed with no timestamp — malformed, not a seam). A
duplicate checklist reference to #904 inside #901's own body is
de-duplicated to a single surfaced candidate, not two. #903's bare "See
#904 for related context" mention is never extracted at all (no checkbox
precedes it) and #907's identical checklist is never considered at all
(the parent itself is still open).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/issue-closed-subissue-still-open/recipe.json
```
