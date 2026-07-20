"""The recipe schema, and the oath's validator — community seam-recipes
(gap detectors), gated the same way everything else in this engine is:
enforced in code, not asked for in prose. (ROADMAP.md #22)

A **seam recipe** is the unit a stranger contributes: a small, self-contained
detector that watches one new seam, shaped exactly like the two detectors
already in this engine (`scan.compute_candidates`, `gmail_calendar.compute_gaps`)
but living outside the core package, under `RECIPES/<slug>/`, so a first-time
contributor never has to touch `seam_engine/src/seam_engine/` at all.

CONTRIBUTING.md is the schema written in prose, for a human. This module is
the same schema written in code, for a CI run that does not trust prose —
`discover_recipes()` walks every `RECIPES/<slug>/recipe.json` in the repo and
raises before a single one that declares a write-shaped scope is allowed to
exist, independent of whether a human reviewer ever reads the manifest.
Ògún's oath (`SCOPES.md`, "`Get*`, `List*`, `Read*`, `Search*`, `Count*`,
`WhoAmI` — and nothing else") does not bend for a recipe just because a
stranger, not a god, wrote it.

Two independent checks guard every declared scope, the same "fails closed,
not just once" shape as `gateway.is_read_only_capabilities` and
`draftback.FORBIDDEN_DELIVERY_ACTIONS`:

1. **Allow-list, by prefix.** A scope must match `Get*`/`List*`/`Read*`/
   `Search*`/`Count*`, or be exactly `WhoAmI`. Anything else is refused on
   sight.
2. **Deny-list, by word.** Even a scope that happens to start with an
   allowed prefix is refused if a write verb appears anywhere inside it as
   its own PascalCase word — `ListAndDeleteIssues` clears check 1 (it starts
   with `List`) but is caught here, because `Delete` is one of its words.
   Belt and suspenders: the allow-list alone is not enough to catch a scope
   name shaped to slip past it.

A recipe also has to keep the town's other standing law: MOCK ONLY. Every
recipe's `fixture` field must point under `fixtures/` — no recipe reads a
real account, on the day it is merged, no matter how narrow its declared
scopes are. That graduates only the way `gmail_calendar.py` did: the Hand
extends a live gateway, and the fixture loader is swapped for a real call —
the detection logic does not change.

This is a schema-and-manifest gate, not a sandboxed code executor: it never
runs a contributed `detector.py` as part of validating a PR is safe to
consider — `load_recipe_manifest` never imports it, only checks its
`recipe.json`. It makes no claim about what a recipe's Python *does* beyond
what its manifest *declares*. A human still reads the code before merge —
this module is what makes sure that human is never the only thing standing
between a write-scoped recipe and the repo.
"""
from __future__ import annotations

import importlib.util
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# fencepost/  (…/fencepost/seam_engine/src/seam_engine/recipes.py → parents[3])
_FENCEPOST_ROOT = Path(__file__).resolve().parents[3]
RECIPES_DIR_NAME = "RECIPES"
MANIFEST_FILENAME = "recipe.json"

# Every field a recipe.json must carry, no more forgiving than this. Quoted
# verbatim in CONTRIBUTING.md's schema table — tests/test_recipes_doctrine.py
# fails red the moment the two drift.
REQUIRED_FIELDS: tuple[str, ...] = (
    "slug",
    "title",
    "author",
    "description",
    "toolkit",
    "scopes",
    "fixture",
    "detector_file",
    "entrypoint",
    "confidence_notes",
)

_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")

# Check 1/2 — allow-list, by prefix. Mirrors SCOPES.md's oath line verbatim:
# "Get*, List*, Read*, Search*, Count*, WhoAmI — and nothing else."
_ALLOWED_SCOPE_RE = re.compile(r"^(Get|List|Read|Search|Count)[A-Za-z0-9]*$")

# Check 2/2 — deny-list, by PascalCase word. Same spirit as gateway.py's
# _WRITE_VERBS and draftback.py's FORBIDDEN_DELIVERY_ACTIONS: a word that, if
# it named a whole tool, would change the world, is refused here even when it
# is only one word inside a longer scope name.
_FORBIDDEN_VERBS: frozenset[str] = frozenset({
    "Create", "Update", "Merge", "Delete", "Post", "Reply", "Send",
    "Modify", "Write", "Remove", "Label", "Draft", "Trash", "Invite",
    "Revoke", "Publish", "Share",
})

