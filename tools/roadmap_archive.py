#!/usr/bin/env python3
"""Task 169. The scalpel task 168 flagged but did not build.

Task 168 (`scribe_growth_check.py`) made `ROADMAP.md`'s (656,152 bytes)
and `BUILDLOG.md`'s (329,811 bytes) unbounded, append-only growth durably
WATCHED -- informational only, never blocking. It did not make the growth
STOP. As of task 168 closing, every one of `ROADMAP.md`'s 168 backlog rows
reads `DONE` or `DONE-MACHINERY`; none of that history needs to stay in
the file the loop re-reads at the top of every single hour to find "the
next TODO in order" -- it needs to stay FINDABLE, in a dated archive,
forever.

This module is the archiving MECHANISM, not the archiving ACT: it splits
a `ROADMAP.md`-shaped document into (1) a prefix of fully-DONE sections,
moved byte-for-byte into a dated archive file, and (2) the remaining live
tail -- proven, by construction and by test, to reconstruct the original
document exactly when concatenated back together. Running it for real
against the live 168-row file is left to a later task (a smaller, lower-
risk hour than building AND wielding a scalpel on the town's own live
record in the same sitting); this task ships the scalpel and proves, live
and by test, that it cuts clean.

Structure this leans on (confirmed by reading `ROADMAP.md`'s own real
headers via `grep -n "^## \\|^| # | status"`, never assumed): the file is
a sequence of `## `-prefixed sections. Most task rows born after the
first ~30 each get their own section (one `## Interlude -- ...` header,
one `| # | status | owner | task | done when |` table with exactly one
row, then prose); a few early sections (`## Backlog`, `## Platform
Backlog`, ...) hold many rows under one header. A SECTION -- from one
`## ` line up to (not including) the next `## ` line, or end of file --
is this module's unit of archiving: the smallest span that is both
unambiguous to find (a `## ` line is a `## ` line; a bare table row is
not always inside one contiguous table once interludes interleave prose
between rows) and complete (it carries every row it opens plus everything
narrated about it, including a trailing "*Real proof: ...*" paragraph
that sits AFTER the row and belongs to it, not to whatever comes next).

The status field itself is not always the bare word `DONE` -- task 19
reads `DONE-MACHINERY \xb7 the seven-day count completes only via the
daily routine...`, a full sentence, not a token. A section counts as
fully done only if EVERY row inside it has a status cell that starts with
`DONE` (case-insensitive), never an exact-match check that a real row
like task 19's would silently fail.

Usage:
    python3 tools/roadmap_archive.py plan <path> --up-to N
    python3 tools/roadmap_archive.py archive <path> --up-to N --out <archive-path>
"""
import argparse
import datetime
import os
import re
import sys
from typing import TypedDict


class Section(TypedDict):
    start: int
    end: int
    text: str


class ArchiveResult(TypedDict):
    archived_text: str
    remainder_text: str
    task_range: tuple[int, int] | None
    sections_archived: int


class ArchiveFileResult(TypedDict):
    archived_text: str
    remainder_text: str
    task_range: tuple[int, int]
    sections_archived: int
    out_path: str


ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DEFAULT_ROADMAP = os.path.join(ROOT, "ROADMAP.md")

SECTION_RE = re.compile(r"(?m)^## .*$")
# Group 1: the task number. Group 2: the FULL status cell text (whatever
# sits between the second and third pipe), which may be more than one
# word (task 19's "DONE-MACHINERY \xb7 ..."). Only the first two columns
# are parsed -- later columns routinely carry literal `\|` (escaped pipes
# inside inline code, e.g. task 123/157/161) which would confuse a regex
# that tried to also capture "owner"/"task"/"done when" generically; this
# module never needs those columns, only the number and whether the row
# is done.
ROW_RE = re.compile(r"(?m)^\|\s*(\d+)\s*\|([^|]*)\|")


class RoadmapArchiveError(Exception):
    """Raised when the document can't be split safely -- named, not silent."""


