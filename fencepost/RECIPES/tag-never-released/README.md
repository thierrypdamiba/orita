# tag-never-released

The seventy-eighth real recipe (ROADMAP.md #653). A git tag was pushed to
the repository, but no GitHub Release was ever published for it.

**The seam it watches:** `git push origin v1.1.0` creates a ref, full
stop — it fires no webhook a Release listener would catch, appears
nowhere on the Releases page, and GitHub's own UI never once suggests
turning it into one. Pushing a tag and publishing a release are two
structurally independent GitHub actions; a repo can accumulate any
number of tags that never become releases, silently, forever. `ListTags`
alone shows what was pushed; `ListReleases` alone shows what was
published — only holding both at once, matched by exact `name`/`tag_name`,
shows the gap between them.

This is the first recipe in the tree to read a git tag as its own object
at all — grepped every prior recipe's docstring, README, and fixture for
`ListTags`/`GetTag`/"tag": zero hits outside ordinary release `tag_name`
fields already used for matching, never for a tag's own existence.
Genuinely distinct from the closest sibling,
[`../example-release-vs-changelog/`](../example-release-vs-changelog/)
(the reference recipe CONTRIBUTING.md points new contributors at): that
recipe starts from a Release that already exists and asks whether
CHANGELOG.md caught up to it — one level downstream of this one. This
recipe starts one level further upstream, at the raw tag, and asks
whether a Release was ever created for it in the first place; a tag that
never becomes a release also, definitionally, never gets a chance to
reach `example-release-vs-changelog`'s own seam. It is also distinct from
the `*-never-released` family (`merged-pr-never-released`,
`milestone-closed-never-released`, `issue-closed-never-released`): those
three read a Release's own BODY TEXT for a later claim phrase ("ships
#N", "milestone #N") about a *different* object; this recipe never reads
release body text at all — it is a structural, no-prose-marker existence
check, matching a tag's own `name` against a release's own `tag_name`
field, the same "no keyword fuzziness to misfire on" shape
`example-release-vs-changelog` already established for its own exact-tag
match.

Two fixtures, no live account —
[`../../fixtures/tag_never_released/tags.json`](../../fixtures/tag_never_released/tags.json)
and
[`../../fixtures/tag_never_released/releases.json`](../../fixtures/tag_never_released/releases.json)
— shaped like what `ListTags`/`ListReleases` would actually return.
Neither scope sat on `SCOPES.md`'s cleared oath table before this
recipe; both are added in the same commit, with a WIP note explaining
why (both clear the allow-list's `Get*`/`List*` prefix check and name no
forbidden write verb — the identical naming-check every scope in this
engine clears — and neither is exposed live on the-hand gateway today,
confirmed the same way the Slack/Linear notes above it already were).

Confidence is age-gated on how long the tag has sat unreleased, mirroring
[`../duplicate-milestone-still-open/`](../duplicate-milestone-still-open/)'s
own 24-hour bar rather than inventing a new number for a structurally
similar "no prose marker" seam: under 24 hours since the tag was pushed
scores 0.5, below the bar, weighed in the tail not hidden (a human may be
mid-release, about to publish within the day); at or past 24 hours it
scores a flat 0.85 — an unambiguous, non-fuzzy signal, exact `tag_name`
match found nowhere in the release list. A tag with a matching release is
excluded, named not hidden, at confidence 0.0 — the identical discipline
every recipe before this one holds.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/tag-never-released/detector.py
```

Run bare like this it uses the real wall clock, so the fixture tags' own
ages will drift as real time passes — expected for a manual demo, not a
bug; the test suite always pins `now` explicitly so the result stays
deterministic in CI.

Against the pinned test clock it finds one real gap in its own fixture as
the elected primary (`v1.1.0`, pushed 2026-07-01, confidence 0.85 — over
a month unreleased with no matching release), one more weighed in the
tail (`v1.2.0-rc1`, pushed hours before the pinned clock — still inside
the grace window), while correctly excluding `v0.9.0` and `v1.0.0` (each
has a real matching release by exact `tag_name`).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/tag-never-released/recipe.json
```