_PASCAL_WORD_RE = re.compile(r"[A-Z][a-z0-9]*")

# The allow-list prefixes (check 1), lowercased once for the glued-verb check
# below. Every scope that reaches check 2 is already guaranteed (by check 1)
# to start with one of these -- which makes the very first PascalCase word
# the one place a scope author is forced to put something, and so the most
# natural place to hide a write verb if the tokenizer can be fooled.
_ALLOWED_PREFIXES_LOWER: tuple[str, ...] = ("get", "list", "read", "search", "count")


def _word_hides_glued_verb(word: str) -> str | None:
    """`_pascal_words` only starts a new word at an uppercase letter, so a
    forbidden verb spelled in lowercase right after an allowed prefix -- with
    no capital letter to mark where the prefix ends and the verb begins --
    is swallowed into one word and never reaches the exact-match check below.
    `"GetdeleteIssues"` tokenizes as `["Getdelete", "Issues"]`; `"Getdelete"`
    equals neither `"Get"` nor `"Delete"`, so the write verb inside it was
    never checked at all. Returns the forbidden verb found glued this way, or
    `None` if `word` doesn't start with an allowed prefix immediately
    followed by one."""
    lowered = word.lower()
    for prefix in _ALLOWED_PREFIXES_LOWER:
        if not lowered.startswith(prefix):
            continue
        remainder = lowered[len(prefix):]
        for verb in _FORBIDDEN_VERBS:
            if remainder.startswith(verb.lower()):
                return verb
    return None


class RecipeValidationError(ValueError):
    """Raised when a recipe manifest fails the oath or the schema. Fails
    closed: a manifest is refused until every check clears, never assumed
    safe because most of it looked fine."""


@dataclass(frozen=True)
class RecipeManifest:
    """One community recipe's declared shape — parsed, not yet trusted until
    `validate_recipe` has run on it. `path`, when set, is where this manifest
    was loaded from (`load_recipe_manifest` sets it; a manifest built by hand
    in a test may leave it `None`)."""

    slug: str
    title: str
    author: str
    description: str
    toolkit: str
    scopes: tuple[str, ...]
    fixture: str
    detector_file: str
    entrypoint: str
    confidence_notes: str
    path: Path | None = None


def _pascal_words(scope: str) -> list[str]:
    return _PASCAL_WORD_RE.findall(scope)


def _check_scope_is_read_only(scope: str, *, where: str) -> None:
    """Both checks, in order. Raises `RecipeValidationError` naming exactly
    which one failed and why — never a bare refusal."""
    if scope != "WhoAmI" and not _ALLOWED_SCOPE_RE.match(scope):
        raise RecipeValidationError(
            f"{where}: scope {scope!r} is not read-only. Per SCOPES.md's oath, "
            "every scope a recipe declares must be Get*/List*/Read*/Search*/"
            "Count*, or exactly WhoAmI — nothing else, ever. RED MEANS STOP."
        )
    for word in _pascal_words(scope):
        if word in _FORBIDDEN_VERBS:
            raise RecipeValidationError(
                f"{where}: scope {scope!r} carries the write verb {word!r} as "
                "one of its own words. A recipe that can create, update, "
                "merge, delete, post, reply, send, modify, write, remove, "
                "label, draft, trash, invite, revoke, publish, or share is "
                "not a Fencepost recipe. Refused before a human reviewer "
                "ever reads the detector code."
            )
        glued_verb = _word_hides_glued_verb(word)
        if glued_verb is not None:
            raise RecipeValidationError(
                f"{where}: scope {scope!r} glues the write verb {glued_verb!r} "
                f"directly onto its allowed prefix inside the word {word!r}, "
                "with no capital letter marking where one ends and the other "
                "begins. Shaped exactly to slip past the exact-word check -- "
                "refused before a human reviewer ever reads the detector code."
            )