def split_sections(text: str) -> list[Section]:
    """Split `text` into a list of contiguous, gapless section dicts.

    Each dict is {"start": int, "end": int, "text": str}. If any text
    precedes the first `## ` line (the title + non-negotiable-constraints
    preamble in the real file), it is returned as the first entry with no
    special marking -- callers identify it by `section_task_numbers`
    returning an empty list, the same way any other prose-only section
    would. Sections are exactly contiguous: section[i]["end"] ==
    section[i + 1]["start"] for every adjacent pair, and the first starts
    at 0 and the last ends at len(text) -- so concatenating every
    section's "text" in order reproduces `text` exactly, always.
    """
    matches = list(SECTION_RE.finditer(text))
    sections: list[Section] = []
    first_start = matches[0].start() if matches else len(text)
    if first_start > 0:
        sections.append({"start": 0, "end": first_start, "text": text[:first_start]})
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append({"start": start, "end": end, "text": text[start:end]})
    return sections


def section_task_rows(section_text: str) -> list[tuple[int, str]]:
    """Return [(task_num:int, status_cell:str), ...] for every numbered
    row found in this section, in document order. `status_cell` is
    stripped but otherwise verbatim -- callers decide what "done" means.
    """
    return [(int(n), status.strip()) for n, status in ROW_RE.findall(section_text)]


def is_done_status(status_cell: str) -> bool:
    """A row counts as done if its status cell STARTS WITH 'DONE'
    (case-insensitive) -- covers both the bare `DONE` token and
    real, longer cells like task 19's `DONE-MACHINERY \xb7 ...`
    sentence. An exact `== "DONE"` check would silently miss that row.
    """
    return status_cell.strip().upper().startswith("DONE")


def section_is_fully_done(section_text: str) -> bool | None:
    """True if every row in this section is done; None if the section
    carries no numbered row at all (prose-only, or the preamble) --
    distinct from False, since "no rows" is never itself a reason to stop
    archiving on its own (see `select_archivable_prefix`'s own handling).
    """
    rows = section_task_rows(section_text)
    if not rows:
        return None
    return all(is_done_status(status) for _, status in rows)


def select_archivable_prefix(text: str, up_to_task_num: int) -> list[Section]:
    """Return the contiguous run of sections (a Python list, in document
    order) eligible to move into an archive, given a ceiling task number.

    Rules, in order:
    - Sections before the first row-bearing section (the title/preamble)
      are never archived and never stop the scan -- skipped silently.
    - The run starts at the first row-bearing section and extends while
      each subsequent section is (a) fully done and (b) its highest task
      number is <= `up_to_task_num`.
    - A row-bearing section that fails either test ends the run (not
      included). A prose-only section encountered AFTER the run has
      started also ends it (real `ROADMAP.md` never produces this today
      -- every section born after task ~30 carries exactly one row -- but
      the guard is unconditional so a future prose-only section between
      two done rows can never be silently swallowed into an archived
      range it isn't actually part of).

    The returned list is always a contiguous slice of `split_sections`'
    own output, so concatenating the returned sections' "text" fields
    reproduces exactly `text[selected[0]["start"]:selected[-1]["end"]]`,
    and that whole span is the piece safe to lift out of the live file.
    """
    sections = split_sections(text)
    selected: list[Section] = []
    started = False
    for sec in sections:
        rows = section_task_rows(sec["text"])
        if not rows:
            if started:
                break
            continue
        if not all(is_done_status(status) for _, status in rows):
            break
        if max(n for n, _ in rows) > up_to_task_num:
            break
        selected.append(sec)
        started = True
    return selected


def archive_text(text: str, up_to_task_num: int) -> ArchiveResult:
    """Compute the archive/remainder split. Returns a dict:
    {
      "archived_text": the exact, verbatim span being lifted out (may be
          "" if nothing is eligible -- callers should treat that as a
          no-op, not an error),
      "remainder_text": `text` with that exact span removed, plus a
          pointer note in its place (empty string in, empty note out --
          no pointer is inserted when there is nothing to archive),
      "task_range": (min_task, max_task) actually archived, or None,
      "sections_archived": count of sections archived,
    }

    Never writes to disk -- this is the pure function the CLI's `plan`
    and `archive` subcommands both call; `plan` only ever reads this
    dict, `archive` is the only one that touches the filesystem.
    """
    selected = select_archivable_prefix(text, up_to_task_num)
    if not selected:
        return {
            "archived_text": "",
            "remainder_text": text,
            "task_range": None,
            "sections_archived": 0,
        }
    start = selected[0]["start"]
    end = selected[-1]["end"]
    archived = text[start:end]
    all_nums = [n for sec in selected for n, _ in section_task_rows(sec["text"])]
    task_range = (min(all_nums), max(all_nums))
    pointer = (
        f"## Archived: tasks {task_range[0]}-{task_range[1]}\n\n"
        f"Tasks {task_range[0]}-{task_range[1]} (all fully DONE) were moved "
        f"out of this file for length (task 169's `tools/roadmap_archive.py`). "
        f"Original text preserved byte-for-byte in the archive file named in "
        f"that commit -- nothing paraphrased, nothing lost, still findable "
        f"by task number or `grep`.\n\n"
    )
    remainder = text[:start] + pointer + text[end:]
    return {
        "archived_text": archived,
        "remainder_text": remainder,
        "task_range": task_range,
        "sections_archived": len(selected),
    }


