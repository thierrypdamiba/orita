# RECIPES

Community-submitted seam recipes — gap detectors that watch a new seam,
contributed by someone other than the nine gods. One directory per recipe,
`RECIPES/<slug>/`. The schema, the oath, and how to open a PR live in
[`../CONTRIBUTING.md`](../CONTRIBUTING.md); the validator that enforces the
oath in code, not just in prose, is
[`../seam_engine/src/seam_engine/recipes.py`](../seam_engine/src/seam_engine/recipes.py).

Start with [`example-release-vs-changelog/`](example-release-vs-changelog/)
— the reference recipe, and the one every new contribution's directory
should look like the shape of.

*A recipe that declares a write/send/delete/post scope does not reach a
human reviewer. It is refused on iron, by `recipes.validate_recipe`, before
that.*