def validate_recipe(manifest: RecipeManifest) -> RecipeManifest:
    """Pure function, no I/O: the oath and the schema, checked against an
    already-parsed manifest. Returns the same manifest unchanged if every
    check clears; raises `RecipeValidationError` on the first one that
    doesn't. Same "prove it, don't just claim it" shape as
    `gateway.is_read_only_capabilities` — this is the code a CI run trusts,
    not the prose in CONTRIBUTING.md that merely describes it.
    """
    where = str(manifest.path) if manifest.path is not None else f"RECIPES/{manifest.slug}/{MANIFEST_FILENAME}"

    if not _SLUG_RE.match(manifest.slug):
        raise RecipeValidationError(
            f"{where}: slug {manifest.slug!r} must match {_SLUG_RE.pattern} "
            "(lowercase, starts with a letter, kebab-case)"
        )

    if not manifest.title.strip():
        raise RecipeValidationError(f"{where}: title is empty")
    if not manifest.description.strip():
        raise RecipeValidationError(f"{where}: description is empty")
    if not manifest.confidence_notes.strip():
        raise RecipeValidationError(
            f"{where}: confidence_notes is empty — Ogun's law: a recipe that "
            "cannot explain, in plain language, why its confidence score is "
            "not inflated does not get to carry one"
        )

    if not manifest.scopes:
        raise RecipeValidationError(
            f"{where}: scopes must name at least one Arcade tool this recipe reads"
        )
    for scope in manifest.scopes:
        _check_scope_is_read_only(scope, where=where)

    if not manifest.fixture.startswith("fixtures/"):
        raise RecipeValidationError(
            f"{where}: fixture {manifest.fixture!r} must live under fixtures/ "
            "— MOCK ONLY, per the Hand's law. No recipe reads a live account "
            "the day it is merged, no matter how narrow its scopes are; see "
            "gmail_calendar.py's own WIP doctrine for how a recipe graduates."
        )
    if ".." in Path(manifest.fixture).parts:
        raise RecipeValidationError(
            f"{where}: fixture path {manifest.fixture!r} may not escape fixtures/"
        )

    if (
        "/" in manifest.detector_file
        or "\\" in manifest.detector_file
        or not manifest.detector_file.endswith(".py")
        or manifest.detector_file in ("", ".py")
    ):
        raise RecipeValidationError(
            f"{where}: detector_file {manifest.detector_file!r} must be a "
            "bare *.py filename inside the recipe's own RECIPES/<slug>/ "
            "directory — no path segments, no escaping it"
        )

    if not manifest.entrypoint.isidentifier():
        raise RecipeValidationError(
            f"{where}: entrypoint {manifest.entrypoint!r} is not a valid Python identifier"
        )

    return manifest


def load_recipe_manifest(path: Path) -> RecipeManifest:
    """Read one `recipe.json` off disk, check its schema is complete, check
    its slug matches the directory it lives in, then run it through
    `validate_recipe`. Raises `RecipeValidationError` naming exactly what is
    wrong; never silently coerces a bad manifest into a passable one."""
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RecipeValidationError(f"{path}: no such file") from exc

    try:
        data: dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RecipeValidationError(f"{path}: not valid JSON ({exc})") from exc

    if not isinstance(data, dict):
        raise RecipeValidationError(f"{path}: recipe.json must be a JSON object")

    missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
    if missing:
        raise RecipeValidationError(
            f"{path}: missing required field(s) {missing} — see CONTRIBUTING.md's schema table"
        )

    scopes_raw = data["scopes"]
    if not isinstance(scopes_raw, list):
        raise RecipeValidationError(f"{path}: scopes must be a JSON list of strings")

    manifest = RecipeManifest(
        slug=str(data["slug"]),
        title=str(data["title"]),
        author=str(data["author"]),
        description=str(data["description"]),
        toolkit=str(data["toolkit"]),
        scopes=tuple(str(s) for s in scopes_raw),
        fixture=str(data["fixture"]),
        detector_file=str(data["detector_file"]),
        entrypoint=str(data["entrypoint"]),
        confidence_notes=str(data["confidence_notes"]),
        path=path,
    )

    if manifest.slug != path.parent.name:
        raise RecipeValidationError(
            f"{path}: manifest slug {manifest.slug!r} does not match its own "
            f"directory name {path.parent.name!r} — RECIPES/<slug>/recipe.json, always"
        )

    return validate_recipe(manifest)