def build_archive_file_content(
    archived_text: str,
    task_range: tuple[int, int],
    source_path: str,
    archived_at: str,
) -> tuple[str, str]:
    """Wrap the verbatim archived span with a small, fixed-shape header.
    Returns (header, full_content) so a caller/test can slice
    `full_content[len(header):]` and get back `archived_text` exactly --
    the header never touches the archived bytes.
    """
    header = (
        f"# ROADMAP Archive: tasks {task_range[0]}-{task_range[1]}\n\n"
        f"*Moved out of `{os.path.basename(source_path)}` by "
        f"`tools/roadmap_archive.py` (task 169) on {archived_at}. Every "
        f"byte below this line is verbatim, unedited original text -- "
        f"nothing paraphrased, nothing dropped.*\n\n---\n\n"
    )
    return header, header + archived_text


def archive(
    path: str, up_to_task_num: int, out_path: str, now: str | None = None
) -> ArchiveFileResult:
    """Perform the real, on-disk archive: read `path`, split it, write
    the archived span to `out_path` (must not already exist -- refuses to
    silently overwrite or append into a prior archive's byte range), and
    overwrite `path` with the remainder. Returns the same dict
    `archive_text` returns, plus `"out_path"`.

    Raises `RoadmapArchiveError` (naming the reason) rather than doing a
    partial write: nothing eligible to archive, or `out_path` already
    exists.
    """
    if os.path.exists(out_path):
        raise RoadmapArchiveError(f"refusing to overwrite existing archive: {out_path}")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    result = archive_text(text, up_to_task_num)
    if result["task_range"] is None:
        raise RoadmapArchiveError(
            f"nothing fully-DONE and <= task {up_to_task_num} to archive"
        )
    when = now or datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    _, archive_content = build_archive_file_content(
        result["archived_text"], result["task_range"], path, when
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(archive_content)
    with open(path, "w", encoding="utf-8") as f:
        f.write(result["remainder_text"])
    return ArchiveFileResult(
        archived_text=result["archived_text"],
        remainder_text=result["remainder_text"],
        task_range=result["task_range"],
        sections_archived=result["sections_archived"],
        out_path=out_path,
    )


def format_plan(result: ArchiveResult, up_to_task_num: int) -> str:
    if result["task_range"] is None:
        return f"nothing archivable at or below task {up_to_task_num}"
    lo, hi = result["task_range"]
    return (
        f"archivable: tasks {lo}-{hi} ({result['sections_archived']} "
        f"section(s), {len(result['archived_text'])} bytes archived, "
        f"{len(result['remainder_text'])} bytes remaining live)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    plan_p = sub.add_parser("plan", help="Read-only: show what would be archived")
    plan_p.add_argument("path", nargs="?", default=DEFAULT_ROADMAP)
    plan_p.add_argument("--up-to", type=int, required=True)

    arch_p = sub.add_parser("archive", help="Write the archive and rewrite the source")
    arch_p.add_argument("path", nargs="?", default=DEFAULT_ROADMAP)
    arch_p.add_argument("--up-to", type=int, required=True)
    arch_p.add_argument("--out", required=True)

    args = parser.parse_args(argv)

    if args.command == "plan":
        with open(args.path, encoding="utf-8") as f:
            text = f.read()
        result = archive_text(text, args.up_to)
        print(format_plan(result, args.up_to))
        return 0

    if args.command == "archive":
        try:
            archive_result = archive(args.path, args.up_to, args.out)
        except RoadmapArchiveError as e:
            print(f"refused: {e}", file=sys.stderr)
            return 1
        lo, hi = archive_result["task_range"]
        print(
            f"archived tasks {lo}-{hi} -> {archive_result['out_path']} "
            f"({len(archive_result['archived_text'])} bytes); "
            f"{args.path} now {len(archive_result['remainder_text'])} bytes"
        )
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
