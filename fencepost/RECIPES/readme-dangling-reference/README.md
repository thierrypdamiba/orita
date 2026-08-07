# readme-dangling-reference

The fifty-seventh real recipe, and the ninth leg of the dangling-reference
family alongside [`../dangling-issue-reference/`](../dangling-issue-reference/)
(commit messages), [`../mention-dangling-reference/`](../mention-dangling-reference/)
(X mentions), [`../release-note-dangling-reference/`](../release-note-dangling-reference/)
(release notes), [`../issue-body-dangling-reference/`](../issue-body-dangling-reference/)
(issue/PR bodies), [`../milestone-body-dangling-reference/`](../milestone-body-dangling-reference/)
(milestone descriptions), [`../own-tweet-dangling-reference/`](../own-tweet-dangling-reference/)
(the town's own tweets), [`../review-comment-dangling-reference/`](../review-comment-dangling-reference/)
(inline review comments), and [`../issue-comment-dangling-reference/`](../issue-comment-dangling-reference/)
(timeline comments). Every one of those eight asks the same question of a
different text surface — does this `#N` actually exist? — but none of them
ever looked at README.md itself, even though README is the ONE surface the
claims-X family already checks from all three angles
([`../readme-claims-open-milestone/`](../readme-claims-open-milestone/),
[`../readme-claims-unfixed-issue/`](../readme-claims-unfixed-issue/),
[`../readme-claims-unmerged-pr/`](../readme-claims-unmerged-pr/)). All
three of those recipes only ever examine the numbers sitting inside a
milestone/fixes/ships *claim phrase* — a README can also mention `#N` in
ordinary prose (background, credit, a passing remark) with no claim phrase
anywhere nearby, and nothing before this recipe ever checked whether THAT
number actually exists. README is alone among the six claims-X sources
(readme, release, tweet, mention, milestone, review-comment) in having
zero dangling-reference coverage until now — every other source in that
grid already grew both a claims-X leg and a dangling-reference leg.

**The seam it watches:** GitHub renders `#N` inside README.md as a
clickable link without ever checking it resolves to anything — the same
seam every dangling-reference sibling already proved, now on the repo's
own front door, the one document a stranger reads first. A typo, a
reference to something deleted, or a number meant for a different repo
sits there in public, forever, the same "nobody reads it looking for a
broken link" blind spot every sibling recipe already found on its own
surface.

Three fixture files, no live account —
[`../../fixtures/readme_dangling_reference/readme.json`](../../fixtures/readme_dangling_reference/readme.json),
[`.../issues.json`](../../fixtures/readme_dangling_reference/issues.json),
and [`.../pulls.json`](../../fixtures/readme_dangling_reference/pulls.json)
— shaped like what `GetFileContents`, `ListIssues`, and `ListPullRequests`
would actually return. All three declared scopes already sit on
`SCOPES.md`'s cleared oath table. No new scope is asked for anywhere in
this recipe.

A `#N` reference is checked against BOTH the issue list and the PR list —
GitHub shares one number sequence between them, so checking only one would
misfire on a perfectly good reference to a merged PR, exactly the
crying-wolf failure Ogun's law calls fatal. A cross-repo reference
(`owner/repo#N`) is never even extracted as a candidate — that names a
different repo's own number space on purpose, a seam for a recipe watching
*that* repo, not a gap in this one. A README with no `#N` reference at all
never becomes a candidate either — it never claims anything about a
second record, so there is no seam to weigh. This recipe imports
`seam_engine.references.referenced_numbers` rather than writing a ninth
copy of the same extraction regex — the same "one law, not a ninth copy of
it" discipline this engine has already paid for eight times over on the
identical shared pattern.

Confidence is deliberately NOT age-gated, mirroring
`readme-claims-open-milestone`'s own reasoning exactly rather than the
dangling-reference family's more common flat 0.8: a `GetFileContents`
read of README.md returns current text, not a change history, so there is
no per-claim timestamp to weigh a staleness window against — and no race
either, since a README is read live, right now, so a reference it
currently makes and the issue/PR tracker's currently-known numbers are
both true at the same instant this scan runs. Flat 0.85, the higher
confidence belonging to the source surface, not to the shape of the check.
See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src:../RECIPES/readme-dangling-reference uv run python ../RECIPES/readme-dangling-reference/detector.py
```

It finds one real gap in its own fixture (README.md's reference to "#4001,"
which does not exist, confidence 0.85) and correctly excludes a reference
that resolves to a real open issue (#4), a real closed issue (#12), a real
merged PR (#40), and a cross-repo reference (`arcadeai/gasstation#42`).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/readme-dangling-reference/recipe.json
```