def discover_recipes(fencepost_root: Path | None = None) -> list[RecipeManifest]:
    """Walk every `RECIPES/<slug>/recipe.json` in the repo, validate each one,
    and return the full list only if every single one clears the oath and
    the schema. This is the function CI runs over a PR: it raises, naming
    every failing manifest at once, the moment any one recipe in the
    directory — new or old — declares a write-shaped scope or a broken
    schema. A first external recipe PR is mergeable exactly when this
    function, run against the tree the PR produces, returns cleanly.
    """
    root = fencepost_root if fencepost_root is not None else _FENCEPOST_ROOT
    recipes_dir = root / RECIPES_DIR_NAME
    if not recipes_dir.exists():
        return []

    manifest_paths = sorted(recipes_dir.glob(f"*/{MANIFEST_FILENAME}"))
    manifests: list[RecipeManifest] = []
    errors: list[str] = []
    for path in manifest_paths:
        try:
            manifests.append(load_recipe_manifest(path))
        except RecipeValidationError as exc:
            errors.append(str(exc))

    if errors:
        raise RecipeValidationError(
            "one or more recipe manifests failed the read-only oath or the "
            "schema — nothing merges until every line below is fixed:\n  "
            + "\n  ".join(errors)
        )

    return manifests


def load_detector(manifest: RecipeManifest) -> Callable[..., Any]:
    """Import `manifest.detector_file` as a standalone module (never through
    `seam_engine`'s own package — a recipe is not part of the core engine)
    and return the callable named `manifest.entrypoint`. Used to prove a
    shipped recipe's detector is real and runnable, not merely declared —
    the same "prove it" discipline the rest of this engine holds itself to.
    """
    if manifest.path is None:
        raise RecipeValidationError(
            "load_detector needs a manifest loaded from disk via load_recipe_manifest "
            "(this manifest's .path is None)"
        )
    detector_path = manifest.path.parent / manifest.detector_file
    if not detector_path.exists():
        raise RecipeValidationError(
            f"{manifest.path}: detector_file {manifest.detector_file!r} does "
            f"not exist at {detector_path}"
        )

    module_name = f"seam_engine._recipe_{manifest.slug.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, detector_path)
    if spec is None or spec.loader is None:
        raise RecipeValidationError(f"{detector_path}: could not be loaded as a Python module")
    module = importlib.util.module_from_spec(spec)
    # Registered in sys.modules *before* exec, not after: dataclasses in the
    # loaded module (like detector.py's Release/ChangelogEntry) resolve their
    # own field annotations via sys.modules[cls.__module__] at class-body
    # time, which is None until this line runs.
    import sys as _sys
    _sys.modules[module_name] = module
    spec.loader.exec_module(module)

    fn = getattr(module, manifest.entrypoint, None)
    if fn is None or not callable(fn):
        raise RecipeValidationError(
            f"{detector_path}: no callable named {manifest.entrypoint!r} found"
        )
    return fn


# --- CLI: a contributor's own pre-flight check, before opening a PR --------


def main(argv: list[str] | None = None) -> int:
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ("discover", "check"):
        print("usage: python -m seam_engine.recipes {discover|check <path/to/recipe.json>}")
        print("       (the same check CI runs over every PR that touches RECIPES/)")
        return 2

    cmd = argv[0]
    try:
        if cmd == "discover":
            manifests = discover_recipes()
            print(f"{len(manifests)} recipe(s) cleared the oath and the schema:")
            for m in manifests:
                print(f"  - {m.slug}  ({m.title})")
        else:
            if len(argv) < 2:
                print("usage: python -m seam_engine.recipes check <path/to/recipe.json>")
                return 2
            manifest = load_recipe_manifest(Path(argv[1]))
            print(f"OK  {manifest.slug}: {manifest.title}")
    except RecipeValidationError as exc:
        print(f"REJECTED\n{exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
