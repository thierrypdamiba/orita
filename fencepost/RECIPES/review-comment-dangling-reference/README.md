# review-comment-dangling-reference

The forty-fourth real recipe, and a seventh leg of the dangling-reference
family alongside [`../dangling-issue-reference/`](../dangling-issue-reference/)
(the fourth real recipe, commit messages),
[`../mention-dangling-reference/`](../mention-dangling-reference/) (the
eighteenth, X mentions),
[`../release-note-dangling-reference/`](../release-note-dangling-reference/)
(the twenty-third, release notes),
[`../issue-body-dangling-reference/`](../issue-body-dangling-reference/) (the
thirty-fourth, issue and PR bodies),
[`../milestone-body-dangling-reference/`](../milestone-body-dangling-reference/)
(the forty-first, milestone descriptions), and
[`../own-tweet-dangling-reference/`](../own-tweet-dangling-reference/) (the
forty-second, the town's own tweets). The fifth of those called itself "the
fifth and final leg"; the sixth called itself "the sixth and final leg" one
hour later. This one does not repeat the word — GitHub has more editable
text surfaces inviting the same mistake than any single docstring has yet
correctly counted. None of the six ever read a pull request's own **review
comments** — the inline, per-line code-review thread, a genuinely different
GitHub object from the PR body `issue-body-dangling-reference` already
covers.

**The seam it watches:** the same blind spot every sibling recipe already
proved, now on a text surface none of them had ever read. A reviewer writes
"same root cause as #501" or "isn't this the same bug as #N" directly into
an inline review thread constantly, and GitHub renders every `#N` there as a
clickable link with no check that it resolves to anything at all. A `#N`
inside a review comment's own body is checked against BOTH the issue list
and the PR list — GitHub shares one number sequence between them, so
checking only one would misfire on a perfectly good reference to a merged
PR sitting inside a review thread, exactly the crying-wolf failure Ogun's
law calls fatal.

Three fixture lists, no live account —
[`../../fixtures/review_comment_dangling_reference/review_comments.json`](../../fixtures/review_comment_dangling_reference/review_comments.json),
[`.../issues.json`](../../fixtures/review_comment_dangling_reference/issues.json),
and
[`.../pulls.json`](../../fixtures/review_comment_dangling_reference/pulls.json)
— shaped like what `ListReviewCommentsInARepository`, `ListIssues`, and
`ListPullRequests` would actually return. `ListIssues` and
`ListPullRequests` already sat on `SCOPES.md`'s cleared oath table;
`ListReviewCommentsInARepository` is a real, currently-live, read-only tool
on the-hand gateway, added to that table by this same task.

A cross-repo reference (`owner/repo#N`) is never even extracted as a
candidate — that names a different repo's own number space on purpose. A
review comment with no body at all never becomes a candidate either — it
never claims anything about a second record, so there is no seam to weigh.
This recipe imports `seam_engine.references.referenced_numbers` rather than
writing a seventh copy of the same extraction regex — the same "one law,
not a seventh copy of it" discipline this whole family already pays for.

**Confidence mirrors `issue-body-dangling-reference` and
`milestone-body-dangling-reference` exactly, for the same reason.** A
review comment, like an issue/PR body or a milestone description, is a text
surface its own author can still edit at any time, and a typo'd `#N` gets
corrected in the ordinary course of review constantly, so this recipe
age-gates against the comment's own `updated_at`: a dangling reference
touched less than 24 hours ago scores 0.55 (may still get fixed), one that
has sat untouched for at least 24 hours scores 0.85 (nobody is coming back
for it). See `recipe.json`'s `confidence_notes` for the full reasoning.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src:../RECIPES/review-comment-dangling-reference uv run python ../RECIPES/review-comment-dangling-reference/detector.py
```

Against its own fixture it elects exactly one primary gap (review comment
#9002's stale reference to "#9999", 24+ hours since its own last update,
confidence 0.85) and weighs one coincidence in the tail (review comment
#9003's fresh reference to "#8888", 2 hours since its own last update,
confidence 0.55). It correctly excludes comment #9001's reference to the
real issue #501, comment #9006's reference to the real PR #510, a
cross-repo reference (`arcadeai/gasstation#42` in comment #9005), a review
comment with no body at all (#9004), and a comment whose body carries no
`#N` reference (#9007).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/review-comment-dangling-reference/recipe.json
```
