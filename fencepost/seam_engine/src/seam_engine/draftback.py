"""The draft-back — the Ledger, written into a place YOU own. (ROADMAP #17)

Everything upstream of this module (`scan.py`, `ranking.py`, `ledger.py`,
`report.py`) ends with a *record*: a sealed tablet in `GAPS/`, a rendered
dispatch in `REPORTS/`. Both live in the town's own repo. STRATEGY.md's third
promise (fencepost/README.md §"three promises") is a different thing: "each
morning [the human] receives one legible, timestamped artifact written back
into a place they own (an email-to-self draft or a Notion page)." A GitHub
file is durable, but it is not *yours* the way your own inbox or your own
Notion workspace is. This module is the seam between the two.

**This is the one place in Fencepost that is allowed to write anything
outside the repo at all — and it is bounded on every side:**

1. **Draft-only, on iron.** The only actions this module will ever call are
   draft-creation actions (`CreateDraftEmail`, `CreateDraft`, `CreatePage`).
   `SendEmail`, `Publish`, `Share`, `Post`, `Delete`, `Trash`, `Modify` are a
   permanent deny-list (`FORBIDDEN_DELIVERY_ACTIONS`) — `deliver_email_draft`
   and `deliver_notion_page` refuse to run at all against an action name that
   is not on `ALLOWED_DELIVERY_ACTIONS`, raising `DraftBackViolation` before
   any call happens. `tests/test_draftback_doctrine.py` goes further and
   statically proves the send path doesn't exist at all: no forbidden action
   (nor `OutlookMail_SendEmail`, the live tool's name) ever appears in this
   file's source shaped like a call, the injected adapter is invoked nowhere
   but the two `deliver_*` functions, and `_assert_draft_only` runs strictly
   before it in both — the same "prove it, don't just claim it" discipline
   `gateway.is_read_only_capabilities` holds the scan's capabilities string
   to, applied to code instead of prose.
2. **Self, never a destination.** `render_email_draft` does not accept a
   `to` address. There is no parameter anywhere in this module that lets a
   caller point a draft at someone else's inbox or someone else's Notion
   workspace — the address is always resolved by whichever Arcade OAuth
   session the caller's adapter is authenticated as, i.e. always the
   connected user's own account. A draft-back cannot be redirected because
   it is never given anywhere to redirect *to*.
3. **A draft is not a send.** Creating a draft is a write, but it is a write
   that changes nothing the human did not already ask to receive, and it
   fires nothing — the message sits, unsent, until the human reads it and
   decides. This is the same "last action is the human's" promise
   (SCOPES.md §2) the whole town already keeps for the suggested move in
   every report; draft-back keeps it for the record itself.
4. **No adapter, no network, by default.** This module holds no Arcade
   client, no HTTP library, no credential. `deliver_email_draft` and
   `deliver_notion_page` take the actual draft-creating call as an injected
   function (`create_fn`) supplied by the caller — this file cannot reach a
   real account on its own, because it does not know how to. The CLI at the
   bottom never wires one; it only renders and writes a **local preview** to
   `DRAFTS/`, so the exact bytes a live draft would carry are visible and
   testable before any live target exists.

**WIP, on purpose (ROADMAP.md #17).** No live target is connected: the-hand
gateway is a shared bot account, not a human's own inbox or Notion
workspace, so there is no "self" for a draft to land in yet, and only the
Hand may connect one (docs/architecture/reference.md, the Road-Law: "The
gods argue. The Hand decides. Arcade acts."). Nisaba can build the seam and
prove it never sends; Nisaba cannot open the account it writes into.

**Documented, not executed: the exact live mapping.** The-hand gateway
already carries an email channel — `OutlookMail_CreateDraftEmail` — and this
module's email path is built to bind to it exactly: a future live `create_fn`
for `deliver_email_draft` would call `OutlookMail_CreateDraftEmail` with the
rendered `EmailDraft`'s subject/body, action_name still checked against
`ALLOWED_DELIVERY_ACTIONS` first. The counterpart, `OutlookMail_SendEmail`,
is the one tool this module is documented to NEVER call, under any
circumstance — it is not in `ALLOWED_DELIVERY_ACTIONS`, it is not wired as
anyone's `create_fn` here, and no line of this file invokes it
(`tests/test_draftback_doctrine.py` statically proves the call never
appears). Writing this mapping down is the whole of what this task asks for
today; actually connecting `create_fn` to a live mailbox is the Hand's ground
alone, and stays PENDING until the Hand crosses it.

Recorded.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from seam_engine import ledger, report
from seam_engine.wall import wall_for

# fencepost/  (…/fencepost/seam_engine/src/seam_engine/draftback.py → parents[3])
_FENCEPOST_ROOT = Path(__file__).resolve().parents[3]

# The only account a draft is ever addressed to: the caller's own, resolved
# by whichever OAuth session the adapter is authenticated as. Never a real
# address, on purpose — see module docstring, point 2.
SELF = "self"

# --- the deny-list / allow-list, on iron -------------------------------------

# The only delivery actions this module will ever call. Every one of them
# creates a draft and fires nothing. Nothing else may be passed to
# deliver_email_draft / deliver_notion_page as `action_name`.
ALLOWED_DELIVERY_ACTIONS: tuple[str, ...] = (
    "CreateDraftEmail",
    "CreateDraft",
    "CreatePage",
)

# Never, under any action_name, may these run through this module. Kept
# explicit (not just "not in ALLOWED_DELIVERY_ACTIONS") so a future action
# with an unfamiliar name still fails safe: the allow-list check below is
# the real gate, this list is what a doctrine test greps for by name.
FORBIDDEN_DELIVERY_ACTIONS: tuple[str, ...] = (
    "SendEmail",
    "Send",
    "Publish",
    "Share",
    "PostTweet",
    "Post",
    "Delete",
    "Trash",
    "Modify",
    "Reply",
)


class DraftBackViolation(RuntimeError):
    """Raised when a caller asks this module to deliver through an action
    that is not on the draft-only allow-list. Fails closed: an unrecognized
    action name is refused, not assumed safe."""


def _assert_draft_only(action_name: str) -> None:
    if action_name not in ALLOWED_DELIVERY_ACTIONS:
        raise DraftBackViolation(
            f"{action_name!r} is not a draft-only action. Fencepost's draft-back "
            f"will only ever call one of {ALLOWED_DELIVERY_ACTIONS}. Refused, "
            f"nothing was sent, nothing was called."
        )


# --- pure rendering: the ledger's latest entry, shaped for delivery ---------


@dataclass
class EmailDraft:
    """An unsent email draft. `to` is always SELF — see module docstring."""

    to: str
    subject: str
    body: str


@dataclass
class NotionBlock:
    kind: str  # "heading" | "paragraph" | "bulleted_list_item" | "divider"
    text: str = ""


@dataclass
class NotionPageDraft:
    """An unpublished Notion page. Lives in the caller's own workspace only
    — this module never names a workspace, database, or parent page id."""

    title: str
    blocks: list[NotionBlock] = field(default_factory=list)


def render_email_draft(sealed: dict[str, Any]) -> EmailDraft:
    """Render the ledger's sealed record as an email-to-self draft.

    Pure and deterministic: the same `sealed` payload always yields the same
    draft. Reuses `report.render_report` for the body so the draft and the
    public dispatch never drift into two different tellings of the same day.
    """
    date = sealed.get("date") or sealed.get("generated_at", "")[:10]
    body = report.render_report(sealed)
    subject = f"Fencepost — {date}: {_headline_for_subject(sealed)}"
    return EmailDraft(to=SELF, subject=subject, body=body)


def render_notion_page(sealed: dict[str, Any]) -> NotionPageDraft:
    """Render the ledger's sealed record as an unpublished Notion page.

    Pure and deterministic, same contract as `render_email_draft`. Blocks are
    a plain, adapter-agnostic shape (`NotionBlock`) — a caller's live adapter
    is responsible for turning these into the real Notion API's block JSON,
    keeping this module free of any Notion SDK or network dependency.
    """
    date = sealed.get("date") or sealed.get("generated_at", "")[:10]
    repo = sealed.get("repo", "unknown")
    primary = sealed.get("primary_gap")
    recorded = sealed.get("fenceposts_recorded_total", 0)
    wall = wall_for(recorded)

    blocks: list[NotionBlock] = [
        NotionBlock("heading", f"Fencepost Report — {date}"),
        NotionBlock("paragraph", f"The one thing that fell between {repo}'s accounts yesterday."),
        NotionBlock("divider"),
    ]
    # Task 728 (retrya): mirrors `report.render_report`'s own three-way split
    # (primary / contender-too-close / nothing cleared) -- this page used to
    # collapse the contender case into the same "Nothing cleared the bar"
    # line as a genuinely quiet day, the same false-claim shape task 605
    # already fixed once in `report.py` but never carried over here.
    has_contender = (not primary) and any(t.get("label") == "contender" for t in sealed.get("tail", []))
    if primary:
        blocks.append(NotionBlock("heading", primary["headline"]))
        blocks.append(NotionBlock("paragraph", f"Confidence {primary['confidence']}."))
        detail = (primary.get("detail") or "").strip()
        if detail:
            blocks.append(NotionBlock("paragraph", detail))
        for ev in primary.get("evidence", []):
            blocks.append(NotionBlock("bulleted_list_item", ev))
    elif has_contender:
        blocks.append(
            NotionBlock(
                "paragraph",
                "None elected today. A candidate cleared the bar, but the field "
                "stood too close together to honestly call one THE gap.",
            )
        )
    else:
        blocks.append(NotionBlock("paragraph", "Nothing cleared the bar today. The seam held."))

    plural = "" if recorded == 1 else "s"
    blocks.append(NotionBlock("paragraph", f"{recorded} fencepost{plural} named to date. The wall reads {wall}."))
    blocks.append(NotionBlock("paragraph", f"Your move: {report.suggest_move(primary, has_contender=has_contender)}"))
    blocks.append(NotionBlock("paragraph", report.THE_LINE))

    return NotionPageDraft(title=f"Fencepost — {date}", blocks=blocks)


def _headline_for_subject(sealed: dict[str, Any]) -> str:
    primary = sealed.get("primary_gap")
    if not primary:
        return "nothing cleared the bar"
    headline = primary.get("headline", "").strip()
    return headline if headline else "one gap found"


# --- delivery: injected adapter only, draft-only action, never a send -------


def deliver_email_draft(
    sealed: dict[str, Any],
    create_fn: Callable[[EmailDraft], dict[str, Any]],
    *,
    action_name: str = "CreateDraftEmail",
) -> dict[str, Any]:
    """Render an email-to-self draft and hand it to `create_fn` — the ONE
    call this function will ever make, and only after `action_name` is
    checked against the draft-only allow-list. `create_fn` is supplied by
    the caller (e.g. a live Arcade tool binding); this module holds no
    credential and calls nothing on its own. Never sends. Returns the
    rendered draft plus whatever `create_fn` returns (e.g. a draft id).
    """
    _assert_draft_only(action_name)
    draft = render_email_draft(sealed)
    result = create_fn(draft)
    return {"channel": "email", "action": action_name, "draft": asdict(draft), "result": result}


def deliver_notion_page(
    sealed: dict[str, Any],
    create_fn: Callable[[NotionPageDraft], dict[str, Any]],
    *,
    action_name: str = "CreatePage",
) -> dict[str, Any]:
    """Same contract as `deliver_email_draft`, for an unpublished Notion
    page. `create_fn` must create the page only — never publish or share it."""
    _assert_draft_only(action_name)
    page = render_notion_page(sealed)
    result = create_fn(page)
    return {
        "channel": "notion",
        "action": action_name,
        "draft": {"title": page.title, "blocks": [asdict(b) for b in page.blocks]},
        "result": result,
    }


# --- local preview (what the CLI writes; no live account, ever) -------------


def drafts_dir(base: Path | None = None) -> Path:
    """Where local, offline previews of the draft-back land. Not a live
    account — a rendering a human can read before any live target exists."""
    return (base if base is not None else _FENCEPOST_ROOT) / "DRAFTS"


def _fmt_notion_preview(page: NotionPageDraft) -> str:
    lines = [f"# {page.title}", ""]
    for b in page.blocks:
        if b.kind == "heading":
            lines.append(f"## {b.text}")
        elif b.kind == "divider":
            lines.append("---")
        elif b.kind == "bulleted_list_item":
            lines.append(f"- {b.text}")
        else:
            lines.append(b.text)
        lines.append("")
    return "\n".join(lines)


def render_preview(sealed: dict[str, Any], channel: str) -> str:
    """The local, offline preview text for `channel` ('email' or 'notion').
    This is what DRAFTS/YYYY-MM-DD-<channel>.md holds — never a live draft,
    just the honest rendering of what one would contain."""
    if channel == "email":
        draft = render_email_draft(sealed)
        return (
            f"<!-- LOCAL PREVIEW ONLY. Not a live draft. No account was written to. -->\n"
            f"To: {draft.to}\n"
            f"Subject: {draft.subject}\n\n"
            f"{draft.body}"
        )
    if channel == "notion":
        page = render_notion_page(sealed)
        return (
            f"<!-- LOCAL PREVIEW ONLY. Not a live page. No workspace was written to. -->\n\n"
            f"{_fmt_notion_preview(page)}"
        )
    raise ValueError(f"unknown channel: {channel!r} (expected 'email' or 'notion')")


# --- CLI ----------------------------------------------------------------------


def _load_sealed(path: str) -> dict[str, Any]:
    """Read a sealed record for the CLI from `path` ('-' for stdin).

    A CLI-supplied file (or stdin stream) can be any syntactically valid
    JSON -- a bare list, int, bool, null, or string, not just an object --
    and `render_email_draft`/`render_notion_page` immediately treat their
    argument as a dict (`sealed.get("date")`, first line of each). Left
    unguarded, a non-object payload would crash `main()` with a bare
    `AttributeError: '<type>' object has no attribute 'get'` instead of a
    message naming the actual problem -- the same discipline `report.py`'s
    `_load_sealed_arg` and `ledger.py`'s `_load_scan` already hold in this
    same package. Task 538: all three now delegate to
    `ledger._load_json_dict`, one real implementation instead of three
    copies an AST-hash sweep only ever caught two of.
    """
    return ledger._load_json_dict(path, "sealed record")


def main(argv: list[str] | None = None) -> int:
    import sys

    from seam_engine import ledger

    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ("email", "notion"):
        print("usage: python -m seam_engine.draftback {email|notion} [sealed.json|-] [--write] [--base DIR]")
        print("       (renders a LOCAL PREVIEW only — never a live draft; see module docstring)")
        return 2

    channel = argv.pop(0)

    base: Path | None = None
    if "--base" in argv:
        i = argv.index("--base")
        if i + 1 >= len(argv):
            print("--base needs a path to a Ledger directory.")
            return 2
        base = Path(argv[i + 1])
        del argv[i : i + 2]

    write = "--write" in argv
    if write:
        argv.remove("--write")

    if argv and argv[0] != "-":
        sealed = _load_sealed(argv[0])
    elif argv == ["-"]:
        sealed = _load_sealed("-")
    else:
        records = ledger.read_records(base)
        if not records:
            print("the ledger is empty — nothing to draft-back yet")
            return 1
        sealed = ledger.tip_sealed(records)

    preview = render_preview(sealed, channel)
    print(preview)

    if write:
        date = sealed.get("date") or sealed.get("generated_at", "")[:10]
        d = drafts_dir(base)
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{date}-{channel}.md"
        path.write_text(preview, encoding="utf-8")
        print(f"\nWritten (local preview, no live account touched): {path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
