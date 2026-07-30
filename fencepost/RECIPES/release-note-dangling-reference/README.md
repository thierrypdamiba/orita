# release-note-dangling-reference

The twenty-third real recipe, and the third leg of the dangling-reference
family alongside [`../dangling-issue-reference/`](../dangling-issue-reference/)
(the fourth real recipe, commit messages) and
[`../mention-dangling-reference/`](../mention-dangling-reference/) (the
eighteenth, X mentions). Both siblings ask the same question of a
different text surface — does this `#N` actually exist? — but neither
ever looked at a release's own body. `release-claims-unmerged-pr`,
`release-claims-unfixed-issue`, and `release-claims-open-milestone` all
read a release's body too, but only ever check the numbers sitting inside
a ships/fixes/milestone *claim phrase*. A release note can also mention
`#N` in ordinary prose — background, credit, a passing remark — with no
claim phrase anywhere nearby, and none of those three recipes ever look
there.

**The seam it watches:** GitHub renders `#N` inside a release body as a
clickable link without ever checking it resolves to anything — the same
seam both sibling recipes already proved, now on the one text surface this
engine reads for other reasons but has never checked for THIS. A release
note is exactly as permanent and unproofread as a commit message once
published: a typo, a reference to something deleted, or a number meant for
a different repo sits there in public, forever, the same "nobody reads it
looking for a broken link" blind spot.

Three fixture lists, no live account —
[`../../fixtures/release_note_dangling_reference/releases.json`](../../fixtures/release_note_dangling_reference/releases.json),
[`.../issues.json`](../../fixtures/release_note_dangling_reference/issues.json),
and [`.../pulls.json`](../../fixtures/release_note_dangling_reference/pulls.json)
— shaped like what `GetLatestRelease` (read repeatedly over time, the same
"recent-releases history" convention `release-claims-unmerged-pr/recipe.json`
already established), `ListIssues`, and `ListPullRequests` would actually
return. All three declared scopes already sit on `SCOPES.md`'s cleared
oath table. No new scope is asked for anywhere in this recipe.

A `#N` reference is checked against BOTH the issue list and the PR list —
GitHub shares one number sequence between them, so checking only one would
misfire on a perfectly good reference to a merged PR, exactly the
crying-wolf failure Ogun's law calls fatal. A cross-repo reference
(`owner/repo#N`) is never even extracted as a candidate — that names a
different repo's own number space on purpose, a seam for a recipe watching
*that* repo, not a gap in this one. A release with no `#N` reference at
all never becomes a candidate either — it never claims anything about a
second record, so there is no seam to weigh. This recipe imports
`seam_engine.references.referenced_numbers` rather than writing a third
copy of the same extraction regex — the same "one law, not a third copy of
it" discipline tasks 389/390/393/394/396/400 already paid for on five
other shared patterns in this engine. See `recipe.json`'s
`confidence_notes` for the full reasoning behind the flat 0.8 score,
matching `dangling-issue-reference`'s own bar exactly.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src:../RECIPES/release-note-dangling-reference uv run python ../RECIPES/release-note-dangling-reference/detector.py
```

It finds one real gap in its own fixture (release v2.1.0's reference to
"#2099," which does not exist, confidence 0.8) and correctly excludes a
reference that resolves to a real issue (#2001), a reference that resolves
to a real merged PR (#2002), a cross-repo reference
(`arcadeai/gasstation#42`), and a release with no reference at all.

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/release-note-dangling-reference/recipe.json
```
