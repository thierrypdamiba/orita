# manifest-version-never-tagged

The hundred-eleventh real recipe (ROADMAP.md #1607). The project's own
version manifest (`pyproject.toml`, `package.json`, `Cargo.toml`, or any
sibling file carrying a `version` field) was bumped, but no git tag was
ever pushed for it.

**The seam it watches:** `git push origin main` moves a version manifest
forward the moment someone edits it, full stop — nothing about that push
creates a tag, fires a tag-shaped webhook, or nudges anyone to run
`git tag`. `GetFileContents` alone shows what a manifest currently
declares; `ListTags` alone shows what was pushed — only holding both at
once, matched by normalized exact version string, shows the gap between
them: a version that shipped in code and never became a release at all.

Distinct from the closest sibling,
[`../tag-never-released/`](../tag-never-released/): that recipe starts
from a tag that already, unambiguously, exists and asks whether a GitHub
Release object was ever published for it — one level downstream of this
one. This recipe starts one level further upstream, at the raw version
string a human (or a bot) already typed into a committed file, and asks
whether a tag was ever pushed for it in the first place; a version that
never becomes a tag also, definitionally, never gets a chance to reach
`tag-never-released`'s own seam.

Matching is by normalized exact version string, not keyword overlap — the
same "no fuzziness to misfire on" discipline
[`../example-release-vs-changelog/`](../example-release-vs-changelog/)
and `tag-never-released` already hold for their own exact-match seams.
Git tags conventionally carry a leading `v` (`v1.4.0`); manifest `version`
fields conventionally do not (`1.4.0`) — `_normalize_version` strips an
optional leading `v`/`V` from both sides before comparing, in both
directions, so the two ordinary spelling conventions never register as a
false gap.

A version carrying its own pre-release/build-metadata suffix (`-rc.1`,
`-alpha`, `-beta`, `-dev`, `-SNAPSHOT`, `+build`, `-nightly`) is excluded
outright, named not hidden — the suffix is itself the author's own
explicit "not released yet" marker (semver's own vocabulary for exactly
this), so flagging it as a missing tag would be the precise crying-wolf
false positive Ògún's law forbids: the human already said, in the version
string itself, that this one isn't done.

Two fixtures, no live account —
[`../../fixtures/manifest_version_never_tagged/manifest_versions.json`](../../fixtures/manifest_version_never_tagged/manifest_versions.json)
and
[`../../fixtures/manifest_version_never_tagged/tags.json`](../../fixtures/manifest_version_never_tagged/tags.json)
— shaped like what `GetFileContents`/`ListTags` would actually return.
Neither scope is new: both already sit on `SCOPES.md`'s cleared oath
table under the `github` row. No new scope is asked for anywhere in this
recipe.

Confidence is flat 0.75 on a surfaced gap — lower than
`tag-never-released`'s own 0.85 on purpose: that recipe's seam starts
from a tag that already, unambiguously, exists; this one starts one
level further upstream, at a version string a human typed into a file,
which can honestly outrun its own tag by a short, ordinary window (a
manifest bumped as part of the same commit that will be tagged moments
later) with no dishonesty involved. The confidence is capped below
`tag-never-released`'s own bar to reflect that extra, real uncertainty,
never inflated to match it. A pre-release-suffixed version, or a version
with a normalized-exact tag match, is excluded at confidence 0.0 — the
identical discipline every recipe before this one holds.

Run it yourself:

```
cd fencepost/seam_engine
PYTHONPATH=src uv run python ../RECIPES/manifest-version-never-tagged/detector.py
```

It finds one real gap in its own fixture as the elected primary
(`pyproject.toml` at `1.4.0`, no matching tag, confidence 0.75), while
correctly excluding `package.json` at `2.0.0-rc.1` (its own suffix already
says "not released yet") and `Cargo.toml` at `1.3.0` (a real, matching
`v1.3.0` tag — the claim was simply true).

Check the manifest against the oath and the schema the same way CI will:

```
uv run python -m seam_engine.recipes check ../../RECIPES/manifest-version-never-tagged/recipe.json
```
