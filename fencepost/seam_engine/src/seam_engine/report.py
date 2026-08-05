"""The Fencepost Report — the daily dispatch, not the tablet.

The Ledger (`ledger.py`) keeps everything: the elected gap, every coincidence
weighed and dropped, sealed and hash-chained, for the mortal who comes back a
year later to check the town's arithmetic. The Report is the other half of the
same job and answers to a different reader — the one who has thirty seconds:
one gap, named plainly, and the line the whole arc turns on.

    You were so close. You are always so close.

A report never shows the coincidence tail. Naming six things that were *not*
the gap is honest bookkeeping in a tablet and noise in a dispatch — the reader
came for the one thing, not the ranking that produced it. If nothing cleared
the bar, the report says so in one line and stops; a quiet seam is still the
truth, and Nisaba corrects flattering numbers downward on principle, never up.

The single hand-off (`suggest_move`): every report carries exactly one "Your
move" line, phrased as something the *reader* does next — never something
Fencepost did or is about to do. This is the third promise on iron (SCOPES.md
§2, "the last action is the human's"): Fencepost may name a gap; it may never
close one. `suggest_move` is a pure function of words in, words out — it holds
no credential, calls no tool, and fires nothing. Read it end to end and you
will find no verb it can act on, only verbs it hands to you.

Pure and deterministic: `render_report` takes the same `sealed` shape a
ledger entry carries (see `ledger.append_scan`) and returns text. No I/O
except the thin CLI at the bottom, which reads the ledger and, on request,
writes `REPORTS/YYYY-MM-DD.md` — a rendering of what the ledger already
sealed, never a second source of truth.

Two more things every report now carries (ROADMAP.md #19, Kwaku Ananse):

1. **The episode line.** `render_report` accepts optional `episode_number`
   and `streak_days` — the installment count and the current unbroken
   daily-cadence count, both computed off the sealed Ledger by
   `seam_engine.streak` and never invented here. When a caller doesn't pass
   them (every existing test, any hand-built `sealed` dict), the line is
   simply absent — `render_report` stays a pure function of its arguments,
   the same law it already held before this task; it does not reach out to
   the Ledger itself to fill them in. `render_latest` and the CLI's
   ledger-reading path *do* pass them, because a report rendered off the
   real Ledger has a real episode and a real streak to report.
2. **The ad.** `CONNECT_YOUR_OWN` — one line, on every report, gap or no
   gap. Never "please star." STRATEGY.md's law on this is explicit ("the
   CTA is never 'please star' — it is 'connect your own and we'll find
   yours'"), and Kwaku Ananse's own law is stricter still (casting-record,
   voice.quirks): never a direct beg, only the story where you'd already
   want to. The line names what the town found on its *own* accounts and
   invites the reader to point the same read-only seam at theirs — it is
   an ad built entirely out of a true claim already sitting above it in
   the same report.

A third thing every report now carries (ROADMAP.md #21, Off-By-One): right
under the count, `seam_engine.wall.TEASER_LINE` — the "day it closes"
teaser. It is imported, not retyped, from the same module that computes the
wall itself (`wall_for`), so the tease and the arithmetic it is teasing can
never say two different things. It never gives a date; it says what ARC.md
already swears — that the day, if it ever comes, is a witnessed declaration,
not a countdown quietly reaching zero.

Recorded.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from seam_engine import ledger, streak
from seam_engine.wall import TEASER_LINE, wall_for

# fencepost/  (…/fencepost/seam_engine/src/seam_engine/report.py → parents[3])
_FENCEPOST_ROOT = Path(__file__).resolve().parents[3]

THE_LINE = "You were so close. You are always so close."

# Matches a single-quoted span, e.g. 'Add calendar sync helper' -- the
# convention every detector in the tree already follows for embedding
# mortal-controlled free text into a headline/detail f-string. See
# `suggest_move`'s own docstring note (task 537) for why this is stripped
# before rule-matching rather than matched over.
_QUOTED_SPAN_RE = re.compile(r"'[^']*'")

# The single hand-off. One rule beneath the words: never a verb Fencepost can
# perform itself. "Post it", "add it", "close it" — all reader-verbs. Never
# "we posted", "we'll add", "we closed". Matched against the gap's own
# headline/detail so the suggestion tracks whatever the seam turns out to be
# (an X gap today, a Gmail-vs-Calendar gap in v0.2) without the ranker or scan
# needing to know anything about report-writing. First match wins; order is
# most-specific first. The default line beneath the table fires only when a
# future gap kind doesn't yet have a rule of its own here — it is deliberately
# generic rather than silently wrong.
#
# Task 537 (retrya): the "post about it" rule only ever matched `scan.py`'s
# own core headline phrasing ("...never reached @oritatown"). Four of
# RECIPES/'s own real, shipped community recipes -- issue-closed-not-tweeted,
# merged-pr-not-tweeted, release-not-tweeted, star-milestone-not-announced --
# grew a different, equally real phrasing ("never tweeted" / "never
# announced") and never once matched, so had any of the four ever ranked as
# the report's primary gap, the reader would have gotten the generic default
# line instead of the correct "post about it" hand-off. Confirmed live
# pre-fix (`suggest_move` on each of the four's real headline shape returned
# `_DEFAULT_MOVE`, not this rule) before adding the two missing needles.
#
# Task 550 (retrya): the same drift, found in the one pair of recipes that
# swept in afterward without anyone re-running this check against them --
# `readme-credited-not-thanked` and `contributor-thanked-not-credited`. The
# first's real headline ("@{handle} is credited in the README, never thanked
# on X") is a genuine "post about it" gap -- thank them on X -- but its own
# phrasing ("never thanked on x") never matched "never tweeted" or "never
# announced" either, so it fell through to `_DEFAULT_MOVE` too (confirmed
# live pre-fix). The second recipe's real headline ("@{handle} was thanked on
# X, not yet in the README credits") is the mirror gap and a genuinely
# different hand-off -- nothing to post, a README line to add -- so it gets
# its own new rule rather than being folded into the post-about-it family.
#
# Task 557 (retrya): a third recurrence of the exact same drift shape, found
# this time by walking every real recipe's own fixture-generated gap
# headline through `suggest_move` (`discover_recipes`/`load_detector`, the
# same mechanism `test_recipes.py` already exercises per recipe) instead of
# re-reading detector.py source by eye, which is what let this one slip past
# both 537's and 550's manual sweeps. `milestone-closed-not-tweeted`'s real
# headline ("Milestone #{n} closed, but no tweet has ever named it") is a
# genuine "post about it" gap -- the milestone-side twin of
# `issue-closed-not-tweeted`/`merged-pr-not-tweeted`/`release-not-tweeted`,
# which this same rule table already covers -- but its own phrasing ("no
# tweet has ever named it") matches none of "never tweeted"/"never
# announced"/"@oritatown", so it fell through to `_DEFAULT_MOVE` too
# (confirmed live pre-fix: `suggest_move` on the recipe's own real fixture
# gap returned "Close it yourself..." for a milestone that is already
# closed -- a doubly wrong hand-off, since there is nothing left to close).
_MOVE_RULES: tuple[tuple[str, str], ...] = (
    (
        "calendar",
        "Add it to your Calendar yourself. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "reminder",
        "Set the reminder yourself. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "@oritatown",
        "Post about it yourself — a single line linking it is enough. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "never tweeted",
        "Post about it yourself — a single line linking it is enough. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "never announced",
        "Post about it yourself — a single line linking it is enough. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "never thanked on x",
        "Post about it yourself — a single line linking it is enough. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "no tweet has ever named it",
        "Post about it yourself — a single line linking it is enough. Fencepost only found the seam; it does not cross it.",
    ),
    (
        "not yet in the readme credits",
        "Add them to the README yourself — a line in the credits is enough. Fencepost only found the seam; it does not cross it.",
    ),
)
_DEFAULT_MOVE = (
    "Close it yourself, however it's meant to be closed. Fencepost only found the seam; it does not cross it."
)
_NO_GAP_MOVE = "Nothing to hand off today. Check back tomorrow — the seam is still watched."

# The live walkthrough (CONNECT.md, mirrored at docs/fencepost/connect.html)
# — the exact page a reader lands on to build their own read-only gateway.
# One URL, quoted here and nowhere paraphrased, so the ad never drifts from
# the walkthrough it is advertising.
CONNECT_URL = "https://thierrypdamiba.github.io/orita/fencepost/connect.html"

# Every report carries this line, gap or no gap (STRATEGY.md, "How stars are
# earned": "the CTA is never 'please star' — it is 'connect your own and
# we'll find yours'"). It names a true claim the report already made above
# it — this seam, this account, this scan — and hands the reader the same
# five-minute, read-only door, never a beg.
CONNECT_YOUR_OWN = (
    f"**Connect your own.** This is the seam we watch on our own accounts. "
    f"Point Fencepost at yours — five minutes, read-only, revocable in one "
    f"click — and it will find the one thing sitting in *your* seam. "
    f"[Connect your own]({CONNECT_URL})."
)


def suggest_move(primary_gap: dict[str, Any] | None) -> str:
    """The single hand-off: one suggested human action, phrased as the reader's
    move, and never Fencepost's. Pure — no I/O, no side effect, nothing fired.

    Deterministic: the same `primary_gap` always yields the same line. When
    there is no primary gap, the move is still exactly one line — checking
    back tomorrow is a move too, and the promise ("every report carries one
    hand-off") does not get an exception for a quiet day.
    """
    if not primary_gap:
        return _NO_GAP_MOVE
    raw = f"{primary_gap.get('headline', '')} {primary_gap.get('detail', '')}"
    # Task 537 (retrya): every detector across scan.py and all 45 RECIPES/
    # embeds mortal-controlled free text (a commit message, an issue/PR/
    # milestone title, a tweet's own text) inside single quotes -- confirmed
    # by grep across every headline=/detail= f-string in the tree, zero
    # exceptions. Left in the haystack, that free text can accidentally
    # contain a rule's needle and misfire the wrong move for an unrelated
    # gap: a dangling-issue-reference gap whose commit message happened to
    # read "Add calendar sync helper" rendered the Calendar move line for a
    # gap that has nothing to do with calendars (reproduced live pre-fix).
    # Stripping quoted spans first leaves only the recipe-authored template
    # prose the rules are actually meant to match.
    haystack = _QUOTED_SPAN_RE.sub(" ", raw).lower()
    for needle, move in _MOVE_RULES:
        if needle in haystack:
            return move
    return _DEFAULT_MOVE


def reports_dir(base: Path | None = None) -> Path:
    """Where rendered dispatches live. Defaults to fencepost/REPORTS/."""
    return (base if base is not None else _FENCEPOST_ROOT) / "REPORTS"


def _fmt_evidence(urls: list[str], limit: int = 3) -> str:
    if not urls:
        return ""
    lines = []
    for u in urls[:limit]:
        tail = u.rstrip("/").rsplit("/", 1)[-1][:12]
        lines.append(f"- [{tail}]({u})")
    return "\n".join(lines)


def render_report(
    sealed: dict[str, Any],
    *,
    episode_number: int | None = None,
    streak_days: int | None = None,
) -> str:
    """Render one Fencepost Report from a sealed (or scan) record.

    `sealed` carries the same fields a ledger entry's typed record does:
    date/generated_at, repo, primary_gap, fenceposts_recorded_total. The tail
    is read but never shown — a report names the one gap, or none.

    `episode_number`/`streak_days` are optional and purely additive: pass
    them (as `render_latest` and the CLI's ledger-reading path do, sourced
    from `seam_engine.streak`) to render the serialization line; omit them
    and the report renders exactly as it always has. `render_report` still
    takes only its arguments and returns text — it never reaches into the
    Ledger itself to invent a number that wasn't handed to it.
    """
    date = sealed.get("date") or sealed.get("generated_at", "")[:10]
    repo = sealed.get("repo", "unknown")
    primary = sealed.get("primary_gap")
    recorded = sealed.get("fenceposts_recorded_total", 0)
    # The wall's law lives in exactly one place now (seam_engine.wall,
    # ROADMAP.md #21), imported and checked here rather than inlined — see
    # ledger._entry_prose for the other caller, and seam_engine/wall.py for
    # why the two used to be able to drift.
    wall = wall_for(recorded)

    lines = [
        f"# Fencepost Report — {date}",
        "",
        f"*The one thing that fell between `{repo}`'s accounts yesterday.*",
        "",
    ]

    if episode_number is not None and streak_days is not None:
        lines.append(
            f"*Episode {episode_number}. Day {streak_days} of the watch, unbroken — "
            f"same seam, same hour, every day.*"
        )
        lines.append("")

    if primary:
        lines.append(f"**{primary['headline']}** — confidence {primary['confidence']}.")
        lines.append("")
        detail = (primary.get("detail") or "").strip()
        if detail:
            lines.append(detail)
            lines.append("")
        evidence = _fmt_evidence(primary.get("evidence", []))
        if evidence:
            lines.append(evidence)
            lines.append("")
    else:
        lines.append("**Nothing cleared the bar today.** The seam held — recorded plainly, not padded.")
        lines.append("")

    plural = "" if recorded == 1 else "s"
    lines.append(f"**The count.** {recorded} fencepost{plural} named to date. The wall reads {wall}.")
    lines.append("")
    lines.append(TEASER_LINE)
    lines.append("")
    lines.append(f"**Your move.** {suggest_move(primary)}")
    lines.append("")
    lines.append(CONNECT_YOUR_OWN)
    lines.append("")
    lines.append(THE_LINE)
    lines.append("")
    lines.append("Recorded. — Nisaba")
    lines.append("")
    return "\n".join(lines)


def render_latest(base: Path | None = None) -> str:
    """Render the Report for the most recent entry in the Gap Ledger.

    This is the path that renders off the real, live Ledger — so it is also
    the path that carries the real episode number and streak length,
    computed by `seam_engine.streak` off the same tablets. A report built
    by hand in a test (`render_report(sealed)` with no ledger behind it) has
    no such history to report and correctly renders without the line.
    """
    records = ledger.read_records(base)
    if not records:
        raise ValueError("the ledger is empty — nothing to report yet")
    status = streak.streak_status(base)
    return render_report(
        ledger.tip_sealed(records),
        episode_number=status["episode"],
        streak_days=status["streak_days"],
    )


# --- CLI ----------------------------------------------------------------------


def _load_sealed_arg(path: str) -> dict[str, Any]:
    """Read a sealed record for the CLI from `path` ('-' for stdin).

    A CLI-supplied file (or stdin stream) can be any syntactically valid
    JSON -- a bare list, int, bool, null, or string, not just an object --
    and `render_report` immediately treats its argument as a dict
    (`sealed.get("date")`, first line of the function). Left unguarded, a
    non-object payload would crash `main()` with a bare
    `AttributeError: '<type>' object has no attribute 'get'` instead of a
    message naming the actual problem -- the same "malformed input is named,
    never an opaque crash" discipline this module already holds for a
    tampered ledger tip via `ledger.LedgerTamperedError`. Task 538: delegates
    to `ledger._load_json_dict` now, alongside `ledger.py`'s own `_load_scan`
    and `draftback.py`'s `_load_sealed` -- one real implementation instead of
    three copies an AST-hash sweep only ever caught two of.
    """
    return ledger._load_json_dict(path, "sealed record")


def main(argv: list[str] | None = None) -> int:
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)

    ledger_base: Path | None = None
    if "--ledger-base" in argv:
        i = argv.index("--ledger-base")
        ledger_base = Path(argv[i + 1])
        del argv[i : i + 2]

    write = "--write" in argv
    if write:
        argv.remove("--write")

    out_base: Path | None = None
    if "--out-base" in argv:
        i = argv.index("--out-base")
        out_base = Path(argv[i + 1])
        del argv[i : i + 2]

    if argv and argv[0] != "-":
        sealed = _load_sealed_arg(argv[0])
        report = render_report(sealed)
        date = sealed.get("date") or sealed.get("generated_at", "")[:10]
    elif argv == ["-"]:
        sealed = _load_sealed_arg("-")
        report = render_report(sealed)
        date = sealed.get("date") or sealed.get("generated_at", "")[:10]
    else:
        records = ledger.read_records(ledger_base)
        if not records:
            print("the ledger is empty — nothing to report yet")
            return 1
        sealed = ledger.tip_sealed(records)
        # This is the path the daily Action actually runs
        # (`python3 -m seam_engine.report --write`, seam-scan.yml) — the one
        # place a report ships for real, off the live Ledger, so it is the
        # one place the episode/streak line is always real, never invented.
        report = render_latest(ledger_base)
        date = sealed.get("date") or sealed.get("generated_at", "")[:10]

    print(report)

    if write:
        d = reports_dir(out_base)
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{date}.md"
        path.write_text(report, encoding="utf-8")
        print(f"\nWritten: {path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
