# Orita Roadmap — Fencepost (demo #1 of the platform)

> The agent that reads across all your accounts, fixes nothing, and hands you the one thing that fell between them.

**The town's work queue. The loop pulls the next `TODO` in order, ships it as the owner god, marks it `DONE`. No idle cycles. Built inside this repo under `fencepost/` so the town's own repo earns the stars.**

## Non-negotiable design constraints (from the Hand)
1. **Read-only.** Only read/list Arcade scopes. Fencepost fixes nothing; the final action is always the human's.
2. **No grading/competing.** Friend of every automation; it catches what falls in the seam, never says anyone "drops the ball." Name and rank no one.
3. **False positives are fatal.** Every gap self-audited; public true-positive rate rendered; a report ships only if its one gap clears the confidence bar (Ògún's law).
4. **Arcade is the hero, shown safely** — per-user OAuth, least privilege, revocable, audit-logged. This protects Arcade's look; treat it as the point.
5. **Written back to a place the user owns.** The Gap Ledger is a durable record, not a diff.

## Archived: tasks 1-169

Tasks 1-169 (all fully DONE) were moved out of this file for length (task 169's `tools/roadmap_archive.py`). Original text preserved byte-for-byte in the archive file named in that commit -- nothing paraphrased, nothing lost, still findable by task number or `grep`.

## Interlude — wielding the scalpel task 169 forged

| # | status | owner | task | done when |
|--:|:--|:--|:--|:--|
| 170 | WIP (nisaba, 2026-07-20T06:00Z) | nisaba | Task 169 shipped `tools/roadmap_archive.py` and proved it live in `plan` mode (read-only) but deliberately left the real cut for a later, smaller hour. All 169 rows now read DONE. Run the tool for real: `archive ROADMAP.md --up-to 169 --out ROADMAP-ARCHIVE-001-169.md`, leaving this file's pointer note plus this row as the only live content. | The archive command exits 0; `ROADMAP-ARCHIVE-001-169.md` exists and contains tasks 1-169 verbatim (byte-for-byte, checked by diffing archived span against the pre-cut file's own slice); `ROADMAP.md` post-cut still starts with its own preamble/design-constraints section unchanged, still contains exactly one live task row (this one), and still round-trips (`pointer + remainder` reconstructs a file whose task-170 section matches the pre-cut original's); root `tests/test_roadmap_archive.py` and the rest of `tests/` stay green; `python3 tools/ritual_check.py`'s `wip_reclaim`/`scribe_growth` folds both read the new, smaller file cleanly with no crash. |
