# Contributing a seam recipe

*How a stranger gets a gap detector merged into this repo, and why the oath
does not need you to be trusted to keep it.*

Fencepost's engine ships two detectors today — `scan.py` (GitHub-vs-X) and
`gmail_calendar.py` (Gmail-vs-Calendar, fixture-only). Both were written by
gods. This document is for the third kind of detector: one a stranger writes,
about a seam the town never thought to watch. We call it a **recipe** — a
small, self-contained gap detector that lives outside the core engine, under
[`RECIPES/<slug>/`](RECIPES/), reviewed and merged the same way any PR is.

The read-only oath (`SCOPES.md`) does not get to depend on who wrote the
code. Ògún's law is "the scope is read-only or nothing runs" — not "the
scope is read-only or nothing runs, unless a human forgot to check." So this
document ships with its own validator,
[`seam_engine/src/seam_engine/recipes.py`](seam_engine/src/seam_engine/recipes.py),
that rejects a recipe declaring a write/send/delete/post scope on iron,
before a reviewer's eyes ever reach the detector's code. Read this file for
the shape; run the validator to prove your recipe holds it.

## What a recipe is

The seam-scan pattern, repeated: read two already-typed lists, compare them,
and return `(surfaced, excluded)` — a list of `GapCandidate`s that might be
the gap, and a list named, not hidden, of the ones that were weighed and
ruled out. `scan.compute_candidates` does this for GitHub-vs-X.
`gmail_calendar.compute_gaps` does it for Gmail-vs-Calendar. Your recipe does
it for whatever seam you noticed nobody was watching.

A recipe does **not** decide the final election — it produces candidates the
same shape `ranking.rank()` already knows how to score (`CONFIDENCE_BAR`,
`SEPARATION_MARGIN`, both in
[`ranking.py`](seam_engine/src/seam_engine/ranking.py)). This document's job
is getting a recipe *merged*, standing on its own, provably read-only and
provably real.

**The wiring itself exists** (ROADMAP.md #111,
[`combined_scan.py`](seam_engine/src/seam_engine/combined_scan.py)):
`run_combined_scan` runs `scan.py`'s own candidates and every discovered
recipe's, converts each recipe's own `primary_gap`/`tail` back into plain
candidates, and calls `ranking.rank()` once over the whole pool — a recipe's
candidate really can out-rank or lose to a god's, tested both directions in
`tests/test_combined_scan.py`. It's also reachable from the live MCP tool
surface itself now (ROADMAP.md #113): `combined_scan_preview` in
[`server.py`](seam_engine/src/seam_engine/server.py), registered read-only
next to `seam_scan`, not just `python -m seam_engine.combined_scan`. Neither
is **wired into `seam-scan.yml`'s live daily run** (the same boundary
`gmail_calendar.py` is still WIP on):
every recipe today reads a `fixture`, per the MOCK ONLY oath below, and a
fixture's data never changes day to day — folding it into the REAL public
report before a recipe holds a live Arcade scope would fabricate a gap that
isn't actually true of the town's live accounts today, not just risk one.
`combined_scan.py` goes live in `seam-scan.yml` the same day a recipe's own
`fixture`/`scopes` graduate to a live read.

## The directory shape

```
RECIPES/<slug>/
  recipe.json     # the manifest — required, see schema below
  detector.py     # the pure detector function — required
  README.md       # optional: how to run it, what it finds

fixtures/<slug>/  # required — MOCK ONLY data your detector reads
```

Copy [`RECIPES/example-release-vs-changelog/`](RECIPES/example-release-vs-changelog/)
— the reference recipe. It is a real, working detector (a GitHub release
with no matching `CHANGELOG.md` entry) built to exactly this shape, and it
is validated by the same test suite a stranger's PR would be.

## The manifest schema (`recipe.json`)

Every field below is required. `seam_engine.recipes.load_recipe_manifest`
refuses a manifest that is missing even one.

| field | type | meaning |
|--|--|--|
| `slug` | string | Lowercase, kebab-case, must equal the directory name (`RECIPES/<slug>/recipe.json`, always). |
| `title` | string | One line, human-readable. |
| `author` | string | Your name or handle. Credited, not graded — see "No grading, ever" below. |
| `description` | string | One or two sentences: what seam this recipe watches. |
| `toolkit` | string | The account family this recipe reads from (`github`, `x`, `gmail`, `google_calendar`, or a new name if you're proposing one — see "New toolkits" below). |
| `scopes` | list of strings | The exact Arcade tool names your detector needs. **Every one must clear the oath below, or the manifest is refused before your code is read.** |
| `fixture` | string | Path, relative to `fencepost/`, to the MOCK ONLY data your detector reads. Must start with `fixtures/`. |
| `detector_file` | string | The bare filename, inside your own `RECIPES/<slug>/`, holding your detector — e.g. `"detector.py"`. No path segments; a recipe cannot point outside its own directory. |
| `entrypoint` | string | The function name in `detector_file` to call. Its contract: zero required arguments, returns a `dict` shaped like `gmail_calendar.run_gmail_calendar_scan`'s output (`generated_at`, `source: "fixture"`, `confidence_bar`, `separation_margin`, `primary_gap`, `tail`, `excluded`). |
| `confidence_notes` | string | Plain language: how your confidence score is computed, and why it isn't inflated. Ogun's law — a reviewer has to be able to see the false-positive reasoning, not just trust a number. |

## The oath, enforced in code

`SCOPES.md` says it in prose: *"Only **read** and **list**... `Get*`,
`List*`, `Read*`, `Search*`, `Count*`, `WhoAmI` — and nothing else."* Every
name you put in `scopes` is checked against that line, twice, by
`seam_engine.recipes.validate_recipe`:

1. **Allow-list, by prefix.** A scope must match `Get*`, `List*`, `Read*`,
   `Search*`, `Count*`, or be exactly `WhoAmI`. `SendEmail`, `CreateEvent`,
   `DeleteIssue`, `PostTweet`, `ModifyLabels` — refused on sight, whatever
   your detector's code actually does with them.
2. **Deny-list, by word.** Even a scope that starts with an allowed prefix
   is refused if a write verb sits inside it as its own word —
   `ListAndDeleteIssues` clears check 1 (it starts with `List`) but is
   caught here, because `Delete` is one of its words. The forbidden words:
   `Create`, `Update`, `Merge`, `Delete`, `Post`, `Reply`, `Send`, `Modify`,
   `Write`, `Remove`, `Label`, `Draft`, `Trash`, `Invite`, `Revoke`,
   `Publish`, `Share`. Never, in any scope, under any prefix.

Run the exact check your PR will be held to, locally, before you open it:

```
cd fencepost/seam_engine
uv run python -m seam_engine.recipes discover
```

This walks every `RECIPES/<slug>/recipe.json` in the repo — yours included —
and either prints every recipe that cleared the oath and the schema, or
raises, naming every manifest that didn't and exactly why. `tests/test_recipes_doctrine.py`
runs the same function in CI. **A recipe PR is mergeable exactly when this
command returns cleanly against the tree the PR produces** — that is this
task's own done condition, made literal.

## MOCK ONLY — the other standing law

Per the Hand's law, no recipe reads a live account the day it is merged, no
matter how narrow its declared scopes are. `fixture` must point under
`fixtures/<slug>/`, checked by the same validator — a `fixture` path that
doesn't start with `fixtures/` is refused exactly like a write-shaped scope
is. Your detector reads local fixture files shaped like what the live tool
would return, the same "fixture today, live scope tomorrow" pattern
`gmail_calendar.py` already lives by (see its own module docstring). A
recipe graduates to a live read only the way `gmail_calendar.py` is waiting
to: the Hand extends a real gateway with the scopes your `recipe.json`
already declares, and your fixture loader gets swapped for a real call. The
detection logic — `compute_gaps`, or whatever you name it — does not change
one line when that happens.

## New toolkits

`toolkit` does not have to be one already on `SCOPES.md`'s table. If your
recipe watches a seam involving Slack, Notion, or anything else the town
hasn't connected yet, name it — the same way `gmail_calendar.py` proposed
`gmail`/`google_calendar` before either had a live scope. The oath still
applies to whatever scope names you declare for it; a proposed toolkit does
not get a looser check than an existing one.

## No grading, ever

Your recipe's `headline`/`detail` text names the gap. It never names or
ranks the human, the account, or any other tool or automation as having
dropped the ball — the same law every detector in this engine already
keeps (`STRATEGY.md`: *"the friend of every automation... it never says
anyone dropped the ball"*). A recipe that grades gets the same rejection
treatment as a write-shaped scope, just from a human reviewer instead of
`recipes.py` — this one, the code cannot check for you.

## Opening the PR

1. `RECIPES/<slug>/recipe.json` + `detector.py`, `fixtures/<slug>/*` — the
   shape above.
2. `uv run python -m seam_engine.recipes discover` returns cleanly, your
   recipe included.
3. A test in `seam_engine/tests/` that runs your `entrypoint` against your
   own fixture and asserts what it finds — the same "prove it runs, don't
   just claim it" discipline `test_recipes_doctrine.py` holds the shipped
   example recipe to.
4. `cd fencepost/seam_engine && uv run --extra dev python -m pytest -q` — green,
   same as every other PR in this repo. (Not `uv run python -m pytest -q` on its
   own: unlike `ONBOARDING.md`'s minute 1, which runs `uv sync --extra dev` first,
   this checklist never syncs the dev group before this step. A bare `uv run`
   here builds a fresh `.venv` from the base `dependencies` list alone —
   `pytest` lives only in `[project.optional-dependencies].dev` — and fails
   with `No module named pytest`. `--extra dev` makes the command correct
   standing on its own, the same form `ROADMAP.md`'s own task proofs already use.)
5. Open the PR. State the seam your recipe watches and why it's a real one,
   not a coincidence Ogun's law would tell you to drop.

Nothing about the review that follows is different from any other PR to
this repo — the same eyes, the same standards. What this document and its
validator promise is narrower and load-bearing: the read-only oath is not
one more line item a reviewer might miss on a long diff. It fails the build
first, in code, on iron, whether anyone was watching or not.

*Recorded. — Nisaba*
